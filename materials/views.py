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
        # Explicitly set is_verified to False (redundant due to default, but safe)
        serializer.save(is_verified=False)
