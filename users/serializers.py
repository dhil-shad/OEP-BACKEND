from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import InstitutionJoinRequest, Department, Notification

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    associated_institution_name = serializers.CharField(source='associated_institution.institution_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'uid', 'username', 'email', 'role', 'enrollment_number', 'department', 'institution_name', 'institution_address', 'institution_phone', 'institution_website', 'associated_institution', 'associated_institution_name')
        read_only_fields = ('id', 'associated_institution_name')

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

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        return token

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class InstitutionJoinRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    institution_name = serializers.CharField(source='institution.institution_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = InstitutionJoinRequest
        fields = ('id', 'student', 'student_name', 'institution', 'institution_name', 'enrollment_number', 'department', 'department_name', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at', 'department_name')
