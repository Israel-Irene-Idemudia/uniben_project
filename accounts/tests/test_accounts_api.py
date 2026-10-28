from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import UserProfile, UserPreferences
from core.models import Faculty, Department, Level

User = get_user_model()

class AccountsAPITests(APITestCase):
    def setUp(self):
        # Create core models for registration
        self.faculty = Faculty.objects.create(name='Science')
        self.department = Department.objects.create(name='Computer Science', faculty=self.faculty)
        self.level = Level.objects.create(name='100L', department=self.department)

        self.user_data = {
            'username': 'teststudent',
            'email': 'teststudent@example.com',
            'password': 'Password123!',
        }
        self.user = User.objects.create_user(**self.user_data)
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'points': 50,
                'faculty': self.faculty,
                'department': self.department,
                'level': self.level,
            }
        )

        self.register_url = reverse('register')
        self.me_url = reverse('me')
        self.preferences_url = reverse('user-preferences')

    def test_user_registration_success(self):
        payload = {
            'username': 'newstudent',
            'email': 'newstudent@example.com',
            'password': 'SecurePassword123!',
            'faculty_id': self.faculty.id,
            'department_id': self.department.id,
            'level_id': self.level.id,
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newstudent').exists())

    def test_user_registration_duplicate_username_fails(self):
        payload = {
            'username': 'teststudent',
            'email': 'different@example.com',
            'password': 'SecurePassword123!',
            'faculty_id': self.faculty.id,
            'department_id': self.department.id,
            'level_id': self.level.id,
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_endpoint_requires_authentication(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_returns_user_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'teststudent')

    def test_user_preferences_get_and_update(self):
        self.client.force_authenticate(user=self.user)
        # GET preferences
        get_response = self.client.get(self.preferences_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        # UPDATE preferences via PUT/POST
        post_response = self.client.put(self.preferences_url, {'theme': 'dark'}, format='json')
        self.assertEqual(post_response.status_code, status.HTTP_200_OK)
        
        pref = UserPreferences.objects.get(user=self.user)
        self.assertEqual(pref.theme, 'dark')
