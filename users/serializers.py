from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import InstitutionJoinRequest, Department, Notification, Section, StudyClass

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    associated_institution_name = serializers.CharField(source='associated_institution.institution_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    study_class_name = serializers.CharField(source='study_class.name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'uid', 'username', 'email', 'role', 'enrollment_number', 'department', 'department_name', 'section', 'study_class', 'study_class_name', 'institution_name', 'institution_address', 'institution_phone', 'institution_website', 'associated_institution', 'associated_institution_name')
        read_only_fields = ('id', 'associated_institution_name', 'study_class_name', 'department_name')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('uid', 'username', 'email', 'password', 'role', 'enrollment_number', 'department', 'institution_name', 'institution_address', 'institution_phone', 'institution_website')
        extra_kwargs = {
            'enrollment_number': {'required': False, 'allow_null': True},
            'department': {'required': False, 'allow_null': True},
            'institution_name': {'required': False, 'allow_null': True},
            'institution_address': {'required': False, 'allow_null': True},
            'institution_phone': {'required': False, 'allow_null': True},
            'institution_website': {'required': False, 'allow_null': True},
        }
        
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
            institution_name=validated_data.get('institution_name', ''),
            institution_address=validated_data.get('institution_address', ''),
            institution_phone=validated_data.get('institution_phone', ''),
            institution_website=validated_data.get('institution_website', '')
        )
        
        # Handle department if it's a student (though it might be null initially)
        dept = validated_data.get('department')
        if dept:
            user.department = dept
            user.save()
            
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
    sections_count = serializers.IntegerField(source='sections.count', read_only=True)

    class Meta:
        model = Department
        fields = ('id', 'name', 'description', 'sections_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'sections_count', 'created_at', 'updated_at')

class SectionSerializer(serializers.ModelSerializer):
    classes_count = serializers.IntegerField(source='classes.count', read_only=True)

    class Meta:
        model = Section
        fields = ('id', 'department', 'name', 'classes_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'classes_count')

class StudyClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyClass
        fields = ('id', 'section', 'name', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'user', 'title', 'message', 'is_read', 'created_at')
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {'user': {'required': False}} # Optional so self-notifications still work without explicitly sending user id

class InstitutionJoinRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    student_role = serializers.CharField(source='requested_role', read_only=True)
    institution_name = serializers.CharField(source='institution.institution_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    section_name = serializers.CharField(source='section.name', read_only=True)
    study_class_name = serializers.CharField(source='study_class.name', read_only=True)

    class Meta:
        model = InstitutionJoinRequest
        fields = ('id', 'student', 'student_name', 'student_role', 'institution', 'institution_name', 'enrollment_number', 'department', 'department_name', 'section', 'section_name', 'study_class', 'study_class_name', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at', 'department_name', 'section_name', 'study_class_name', 'student_role')
