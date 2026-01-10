# accounts/profile_views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import UserTimetableEntry, UserPreferences, UserTodoEntry
from .profile_serializers import UserTimetableEntrySerializer, UserPreferencesSerializer, UserTodoEntrySerializer


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


# ============= TODO SYNC VIEWS =============

class TodoListCreateView(generics.ListCreateAPIView):
    """
    GET: List all todo entries for the authenticated user
    POST: Create a new todo entry
    """
    serializer_class = UserTodoEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserTodoEntry.objects.filter(user=self.request.user)


class TodoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific todo entry
    PUT/PATCH: Update a todo entry
    DELETE: Delete a todo entry
    """
    serializer_class = UserTodoEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserTodoEntry.objects.filter(user=self.request.user)


class TodoBulkSyncView(APIView):
    """
    POST: Bulk sync todo entries (replace all with new data)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Delete existing entries
        UserTodoEntry.objects.filter(user=request.user).delete()
        
        # Create new entries
        entries_data = request.data.get('entries', [])
        serializer = UserTodoEntrySerializer(
            data=entries_data,
            many=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': f'Successfully synced {len(entries_data)} todos',
                'entries': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============= NOTES SYNC VIEWS =============

class NotesListView(APIView):
    """
    GET: List all notes for the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .models import UserNoteEntry
        from .serializers import UserNoteEntrySerializer
        notes = UserNoteEntry.objects.filter(user=request.user)
        serializer = UserNoteEntrySerializer(notes, many=True)
        return Response(serializer.data)


class NotesBulkSyncView(APIView):
    """
    POST: Bulk sync notes (replace all with new data)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from .models import UserNoteEntry
        from .serializers import UserNoteEntrySerializer
        
        # Delete existing entries
        UserNoteEntry.objects.filter(user=request.user).delete()
        
        # Create new entries
        entries_data = request.data.get('entries', [])
        created_notes = []
        
        for entry in entries_data:
            note = UserNoteEntry.objects.create(
                user=request.user,
                note_id=entry.get('note_id'),
                title=entry.get('title', ''),
                body=entry.get('body', ''),
                color=entry.get('color', 0xFF6EA8FE),
                pinned=entry.get('pinned', False),
                note_updated_at=entry.get('note_updated_at')
            )
            created_notes.append(note)
        
        serializer = UserNoteEntrySerializer(created_notes, many=True)
        return Response({
            'message': f'Successfully synced {len(created_notes)} notes',
            'entries': serializer.data
        }, status=status.HTTP_201_CREATED)


# ============= GPA SYNC VIEWS =============

class GpaListView(APIView):
    """
    GET: List all GPA entries for the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .models import UserGpaEntry
        from .serializers import UserGpaEntrySerializer
        entries = UserGpaEntry.objects.filter(user=request.user)
        serializer = UserGpaEntrySerializer(entries, many=True)
        return Response(serializer.data)


class GpaBulkSyncView(APIView):
    """
    POST: Bulk sync GPA entries (replace all with new data)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from .models import UserGpaEntry
        from .serializers import UserGpaEntrySerializer
        
        # Delete existing entries
        UserGpaEntry.objects.filter(user=request.user).delete()
        
        # Create new entries
        entries_data = request.data.get('entries', [])
        created_entries = []
        
        for entry in entries_data:
            gpa_entry = UserGpaEntry.objects.create(
                user=request.user,
                course_code=entry.get('course_code', ''),
                course_name=entry.get('course_name', ''),
                unit=entry.get('unit', 0),
                grade=entry.get('grade', 'A'),
                grade_point=entry.get('grade_point', 5.0)
            )
            created_entries.append(gpa_entry)
        
        serializer = UserGpaEntrySerializer(created_entries, many=True)
        return Response({
            'message': f'Successfully synced {len(created_entries)} GPA entries',
            'entries': serializer.data
        }, status=status.HTTP_201_CREATED)


# ============= DEBATER PROGRESS SYNC VIEWS =============

class DebaterProgressView(APIView):
    """
    GET: Retrieve debater progress (creates default if doesn't exist)
    POST/PUT: Update debater progress
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .models import UserDebaterProgress
        from .serializers import UserDebaterProgressSerializer
        
        progress, created = UserDebaterProgress.objects.get_or_create(
            user=request.user
        )
        serializer = UserDebaterProgressSerializer(progress)
        return Response(serializer.data)
    
    def post(self, request):
        return self.put(request)
    
    def put(self, request):
        from .models import UserDebaterProgress
        from .serializers import UserDebaterProgressSerializer
        
        progress, created = UserDebaterProgress.objects.get_or_create(
            user=request.user
        )
        
        # Update only if client's score is higher (high score logic)
        if 'beginner_score' in request.data:
            progress.beginner_score = max(
                progress.beginner_score, 
                request.data.get('beginner_score', 0)
            )
        if 'intermediate_score' in request.data:
            progress.intermediate_score = max(
                progress.intermediate_score,
                request.data.get('intermediate_score', 0)
            )
        if 'advanced_score' in request.data:
            progress.advanced_score = max(
                progress.advanced_score,
                request.data.get('advanced_score', 0)
            )
        if 'expert_score' in request.data:
            progress.expert_score = max(
                progress.expert_score,
                request.data.get('expert_score', 0)
            )
        
        progress.save()
        serializer = UserDebaterProgressSerializer(progress)
        return Response(serializer.data)
