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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    uid = models.CharField(max_length=15, default=generate_uid, editable=False)
    
    # Optional fields for student profiling
    enrollment_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    department = models.CharField(max_length=100, blank=True, null=True)

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
    enrollment_number = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'institution')

    def __str__(self):
        return f"{self.student.username} -> {self.institution.username} ({self.status})"

