from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import InstitutionJoinRequest, Notification, Department

User = get_user_model()

class IntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.institution = User.objects.create_user(
            username='inst1',
            password='password123',
            role='INSTITUTION',
            institution_name='Test Inst'
        )
        self.student = User.objects.create_user(
            username='student1',
            password='password123',
            role='STUDENT'
        )
        self.dept = Department.objects.create(institution=self.institution, name='CS')
        
        # Get token for institution
        response = self.client.post('/api/token/', {
            'username': 'inst1',
            'password': 'password123'
        })
        self.inst_token = response.data['access']

        # Get token for student
        response = self.client.post('/api/token/', {
            'username': 'student1',
            'password': 'password123'
        })
        self.student_token = response.data['access']

    def test_approve_request_updates_student_and_notifies(self):
        # Create join request with department
        join_req = InstitutionJoinRequest.objects.create(
            student=self.student,
            institution=self.institution,
            enrollment_number='EN001',
            department=self.dept
        )

        # Approve as institution
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.inst_token}')
        response = self.client.post(f'/api/users/institution/requests/{join_req.id}/respond/', {
            'action': 'approve'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify student update
        self.student.refresh_from_db()
        self.assertEqual(self.student.enrollment_number, 'EN001')
        self.assertEqual(self.student.associated_institution, self.institution)
        self.assertEqual(self.student.department, 'CS')

        # Verify notification
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.user, self.student)
        self.assertIn('approved', notif.message)

    def test_student_can_fetch_notifications(self):
        Notification.objects.create(user=self.student, title='Test Notif', message='Hello')
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        response = self.client.get('/api/users/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Notif')
