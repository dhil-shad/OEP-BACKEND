from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'uid', 'username', 'email', 'role', 'enrollment_number', 'department', 'institution_name', 'institution_address', 'institution_phone', 'institution_website')
        read_only_fields = ('id',)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('uid', 'username', 'email', 'password', 'role', 'enrollment_number', 'department', 'institution_name', 'institution_address', 'institution_phone', 'institution_website')
        
    def create(self, validated_data):
        enrollment_num = validated_data.get('enrollment_number', '')
        if not enrollment_num:
            enrollment_num = None

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', 'STUDENT'),
            enrollment_number=enrollment_num,
            department=validated_data.get('department', ''),
            institution_name=validated_data.get('institution_name', ''),
            institution_address=validated_data.get('institution_address', ''),
            institution_phone=validated_data.get('institution_phone', ''),
            institution_website=validated_data.get('institution_website', '')
        )
        return user

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        return token

from .models import InstitutionJoinRequest

class InstitutionJoinRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    institution_name = serializers.CharField(source='institution.institution_name', read_only=True)

    class Meta:
        model = InstitutionJoinRequest
        fields = ('id', 'student', 'student_name', 'institution', 'institution_name', 'enrollment_number', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')
