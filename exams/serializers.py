from rest_framework import serializers
from .models import Exam, Question, Option, Submission, Answer, ActivityLog, ProctoringSettings, ExamInvite, TestCase

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ('id', 'text', 'is_correct')

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ('id', 'input_data', 'expected_output', 'is_hidden', 'points')

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, required=False)
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ('id', 'text', 'question_type', 'marks', 'options', 'test_cases')

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        test_cases_data = validated_data.pop('test_cases', [])
        question = Question.objects.create(**validated_data)
        for option_data in options_data:
            Option.objects.create(question=question, **option_data)
        for tc_data in test_cases_data:
            TestCase.objects.create(question=question, **tc_data)
        return question

class ProctoringSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProctoringSettings
        fields = ('id', 'webcam_enabled', 'screen_record_enabled', 'full_screen_enforced', 'tolerance_count')

class ExamInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamInvite
        fields = ('id', 'email', 'token', 'is_used', 'created_at')
        read_only_fields = ('token', 'is_used', 'created_at')

class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    proctoring = ProctoringSettingsSerializer(required=False)
    invites = ExamInviteSerializer(many=True, read_only=True)
    section_name = serializers.ReadOnlyField(source='section.name')
    study_class_name = serializers.ReadOnlyField(source='study_class.name')
    status = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = (
            'id', 'title', 'description', 'instructor', 'instructor_name',
            'section', 'section_name', 'study_class', 'study_class_name',
            'start_time', 'end_time', 'duration_minutes', 'pass_percentage',
            'is_active', 'is_randomized', 'unique_code', 'created_at', 'questions', 'proctoring', 'invites', 'status'
        )
        read_only_fields = ('instructor', 'created_at', 'instructor_name')
    
    def get_status(self, obj):
        from django.utils import timezone
        now = timezone.now()
        
        if not obj.is_active or obj.questions.count() == 0:
            return "Draft"
        if now < obj.start_time:
            return "Upcoming"
        if obj.start_time <= now <= obj.end_time:
            return "Live"
        return "Ended"
        
    def create(self, validated_data):
        proctoring_data = validated_data.pop('proctoring', None)
        exam = Exam.objects.create(**validated_data)
        if proctoring_data:
            ProctoringSettings.objects.create(exam=exam, **proctoring_data)
        else:
            ProctoringSettings.objects.create(exam=exam) # Create default proctoring settings
        return exam

class StudentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ('id', 'text')

class StudentQuestionSerializer(serializers.ModelSerializer):
    options = StudentOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'question_type', 'marks', 'options')
        # We do NOT include test_cases here because it contains the expected_output and input,
        # which candidates shouldn't see directly unless they are public test cases. 
        # But for now, we'll keep them completely hidden.

class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.ReadOnlyField(source='question.text')
    question_marks = serializers.ReadOnlyField(source='question.marks')
    question_type = serializers.ReadOnlyField(source='question.question_type')
    selected_option_text = serializers.ReadOnlyField(source='selected_option.text')
    
    class Meta:
        model = Answer
        fields = ('id', 'question', 'question_text', 'question_marks', 'question_type', 'selected_option', 'selected_option_text', 'descriptive_text', 'code_submission', 'marks_obtained', 'is_graded')

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ('id', 'timestamp', 'action', 'violation_type', 'details', 'snapshot_url')
        read_only_fields = ('id', 'timestamp')

class SubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    logs = ActivityLogSerializer(many=True, read_only=True)
    student_name = serializers.ReadOnlyField(source='student.username')
    exam_title = serializers.ReadOnlyField(source='exam.title')

    class Meta:
        model = Submission
        fields = ('id', 'exam', 'exam_title', 'student', 'student_name', 'start_time', 'end_time', 'status', 'score', 'passed', 'answers', 'logs')
        read_only_fields = ('student', 'start_time', 'end_time', 'status', 'score', 'passed', 'exam_title')
