from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import UserProfile
from core.models import Faculty, Department, Level
from .models import Material
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class MaterialAPITests(APITestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username='student', password='password123', email='student@test.com')
        
        # Create core models for profile
        self.faculty = Faculty.objects.create(name='Science')
        self.department = Department.objects.create(name='Computer Science', faculty=self.faculty)
        self.level = Level.objects.create(name='100L', department=self.department)
        
        self.profile = UserProfile.objects.create(
            user=self.user,
            faculty=self.faculty,
            department=self.department,
            level=self.level,
            points=0
        )

        # Create admin user
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@test.com')
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, points=0)

        # URLs
        self.upload_url = reverse('materials-upload')
        self.admin_list_url = reverse('material-admin-list')
        self.user_list_url = reverse('user-materials-list')
        self.me_url = reverse('me')

    def test_upload_and_verification_flow(self):
        # 1. Upload file as student
        self.client.force_authenticate(user=self.user)
        
        pdf_file = SimpleUploadedFile("test_doc.pdf", b"pdf_content", content_type="application/pdf")
        
        payload = {
            'title': 'Intro to Coding',
            'description': 'A nice PDF',
            'category': 'course',
            'course_code': 'CSC101',
            'course_name': 'Introduction to Programming',
            'faculty_id': self.faculty.id,
            'department_id': self.department.id,
            'file': pdf_file
        }
        
        response = self.client.post(self.upload_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check material in DB
        self.assertEqual(Material.objects.count(), 1)
        material = Material.objects.first()
        self.assertEqual(material.title, 'Intro to Coding')
        self.assertEqual(material.user, self.user)
        self.assertFalse(material.is_verified)
        self.assertEqual(material.faculty, self.faculty)
        self.assertEqual(material.department, self.department)
        
        # Verify me endpoint returns pending points
        me_resp = self.client.get(self.me_url)
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data['pending_points'], 10)
        self.assertEqual(me_resp.data['points'], 0)
        
        # 2. Verify material as admin
        self.client.force_authenticate(user=self.admin_user)
        verify_url = reverse('material-verify', kwargs={'pk': material.pk})
        
        response = self.client.patch(verify_url, {'is_verified': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check material verified in DB
        material.refresh_from_db()
        self.assertTrue(material.is_verified)
        
        # Check user points updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 10)
        
        # Verify me endpoint updates (pending points go to 0, verified points go to 10)
        self.client.force_authenticate(user=self.user)
        me_resp = self.client.get(self.me_url)
        self.assertEqual(me_resp.data['pending_points'], 0)
        self.assertEqual(me_resp.data['points'], 10)

    def test_upload_duplicate_validation(self):
        # Create an existing duplicate material in DB
        Material.objects.create(
            title='Intro to Coding',
            course_code='CSC101',
            faculty=self.faculty,
            department=self.department,
            is_verified=False
        )
        
        self.client.force_authenticate(user=self.user)
        pdf_file = SimpleUploadedFile("test_doc.pdf", b"pdf_content", content_type="application/pdf")
        
        payload = {
            'title': 'Intro to Coding',
            'description': 'Another copy',
            'category': 'course',
            'course_code': 'CSC101',
            'course_name': 'Introduction to Programming',
            'faculty_id': self.faculty.id,
            'department_id': self.department.id,
            'file': pdf_file
        }
        
        response = self.client.post(self.upload_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], "A material with this title and course code already exists in this faculty/department.")

    def test_user_materials_list(self):
        # Create one verified and one pending material for this user
        Material.objects.create(
            title='Material 1',
            course_code='CSC101',
            faculty=self.faculty,
            department=self.department,
            is_verified=True,
            user=self.user
        )
        Material.objects.create(
            title='Material 2',
            course_code='CSC102',
            faculty=self.faculty,
            department=self.department,
            is_verified=False,
            user=self.user
        )
        
        # Create a material for a different user
        other_user = User.objects.create_user(username='other_student', password='password123', email='other@test.com')
        Material.objects.create(
            title='Material 3',
            course_code='CSC103',
            faculty=self.faculty,
            department=self.department,
            is_verified=False,
            user=other_user
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Titles should be Material 2 and Material 1 (ordered by newest first)
        self.assertEqual(response.data[0]['title'], 'Material 2')
        self.assertEqual(response.data[1]['title'], 'Material 1')
        
        # Check faculty_name and department_name serialized properly
        self.assertEqual(response.data[0]['faculty_name'], 'Science')
        self.assertEqual(response.data[0]['department_name'], 'Computer Science')
