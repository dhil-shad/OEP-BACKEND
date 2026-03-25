from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserRegistrationSerializer

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

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import InstitutionJoinRequest
from .serializers import InstitutionJoinRequestSerializer
from django.shortcuts import get_object_or_404

class JoinInstitutionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if request.user.role != 'STUDENT':
            return Response({'detail': 'Only students can request to join an institution.'}, status=status.HTTP_403_FORBIDDEN)
        
        uid = request.data.get('code')
        enrollment_number = request.data.get('enrollment_number')
        
        if not uid or not enrollment_number:
            return Response({'detail': 'Institution code and enrollment number are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            institution = User.objects.get(uid=uid, role='INSTITUTION')
        except User.DoesNotExist:
            return Response({'detail': 'Invalid institution code.'}, status=status.HTTP_404_NOT_FOUND)
            
        if InstitutionJoinRequest.objects.filter(student=request.user, institution=institution).exists():
            return Response({'detail': 'You have already sent a request to this institution.'}, status=status.HTTP_400_BAD_REQUEST)
            
        req = InstitutionJoinRequest.objects.create(
            student=request.user,
            institution=institution,
            enrollment_number=enrollment_number
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
            join_req.status = 'APPROVED'
            join_req.save()
            join_req.student.enrollment_number = join_req.enrollment_number
            join_req.student.save()
            return Response({'detail': 'Request approved.'})
        elif action == 'reject':
            join_req.status = 'REJECTED'
            join_req.save()
            return Response({'detail': 'Request rejected.'})
            
        return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)
