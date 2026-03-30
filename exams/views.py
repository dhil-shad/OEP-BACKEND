import csv
from django.http import HttpResponse

# User activity update
from django.db.models import Avg, Max, Min, Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Exam, Question, Option, Submission, Answer, ExamInvite, ActivityLog
from .serializers import ExamSerializer, QuestionSerializer, OptionSerializer, SubmissionSerializer, ExamInviteSerializer
from .permissions import IsInstructorOrReadOnly, IsInstructor

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    def get_queryset(self):
        # If student, only show active exams where end_time > now
        user = self.request.user
        if user.role == 'STUDENT':
            # Students should see exams they are authorized for OR exams targeted at their section & class
            # We explicitly check that section and study_class are not None to prevent 
            # independent exams from implicitly matching isolated students.
            q_objects = Q(authorized_students=user)
            if user.section and user.study_class:
                q_objects |= Q(section=user.section, study_class=user.study_class)
                
            return Exam.objects.filter(
                q_objects,
                is_active=True
            ).distinct()
        elif user.role == 'INSTRUCTOR':
            # Instructors see only their own exams in a list view, or we can let them see all
            # Let's show them their own exams for now
            return Exam.objects.filter(instructor=user)
        return super().get_queryset()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        exam = self.get_object()
        user = request.user

        if user.role != 'STUDENT':
            return Response({'detail': 'Only students can start an exam.'}, status=status.HTTP_403_FORBIDDEN)

        # Check if already started
        submission, created = Submission.objects.get_or_create(
            exam=exam,
            student=user,
            defaults={'status': 'ONGOING'}
        )

        if not created and submission.status != 'ONGOING':
            return Response({'detail': 'You have already submitted this exam.'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce strict deadline on re-entry. If they are 'ONGOING' but the time expired, auto-submit and block them.
        duration_delta = timezone.timedelta(minutes=exam.duration_minutes)
        if timezone.now() > (submission.start_time + duration_delta):
            submission.status = 'SUBMITTED'
            submission.end_time = timezone.now()
            submission.save()
            return Response({'detail': 'You have already submitted this exam.'}, status=status.HTTP_400_BAD_REQUEST)

        # Give the student the questions WITHOUT the answers
        from .serializers import StudentQuestionSerializer, SubmissionSerializer
        questions = list(exam.questions.all())
        if exam.is_randomized:
            import random
            random.shuffle(questions)

        questions_data = StudentQuestionSerializer(questions, many=True).data
        submission_data = SubmissionSerializer(submission).data

        return Response({
            'submission': submission_data,
            'questions': questions_data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request):
        user = request.user
        if user.role != 'STUDENT':
            return Response({'detail': 'Only students can join exams using a code.'}, status=status.HTTP_403_FORBIDDEN)
            
        code = request.data.get('unique_code')
        if not code:
            return Response({'detail': 'Please provide a joining code.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            exam = Exam.objects.get(unique_code=code, is_active=True)
        except Exam.DoesNotExist:
            return Response({'detail': 'Invalid or inactive exam code.'}, status=status.HTTP_404_NOT_FOUND)
            
        if timezone.now() > exam.end_time:
             return Response({'detail': 'This exam has already ended.'}, status=status.HTTP_400_BAD_REQUEST)
             
        # Add student to authorized_students
        exam.authorized_students.add(user)
             
        # Just return exam details so the frontend can redirect to the take exam page
        # The actual 'Submssion' entry will be created when they call `/start`
        return Response({
            'exam_id': exam.id,
            'title': exam.title,
            'duration_minutes': exam.duration_minutes
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsInstructor])
    def generate_invites(self, request, pk=None):
        exam = self.get_object()
        emails = request.data.get('emails', [])
        
        if not emails or not isinstance(emails, list):
            return Response({'detail': 'Please provide a list of emails.'}, status=status.HTTP_400_BAD_REQUEST)
            
        invites = []
        for email in emails:
            invite, created = ExamInvite.objects.get_or_create(exam=exam, email=email)
            invites.append(invite)
            
        return Response({'detail': f'Generated {len(invites)} invites.', 'invites': ExamInviteSerializer(invites, many=True).data})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def validate_invite(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            invite = ExamInvite.objects.get(token=token, is_used=False)
        except ExamInvite.DoesNotExist:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Optional: verify if the authenticated user's email matches the invite email
        if request.user.email and request.user.email != invite.email:
             return Response({'detail': 'This invite is for a different email address.'}, status=status.HTTP_403_FORBIDDEN)
             
        # Mark as used (we might want to do this when they ACTUALLY start, but doing it here for simplicity or let them reuse it until submission is done)
        # Note: If we mark it used here, they can't refresh. Let's not mark it used until they submit, or just let 'unique_together' in submission handle single attempts.
        
        return Response({
            'exam_id': invite.exam.id,
            'exam_title': invite.exam.title,
            'duration_minutes': invite.exam.duration_minutes
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_answer(self, request, pk=None):
        exam = self.get_object()
        user = request.user

        try:
            submission = Submission.objects.get(exam=exam, student=user, status='ONGOING')
        except Submission.DoesNotExist:
            return Response({'detail': 'No active session found.'}, status=status.HTTP_400_BAD_REQUEST)

        question_id = request.data.get('question_id')
        selected_option_id = request.data.get('selected_option_id')
        descriptive_text = request.data.get('descriptive_text')
        code_submission = request.data.get('code_submission')

        try:
            question = Question.objects.get(id=question_id, exam=exam)
        except Question.DoesNotExist:
            return Response({'detail': 'Invalid question.'}, status=status.HTTP_400_BAD_REQUEST)

        # Update or create answer
        defaults = {
            'descriptive_text': descriptive_text,
            'code_submission': code_submission
        }
        
        if selected_option_id:
            try:
                defaults['selected_option'] = Option.objects.get(id=selected_option_id)
            except Option.DoesNotExist:
                return Response({'detail': 'Invalid option.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            defaults['selected_option'] = None

        answer, created = Answer.objects.update_or_create(
            submission=submission,
            question=question,
            defaults=defaults
        )

        return Response({'detail': 'Answer saved.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_exam(self, request, pk=None):
        exam = self.get_object()
        user = request.user

        try:
            submission = Submission.objects.get(exam=exam, student=user, status='ONGOING')
        except Submission.DoesNotExist:
            return Response({'detail': 'No active session found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional strict deadline check (allowing a 2-minute buffer for network lag)
        duration_delta = timezone.timedelta(minutes=exam.duration_minutes + 2)
        if timezone.now() > (submission.start_time + duration_delta):
            # We can still accept it but maybe flag it, or just accept whatever was auto-saved
            pass # Keep it lenient as answers auto-save anyway

        # Auto-grade MCQ/TF
        total_score = 0
        answers = Answer.objects.filter(submission=submission)
        
        # To ensure we don't miss unattempted questions if they aren't even in the Answer table,
        # we can just loop through exam.questions. However, Answer objects are created when they click or blur.
        # But if they never clicked an option, it won't exist. Let's pre-create missing answers as 0.
        existing_answer_qids = answers.values_list('question_id', flat=True)
        for question in exam.questions.all():
            if question.id not in existing_answer_qids:
                Answer.objects.create(submission=submission, question=question, marks_obtained=0, is_graded=True)
        
        # Now re-fetch all including the newly created ones
        answers = Answer.objects.filter(submission=submission)

        for answer in answers:
            if answer.question.question_type in ['MCQ', 'TF']:
                if answer.selected_option and answer.selected_option.is_correct:
                    answer.marks_obtained = answer.question.marks
                    total_score += answer.question.marks
                else:
                    answer.marks_obtained = 0
                answer.is_graded = True
                answer.save()

        submission.status = 'SUBMITTED'
        submission.end_time = timezone.now()
        submission.score = total_score
        # Calculate passed if all questions are MCQ/TF, otherwise leave null for manual grading
        has_manual = answers.filter(question__question_type__in=['DESC', 'CODE']).exists()
        if not has_manual:
            max_score = sum(q.marks for q in exam.questions.all())
            if max_score > 0:
                percentage = (total_score / max_score) * 100
                submission.passed = percentage >= exam.pass_percentage
            else:
                submission.passed = True # Default pass if exam has no marks
            submission.status = 'GRADED'
        else:
            submission.status = 'SUBMITTED'

        submission.save()

        return Response({'detail': 'Exam submitted successfully.', 'score': total_score})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def log_activity(self, request, pk=None):
        exam = self.get_object()
        user = request.user

        try:
            submission = Submission.objects.get(exam=exam, student=user, status='ONGOING')
        except Submission.DoesNotExist:
            return Response({'detail': 'No active session found to log.'}, status=status.HTTP_400_BAD_REQUEST)

        action_text = request.data.get('action')
        violation_type = request.data.get('violation_type', 'NONE')
        details = request.data.get('details', {})
        snapshot_url = request.data.get('snapshot_url')

        if not action_text:
            return Response({'detail': 'Action text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        ActivityLog.objects.create(
            submission=submission,
            action=action_text,
            violation_type=violation_type,
            details=details,
            snapshot_url=snapshot_url
        )
        
        # Check tolerance
        if hasattr(exam, 'proctoring'):
            # count the number of violations
            violation_count = ActivityLog.objects.filter(submission=submission).exclude(violation_type='NONE').count()
            if violation_count >= exam.proctoring.tolerance_count:
                # auto submit
                submission.status = 'SUBMITTED'
                submission.end_time = timezone.now()
                # we should probably also grade what they have here, but for now just mark submitted
                submission.save()
                return Response({'detail': 'Activity logged. Tolerance exceeded, exam auto-submitted.', 'auto_submitted': True})

        return Response({'detail': 'Activity logged.', 'auto_submitted': False})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsInstructor])
    def analytics(self, request, pk=None):
        exam = self.get_object()
        submissions = Submission.objects.filter(exam=exam, status__in=['SUBMITTED', 'GRADED'])
        
        total_submissions = submissions.count()
        if total_submissions == 0:
            return Response({
                'total_submissions': 0,
                'pass_ratio': 0,
                'fail_ratio': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'question_difficulty': []
            })

        # Calculate basic stats
        stats = submissions.aggregate(
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score')
        )
        
        passed_count = submissions.filter(passed=True).count()
        pass_ratio = (passed_count / total_submissions) * 100
        fail_ratio = 100 - pass_ratio

        # Question difficulty analysis (MCQ/TF only for simplicity)
        question_difficulty = []
        mcq_tf_questions = exam.questions.filter(question_type__in=['MCQ', 'TF'])
        for q in mcq_tf_questions:
            # Count how many students got it right (marks_obtained > 0)
            correct_answers = Answer.objects.filter(question=q, submission__in=submissions, marks_obtained__gt=0).count()
            # Difficulty is inverse of correct percentage (e.g., 20% got it right -> 80% difficulty)
            difficulty_percentage = 100 - ((correct_answers / total_submissions) * 100) if total_submissions > 0 else 0
            question_difficulty.append({
                'question_id': q.id,
                'question_text': q.text[:50] + '...' if len(q.text) > 50 else q.text,
                'difficulty': round(difficulty_percentage, 1),
                'correct_ratio': round((correct_answers / total_submissions) * 100, 1)
            })

        # Sort by difficulty descending (hardest first)
        question_difficulty.sort(key=lambda x: x['difficulty'], reverse=True)

        return Response({
            'total_submissions': total_submissions,
            'pass_ratio': round(pass_ratio, 1),
            'fail_ratio': round(fail_ratio, 1),
            'average_score': round(stats['avg_score'] or 0, 1),
            'highest_score': stats['max_score'] or 0,
            'lowest_score': stats['min_score'] or 0,
            'question_difficulty': question_difficulty
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsInstructor])
    def download_report(self, request, pk=None):
        exam = self.get_object()
        submissions = Submission.objects.filter(exam=exam).select_related('student')

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="exam_report_{exam.id}.csv"'},
        )

        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Email', 'Start Time', 'End Time', 'Status', 'Score', 'Passed', 'Violations Count'])

        for sub in submissions:
            violation_count = ActivityLog.objects.filter(submission=sub).exclude(violation_type='NONE').count()
            writer.writerow([
                f"{sub.student.first_name} {sub.student.last_name}",
                sub.student.email,
                sub.start_time.strftime("%Y-%m-%d %H:%M:%S") if sub.start_time else 'N/A',
                sub.end_time.strftime("%Y-%m-%d %H:%M:%S") if sub.end_time else 'N/A',
                sub.status,
                sub.score,
                'Yes' if sub.passed else 'No',
                violation_count
            ])

        return response


class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrReadOnly]

    def get_queryset(self):
        return Question.objects.filter(exam_id=self.kwargs['exam_pk'])

    def perform_create(self, serializer):
        exam = Exam.objects.get(pk=self.kwargs['exam_pk'])
        serializer.save(exam=exam)


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'INSTRUCTOR':
            # Instructors can see submissions for their exams
            exam_id = self.kwargs.get('exam_pk')
            if exam_id:
                return Submission.objects.filter(exam__id=exam_id, exam__instructor=user)
            return Submission.objects.filter(exam__instructor=user)
        elif user.role == 'STUDENT':
            # Students can only see their own submissions
            return Submission.objects.filter(student=user)
        return Submission.objects.none()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_results(self, request):
        user = request.user
        if user.role != 'STUDENT':
            return Response({'detail': 'Only students can view their results.'}, status=status.HTTP_403_FORBIDDEN)
            
        submissions = Submission.objects.filter(student=user).order_by('-end_time', '-start_time')
        # We need exam title in the serializer response, but SubmissionSerializer doesn't have it.
        # Let's augment the response data with exam title.
        serializer = self.get_serializer(submissions, many=True)
        data = serializer.data
        for i, sub in enumerate(submissions):
            data[i]['exam_title'] = sub.exam.title
        
        return Response(data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsInstructor])
    def grade(self, request, pk=None, exam_pk=None):
        submission = self.get_object()
        
        # Expecting a dictionary of { answer_id: marks_awarded }
        grades = request.data.get('grades', {})
        
        for answer_id, marks in grades.items():
            try:
                answer = Answer.objects.get(id=answer_id, submission=submission)
                answer.marks_obtained = float(marks)
                answer.is_graded = True
                answer.save()
            except (Answer.DoesNotExist, ValueError):
                continue
                
        # Recalculate total score and pass/fail
        total_score = sum(ans.marks_obtained for ans in submission.answers.filter(is_graded=True))
        submission.score = total_score
        
        max_score = sum(q.marks for q in submission.exam.questions.all())
        if max_score > 0:
            percentage = (total_score / max_score) * 100
            submission.passed = percentage >= submission.exam.pass_percentage
        else:
            submission.passed = True
            
        submission.status = 'GRADED'
        submission.save()
        
        return Response({'detail': 'Submission graded successfully.', 'score': total_score})
