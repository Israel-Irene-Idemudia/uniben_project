# accounts/profile_views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import UserTimetableEntry, UserPreferences
from .profile_serializers import UserTimetableEntrySerializer, UserPreferencesSerializer


class TimetableListCreateView(generics.ListCreateAPIView):
    """
    GET: List all timetable entries for the authenticated user
    POST: Create a new timetable entry
    """
    serializer_class = UserTimetableEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserTimetableEntry.objects.filter(user=self.request.user)


class TimetableDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific timetable entry
    PUT/PATCH: Update a timetable entry
    DELETE: Delete a timetable entry
    """
    serializer_class = UserTimetableEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserTimetableEntry.objects.filter(user=self.request.user)


class UserPreferencesView(APIView):
    """
    GET: Retrieve user preferences (creates default if doesn't exist)
    POST/PUT: Update user preferences
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        preferences, created = UserPreferences.objects.get_or_create(
            user=request.user
        )
        serializer = UserPreferencesSerializer(preferences)
        return Response(serializer.data)
    
    def post(self, request):
        return self.put(request)
    
    def put(self, request):
        preferences, created = UserPreferences.objects.get_or_create(
            user=request.user
        )
        serializer = UserPreferencesSerializer(
            preferences,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TimetableBulkSyncView(APIView):
    """
    POST: Bulk sync timetable entries (replace all with new data)
    Useful for initial sync from local storage
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Delete existing entries
        UserTimetableEntry.objects.filter(user=request.user).delete()
        
        # Create new entries
        entries_data = request.data.get('entries', [])
        serializer = UserTimetableEntrySerializer(
            data=entries_data,
            many=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': f'Successfully synced {len(entries_data)} entries',
                'entries': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
