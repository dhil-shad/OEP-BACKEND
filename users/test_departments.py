from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Department

User = get_user_model()

class DepartmentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.institution = User.objects.create_user(
            username='inst1',
            password='password123',
            role='INSTITUTION',
            institution_name='Test Inst'
        )
        self.other_institution = User.objects.create_user(
            username='inst2',
            password='password123',
            role='INSTITUTION',
            institution_name='Other Inst'
        )
        self.student = User.objects.create_user(
            username='student1',
            password='password123',
            role='STUDENT'
        )
        
        # Get token for institution
        response = self.client.post('/api/token/', {
            'username': 'inst1',
            'password': 'password123'
        })
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_create_department(self):
        response = self.client.post('/api/users/departments/', {
            'name': 'CS',
            'description': 'Computer Science'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Department.objects.count(), 1)
        self.assertEqual(Department.objects.first().institution, self.institution)

    def test_list_departments(self):
        Department.objects.create(institution=self.institution, name='CS')
        Department.objects.create(institution=self.other_institution, name='EE')
        
        response = self.client.get('/api/users/departments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'CS')

    def test_student_cannot_list_departments(self):
        # Login as student
        response = self.client.post('/api/token/', {
            'username': 'student1',
            'password': 'password123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        Department.objects.create(institution=self.institution, name='CS')
        
        response = self.client.get('/api/users/departments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0) # ViewSet filters by institution role
