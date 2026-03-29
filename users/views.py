from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets, status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import InstitutionJoinRequest, Department, Notification, Section, StudyClass
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    CustomTokenObtainPairSerializer, 
    InstitutionJoinRequestSerializer, 
    DepartmentSerializer,
    NotificationSerializer,
    SectionSerializer,
    StudyClassSerializer
)

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

class UserProfileView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class PublicInstitutionDepartmentsView(APIView):
    permission_classes = (IsAuthenticated,) # Authenticated students only

    def get(self, request, uid):
        try:
            institution = User.objects.get(uid=uid, role='INSTITUTION')
        except User.DoesNotExist:
            return Response({'detail': 'Invalid institution code.'}, status=status.HTTP_404_NOT_FOUND)
        
        departments = Department.objects.filter(institution=institution)
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

class PublicDepartmentSectionsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, dept_id):
        sections = Section.objects.filter(department_id=dept_id)
        serializer = SectionSerializer(sections, many=True)
        return Response(serializer.data)

class JoinInstitutionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if request.user.role not in ['STUDENT', 'INSTRUCTOR']:
            return Response({'detail': 'Only students and instructors can request to join an institution.'}, status=status.HTTP_403_FORBIDDEN)
        
        uid = request.data.get('code')
        role = request.data.get('role', 'STUDENT')
        enrollment_number = request.data.get('enrollment_number')
        department_id = request.data.get('department')
        section_id = request.data.get('section')
        study_class_id = request.data.get('study_class')
        
        if not uid or not department_id:
            return Response({'detail': 'Institution code and department are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if role == 'STUDENT' and (not enrollment_number or not section_id or not study_class_id):
            return Response({'detail': 'Enrollment number, section, and class are required for students.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            institution = User.objects.get(uid=uid, role='INSTITUTION')
        except User.DoesNotExist:
            return Response({'detail': 'Invalid institution code.'}, status=status.HTTP_404_NOT_FOUND)
            
        existing_req = InstitutionJoinRequest.objects.filter(student=request.user, institution=institution).first()
        if existing_req:
            if existing_req.status == 'REJECTED':
                existing_req.delete() # Allow re-application by deleting the rejected record
            else:
                return Response({'detail': 'You have already sent a request to this institution.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            dept = Department.objects.get(id=department_id, institution=institution)
        except Department.DoesNotExist:
            return Response({'detail': 'Invalid department.'}, status=status.HTTP_400_BAD_REQUEST)

        sec = None
        if role == 'STUDENT':
            try:
                sec = Section.objects.get(id=section_id, department=dept)
            except Section.DoesNotExist:
                return Response({'detail': 'Invalid section.'}, status=status.HTTP_400_BAD_REQUEST)

        cls = None
        if role == 'STUDENT':
            try:
                cls = StudyClass.objects.get(id=study_class_id, section=sec)
            except StudyClass.DoesNotExist:
                return Response({'detail': 'Invalid class.'}, status=status.HTTP_400_BAD_REQUEST)

        req = InstitutionJoinRequest.objects.create(
            student=request.user,
            institution=institution,
            requested_role=role,
            enrollment_number=enrollment_number,
            department=dept,
            section=sec,
            study_class=cls
        )
        return Response(InstitutionJoinRequestSerializer(req).data, status=status.HTTP_201_CREATED)

class InstitutionRequestsView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = InstitutionJoinRequestSerializer

    def get_queryset(self):
        if self.request.user.role != 'INSTITUTION':
            return InstitutionJoinRequest.objects.none()
        return InstitutionJoinRequest.objects.filter(institution=self.request.user).order_by('-created_at')

class RespondJoinRequestView(APIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, pk):
        if request.user.role != 'INSTITUTION':
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        join_req = get_object_or_404(InstitutionJoinRequest, pk=pk, institution=request.user)
        action = request.data.get('action')
        
        if action == 'approve':
            try:
                from django.db import transaction, IntegrityError
                with transaction.atomic():
                    join_req.status = 'APPROVED'
                    join_req.save()
                    
                    # Update student/instructor's role, institution and hierarchy
                    user = join_req.student
                    user.role = join_req.requested_role # Update role to what was requested
                    user.associated_institution = join_req.institution
                    user.department = join_req.department
                    
                    if user.role == 'STUDENT':
                        user.enrollment_number = join_req.enrollment_number
                        user.section = join_req.section
                        user.study_class = join_req.study_class
                    
                    user.save()

                    # Create notification
                    Notification.objects.create(
                        user=user,
                        title="Institution Join Request Approved",
                        message=f"Your request to join {join_req.institution.institution_name} has been approved."
                    )
                return Response({'detail': 'Request approved.'})
            except IntegrityError:
                return Response({
                    'detail': f'Approval failed: Enrollment number "{join_req.enrollment_number}" is already assigned to another user.'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif action == 'reject':
            join_req.status = 'REJECTED'
            join_req.save()
            return Response({'detail': 'Request rejected.'})
            
        return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

class InstitutionStudentsView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.role != 'INSTITUTION':
            return User.objects.none()
        return User.objects.filter(
            role='STUDENT',
            associated_institution=self.request.user
        ).order_by('username')

class InstitutionStudentActionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        if request.user.role != 'INSTITUTION':
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        student = get_object_or_404(User, pk=pk, associated_institution=request.user, role='STUDENT')
        action = request.data.get('action')

        if action == 'promote':
            dept_id = request.data.get('department_id')
            if not dept_id:
                return Response({'detail': 'Department is required for promotion.'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .models import Department
            department = get_object_or_404(Department, pk=dept_id, institution=request.user)
            
            student.role = 'INSTRUCTOR'
            student.department = department.name
            student.save()
            return Response({'detail': f'Student {student.username} promoted to Instructor in {department.name}.'})
            
        elif action == 'kick':
            student.associated_institution = None
            student.enrollment_number = None
            student.department = None
            student.save()
            return Response({'detail': f'Student {student.username} removed from institution.'})

        return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

class InstitutionInstructorsView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.role != 'INSTITUTION':
            return User.objects.none()
        return User.objects.filter(
            role='INSTRUCTOR',
            associated_institution=self.request.user
        ).order_by('username')

class DepartmentStudentsView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != 'INSTRUCTOR':
            return User.objects.none()
        return User.objects.filter(
            role='STUDENT',
            associated_institution=user.associated_institution,
            department=user.department
        ).order_by('username')

class DepartmentViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        if self.request.user.role != 'INSTITUTION':
            return Department.objects.none()
        return Department.objects.filter(institution=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(institution=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SectionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = SectionSerializer

    def get_queryset(self):
        queryset = Section.objects.filter(department__institution=self.request.user)
        dept_id = self.request.query_params.get('department_id')
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        return queryset.order_by('name')

    def perform_create(self, serializer):
        dept_id = self.request.data.get('department')
        department = get_object_or_404(Department, id=dept_id, institution=self.request.user)
        serializer.save(department=department)

class StudyClassViewSet(viewsets.ModelViewSet):
    serializer_class = StudyClassSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        section_id = self.request.query_params.get('section_id')
        queryset = StudyClass.objects.filter(section__department__institution=self.request.user)
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        return queryset

    def perform_create(self, serializer):
        section_id = self.request.data.get('section')
        try:
            Section.objects.get(id=section_id, department__institution=self.request.user)
            serializer.save()
        except Section.DoesNotExist:
            raise serializers.ValidationError('Invalid section.')

class PublicSectionClassesView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, section_id):
        classes = StudyClass.objects.filter(section_id=section_id)
        serializer = StudyClassSerializer(classes, many=True)
        return Response(serializer.data)
