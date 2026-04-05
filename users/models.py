import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

def generate_uid():
    return uuid.uuid4().hex[:8].upper()

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('INSTRUCTOR', 'Instructor'),
        ('STUDENT', 'Student'),
        ('INSTITUTION', 'Institution'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    uid = models.CharField(max_length=15, default=generate_uid, editable=False)
    
    # Optional fields for student profiling
    enrollment_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    section = models.ForeignKey('Section', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    study_class = models.ForeignKey('StudyClass', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    associated_institution = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='institution_users')

    # Institution-specific fields
    institution_name = models.CharField(max_length=200, blank=True, null=True)
    institution_address = models.TextField(blank=True, null=True)
    institution_phone = models.CharField(max_length=20, blank=True, null=True)
    institution_website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class InstitutionJoinRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='join_requests')
    institution = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    enrollment_number = models.CharField(max_length=50, blank=True, null=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    section = models.ForeignKey('Section', on_delete=models.SET_NULL, null=True, blank=True)
    study_class = models.ForeignKey('StudyClass', on_delete=models.SET_NULL, null=True, blank=True)
    requested_role = models.CharField(max_length=20, default='STUDENT')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'institution')

    def __str__(self):
        return f"{self.student.username} -> {self.institution.username} ({self.status})"

class Department(models.Model):
    institution = models.ForeignKey(User, on_delete=models.CASCADE, related_name='departments', limit_choices_to={'role': 'INSTITUTION'})
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('institution', 'name')

    def __str__(self):
        return f"{self.name} ({self.institution.username})"

class Section(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('department', 'name')

    def __str__(self):
        return f"{self.department.name} - {self.name}"

class StudyClass(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='classes')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('section', 'name')
        verbose_name_plural = "Study Classes"

    def __str__(self):
        return f"{self.section.name} - {self.name}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.user.username}"
