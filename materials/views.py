from django.shortcuts import render
from rest_framework import generics, filters
from .models import Material
from .serializers import MaterialSerializer

# All materials with search + filter
class MaterialListAPI(generics.ListAPIView):
    queryset = Material.objects.all().order_by('-uploaded_at')
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
        return Material.objects.filter(category=category).order_by('-uploaded_at')
