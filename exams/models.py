from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

import string
import random

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Exam(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_exams')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField(help_text="Duration of the exam in minutes")
    pass_percentage = models.FloatField(default=50.0)
    is_active = models.BooleanField(default=True)
    is_randomized = models.BooleanField(default=True, help_text="Randomize question sequence for each student")
    unique_code = models.CharField(max_length=10, default=generate_unique_code, unique=True, help_text="Unique code for students to join the exam")
    authorized_students = models.ManyToManyField(User, related_name='authorized_exams', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ProctoringSettings(models.Model):
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name='proctoring')
    webcam_enabled = models.BooleanField(default=False, help_text="Require webcam access and take periodic snapshots")
    screen_record_enabled = models.BooleanField(default=False, help_text="Require screen sharing")
    full_screen_enforced = models.BooleanField(default=True, help_text="Enforce full screen mode")
    tolerance_count = models.IntegerField(default=3, help_text="Number of warnings before auto-submission")

    def __str__(self):
        return f"Proctoring for {self.exam.title}"

class ExamInvite(models.Model):
    import uuid
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='invites')
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'email')

    def __str__(self):
        return f"Invite for {self.email} - {self.exam.title}"

class Question(models.Model):
    QUESTION_TYPES = (
        ('MCQ', 'Multiple Choice Question'),
        ('TF', 'True/False'),
        ('DESC', 'Descriptive'),
        ('CODE', 'Coding'),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    marks = models.FloatField(default=1.0)

    def __str__(self):
        return f"{self.exam.title} - Q{self.id}"

class TestCase(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(help_text="Input for the program. Each argument on a new line or formatted appropriately.")
    expected_output = models.TextField(help_text="Expected standard output")
    is_hidden = models.BooleanField(default=True, help_text="Hide this test case from the student during evaluation")
    points = models.FloatField(default=1.0)
    
    def __str__(self):
        return f"TestCase for Q{self.question.id}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question.id} - {self.text}"

class Submission(models.Model):
    STATUS_CHOICES = (
        ('ONGOING', 'Ongoing'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ONGOING')
    score = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    
    class Meta:
        unique_together = ('exam', 'student') # Prevent multiple attempts

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"

class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    descriptive_text = models.TextField(null=True, blank=True)
    code_submission = models.TextField(null=True, blank=True)
    marks_obtained = models.FloatField(default=0.0)
    is_graded = models.BooleanField(default=False)

    def __str__(self):
        return f"Submission {self.submission.id} - Q{self.question.id}"

class ActivityLog(models.Model):
    VIOLATION_CHOICES = (
        ('NONE', 'None'),
        ('TAB_SWITCH', 'Tab Switch'),
        ('FOCUS_LOST', 'Window Focus Lost'),
        ('COPY_PASTE', 'Copy/Paste Attempt'),
        ('NO_FACE', 'No Face Detected'),
        ('MULTIPLE_FACES', 'Multiple Faces Detected'),
        ('FULL_SCREEN_EXIT', 'Exited Full Screen')
    )
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)
    violation_type = models.CharField(max_length=30, choices=VIOLATION_CHOICES, default='NONE')
    details = models.JSONField(null=True, blank=True)
    snapshot_url = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.submission.id} - {self.action}"

