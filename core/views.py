
from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Import all models and serializers needed
from core.models import Faculty, Department, CourseArea, Level, Course, CampusLocation
from core.serializers import (
    FacultySerializer, 
    DepartmentSerializer, 
    CourseAreaSerializer, 
    LevelSerializer,
    CourseSerializer,
    CampusLocationSerializer
)


# --- ViewSets for listing Faculties, Departments, Course Areas, and Levels ---

class CampusLocationViewSet(ReadOnlyModelViewSet):
    """
    API endpoint for campus map locations.
    Returns only active locations, ordered by category and name.
    Supports filtering by category via ?category=faculty
    """
    serializer_class = CampusLocationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        qs = CampusLocation.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class FacultyViewSet(ReadOnlyModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [AllowAny]


class DepartmentViewSet(ReadOnlyModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Department.objects.all()
        faculty_id = self.request.query_params.get('faculty_id')
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)
        return qs


class CourseAreaViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseAreaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = CourseArea.objects.all()
        department_id = self.request.query_params.get('department_id')
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs


class LevelViewSet(ReadOnlyModelViewSet):
    serializer_class = LevelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Dynamically filters levels based on faculty, department, and course area.
        - If `department_id` is provided, it filters levels for that department.
        - If `course_area_id` is also provided, it further refines the filter.
        """
        qs = Level.objects.all()

        department_id = self.request.query_params.get('department_id')
        course_area_id = self.request.query_params.get('course_area_id')

        if department_id:
            qs = qs.filter(department_id=department_id)

            # If a course area is also specified, filter by that as well.
            if course_area_id:
                qs = qs.filter(course_area_id=course_area_id)

        else:
            # If no department is specified, it doesn't make sense to return any levels.
            return qs.none()

        return qs.order_by('name')


class CourseViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Course.objects.select_related(
            'level', 'level__department', 'level__course_area'
        ).order_by('code', 'id')

        params = self.request.query_params

        department_id = params.get('department_id')
        level_id = params.get('level_id')

        if not all([department_id, level_id]):
            return qs.none()

        final_qs = qs.filter(
            level__department_id=department_id,
            level_id=level_id
        )

        course_area_id = params.get('course_area_id')
        if course_area_id:
            final_qs = final_qs.filter(level__course_area_id=course_area_id)
        else:
            final_qs = final_qs.filter(level__course_area__isnull=True)

        return final_qs

from rest_framework import generics
from core.models import ContactMessage
from core.serializers import ContactMessageSerializer
from rest_framework import permissions

class ContactMessageListAPI(generics.ListAPIView):
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.IsAdminUser]


class ContactMessageCreateAPI(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to submit

    def perform_create(self, serializer):
        instance = None
        if self.request.user.is_authenticated:
            # Auto-fill name/email if authenticated
            instance = serializer.save(
                user=self.request.user, 
                email=self.request.user.email or "",
                name=f"{self.request.user.first_name} {self.request.user.last_name}".strip()
            )
        else:
            instance = serializer.save()

        # Send email notification
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = f"[Skholar Support] {instance.subject}"
            message = f"""
New support message received from {instance.name} ({instance.email}):

Subject: {instance.subject}

Message:
{instance.message}

---
Sent from Skholar App
            """
            
            recipient_list = ['theproblemsolvers@skholar.site']
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send support email: {e}")


class ContactMessageDeleteAPI(generics.DestroyAPIView):
    """Admin-only endpoint to delete contact messages"""
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admins can delete


class ContactMessageReplyAPI(APIView):
    """
    Admin-only endpoint to reply to a contact message via email.
    POST /api/contact/<id>/reply/
    Body: { "message": "Your reply content..." }
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        message_body = request.data.get('message')
        if not message_body:
             return Response({"error": "Message content is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            contact_msg = ContactMessage.objects.get(pk=pk)
        except ContactMessage.DoesNotExist:
             return Response({"error": "Contact message not found."}, status=status.HTTP_404_NOT_FOUND)

        if not contact_msg.email:
             return Response({"error": "This contact message has no associated email address."}, status=status.HTTP_400_BAD_REQUEST)

        # Send Email
        try:
            from django.core.mail import send_mail
            from django.conf import settings

            subject = f"Re: {contact_msg.subject} - [Skholar Support]"
            email_content = f"""
Hello {contact_msg.name or 'User'},

{message_body}

---
Best regards,
The Skholar Team
            """
            
            send_mail(
                subject,
                email_content,
                settings.DEFAULT_FROM_EMAIL,
                [contact_msg.email],
                fail_silently=False,
            )
            
            return Response({"message": "Reply sent successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from core.models import GlobalPrompt
from core.serializers import GlobalPromptSerializer

class GlobalPromptAPI(APIView):
    """
    API endpoint for the Global Prompt (Windows Prompt / Countdown).
    GET: Returns a list of all prompts (admin only) or the active prompt (public).
    POST: Creates a new prompt (admin only).
    PUT: Updates a specific prompt (admin only).
    DELETE: Deletes a specific prompt (admin only).
    """
    def get_permissions(self):
        if self.request.method == 'GET' and 'admin' not in self.request.query_params:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get(self, request):
        if request.user.is_staff and request.query_params.get('admin') == 'true':
            prompts = GlobalPrompt.objects.all().order_by('-id')
            serializer = GlobalPromptSerializer(prompts, many=True)
            return Response(serializer.data)
        else:
            prompt = GlobalPrompt.objects.filter(is_active=True).first()
            if prompt:
                serializer = GlobalPromptSerializer(prompt)
                return Response(serializer.data)
            return Response({'error': 'No active prompt found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        serializer = GlobalPromptSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        prompt_id = request.data.get('id')
        if not prompt_id:
            return Response({'error': 'Prompt ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            prompt = GlobalPrompt.objects.get(id=prompt_id)
        except GlobalPrompt.DoesNotExist:
            return Response({'error': 'Prompt not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = GlobalPromptSerializer(prompt, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        prompt_id = request.query_params.get('id')
        if not prompt_id:
            return Response({'error': 'Prompt ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            prompt = GlobalPrompt.objects.get(id=prompt_id)
            prompt.delete()
            return Response({'message': 'Prompt deleted'}, status=status.HTTP_204_NO_CONTENT)
        except GlobalPrompt.DoesNotExist:
            return Response({'error': 'Prompt not found'}, status=status.HTTP_404_NOT_FOUND)
