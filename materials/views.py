from django.shortcuts import render
from rest_framework import generics, filters, permissions
from .models import Material
from .serializers import MaterialSerializer
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from notifications.models import InAppNotification
from notifications.utils import send_onesignal_notification

# All materials with search + filter
class MaterialListAPI(generics.ListAPIView):
    queryset = Material.objects.filter(is_verified=True).order_by('-uploaded_at')
    serializer_class = MaterialSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']  # e.g. search "MTH101" or "Past Questions"]

# Filter by category (e.g. course, past_question, other)
class MaterialByCategoryAPI(generics.ListAPIView):
    serializer_class = MaterialSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']

    def get_queryset(self):
        category = self.kwargs['category']
        return Material.objects.filter(category=category, is_verified=True).order_by('-uploaded_at')

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import permissions

class MaterialUploadAPI(generics.CreateAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        faculty_id = self.request.data.get('faculty_id')
        department_id = self.request.data.get('department_id')
        course_code = self.request.data.get('course_code')
        title = self.request.data.get('title')

        # Convert IDs safely
        try:
            faculty_id = int(faculty_id) if faculty_id else None
        except ValueError:
            faculty_id = None

        try:
            department_id = int(department_id) if department_id else None
        except ValueError:
            department_id = None

        # Folder management duplicate check
        if faculty_id and department_id and course_code and title:
            duplicate_exists = Material.objects.filter(
                faculty_id=faculty_id,
                department_id=department_id,
                course_code__iexact=course_code.strip(),
                title__iexact=title.strip()
            ).exists()
            if duplicate_exists:
                raise ValidationError({"error": "A material with this title and course code already exists in this faculty/department."})

        # Save with user, faculty, department and set is_verified to False
        try:
            serializer.save(
                user=self.request.user, 
                is_verified=False,
                faculty_id=faculty_id,
                department_id=department_id
            )
        except ValidationError:
            raise
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            raise ValidationError({"error": f"Upload failed: {str(e)}"})


class UserMaterialListAPI(generics.ListAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Material.objects.filter(user=self.request.user).order_by('-uploaded_at')


# Admin: List all/unverified materials
class MaterialAdminListAPI(generics.ListAPIView):
    queryset = Material.objects.all().order_by('-uploaded_at')
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.query_params.get('status') # 'verified', 'pending'
        if status == 'verified':
            return qs.filter(is_verified=True)
        elif status == 'pending':
            return qs.filter(is_verified=False)
        return qs

# Admin: Verify/Reject material
class MaterialVerificationAPI(generics.UpdateAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_update(self, serializer):
        material = serializer.instance
        was_verified = material.is_verified
        serializer.save()
        if not was_verified and serializer.instance.is_verified:
            user = serializer.instance.user
            if user:
                from accounts.models import UserProfile
                try:
                    profile = user.userprofile
                    profile.points += 10
                    profile.save()
                except UserProfile.DoesNotExist:
                    pass

# Admin: Delete material
class MaterialDeleteAPI(generics.DestroyAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_destroy(self, instance):
        user = instance.user
        title = instance.title
        
        # Send Notification before deleting
        if user:
            message = f"Your uploaded material '{title}' was rejected and removed by an admin because it violates our guidelines or is invalid."
            
            # In-App Notification
            InAppNotification.objects.create(
                user=user,
                notification_type='general',
                title='Material Rejected',
                message=message,
            )
            
            # Push Notification
            try:
                # Include external_id to target specific user
                send_onesignal_notification(
                    heading='Material Rejected ❌',
                    message=message,
                    external_id=str(user.id)
                )
            except Exception as e:
                pass # Fail silently if push fails

        instance.delete()
