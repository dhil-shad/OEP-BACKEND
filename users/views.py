from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import InstitutionJoinRequest, Department, Notification
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    CustomTokenObtainPairSerializer, 
    InstitutionJoinRequestSerializer, 
    DepartmentSerializer,
    NotificationSerializer
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

class JoinInstitutionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if request.user.role != 'STUDENT':
            return Response({'detail': 'Only students can request to join an institution.'}, status=status.HTTP_403_FORBIDDEN)
        
        uid = request.data.get('code')
        enrollment_number = request.data.get('enrollment_number')
        department_id = request.data.get('department')
        
        if not uid or not enrollment_number or not department_id:
            return Response({'detail': 'Institution code, enrollment number, and department are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            institution = User.objects.get(uid=uid, role='INSTITUTION')
        except User.DoesNotExist:
            return Response({'detail': 'Invalid institution code.'}, status=status.HTTP_404_NOT_FOUND)
            
        if InstitutionJoinRequest.objects.filter(student=request.user, institution=institution).exists():
            return Response({'detail': 'You have already sent a request to this institution.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            dept = Department.objects.get(id=department_id, institution=institution)
        except Department.DoesNotExist:
            return Response({'detail': 'Invalid department.'}, status=status.HTTP_400_BAD_REQUEST)

        req = InstitutionJoinRequest.objects.create(
            student=request.user,
            institution=institution,
            enrollment_number=enrollment_number,
            department=dept
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
                    
                    # Update student's institution and enrollment
                    student = join_req.student
                    student.enrollment_number = join_req.enrollment_number
                    student.associated_institution = join_req.institution
                    if join_req.department:
                        student.department = join_req.department.name
                    student.save()

                    # Create notification
                    Notification.objects.create(
                        user=student,
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
