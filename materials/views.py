from django.shortcuts import render
from rest_framework import generics, filters
from .models import Material
from .serializers import MaterialSerializer

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
        # Save with user and set is_verified to False
        serializer.save(user=self.request.user, is_verified=False)

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
        # Allow updating is_verified and other fields
        serializer.save()

# Admin: Delete material
class MaterialDeleteAPI(generics.DestroyAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAdminUser]

