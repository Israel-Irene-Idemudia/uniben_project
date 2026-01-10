# accounts/models.py
from django.db import models
from django.conf import settings
from core.models import Faculty, Department, Level, CourseArea

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='userprofile'
    )
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True)
    course_area = models.ForeignKey(CourseArea, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'


class UserTimetableEntry(models.Model):
    """Stores timetable entries for users to enable cross-device sync."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timetable_entries'
    )
    subject = models.CharField(max_length=200)
    day = models.CharField(max_length=20)  # Monday, Tuesday, etc.
    time = models.CharField(max_length=50)  # e.g., "08:00 AM" or "14:30"
    
    # Alarm settings
    alarm_enabled = models.BooleanField(default=False)
    alarm_times = models.JSONField(
        default=list,
        help_text="List of alarm times in minutes before class (e.g., [30, 15, 5, 0])"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day', 'time']
        verbose_name = 'User Timetable Entry'
        verbose_name_plural = 'User Timetable Entries'
    
    def __str__(self):
        return f"{self.user.username} - {self.subject} ({self.day} {self.time})"


class UserPreferences(models.Model):
    """Stores user preferences and settings."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    
    # Notification preferences
    notifications_enabled = models.BooleanField(default=True)
    notification_sound = models.CharField(max_length=100, blank=True, null=True)
    
    # App preferences
    theme = models.CharField(
        max_length=20,
        choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System')],
        default='system'
    )
    
    # Other settings stored as JSON for flexibility
    other_settings = models.JSONField(default=dict, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"{self.user.username}'s Preferences"


class UserTodoEntry(models.Model):
    """Stores todo entries for users to enable cross-device sync."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='todo_entries'
    )
    task = models.CharField(max_length=500)
    time = models.CharField(max_length=50, blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Todo Entry'
        verbose_name_plural = 'User Todo Entries'
    
    def __str__(self):
        return f"{self.user.username} - {self.task[:50]}"


class UserNoteEntry(models.Model):
    """Stores notes for users to enable cross-device sync."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='note_entries'
    )
    note_id = models.CharField(max_length=50)  # Client-generated ID
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    color = models.IntegerField()  # ARGB color value
    pinned = models.BooleanField(default=False)
    note_updated_at = models.DateTimeField()  # Client's timestamp
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-pinned', '-note_updated_at']
        verbose_name = 'User Note Entry'
        verbose_name_plural = 'User Note Entries'
        unique_together = ['user', 'note_id']  # One note_id per user
    
    def __str__(self):
        return f"{self.user.username} - {self.title[:30] or 'Untitled'}"


class UserGpaEntry(models.Model):
    """Stores GPA calculator entries for users to enable cross-device sync."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gpa_entries'
    )
    course_code = models.CharField(max_length=20, blank=True)
    course_name = models.CharField(max_length=255)
    unit = models.FloatField()
    grade = models.CharField(max_length=2)  # A, B, C, D, E, F
    grade_point = models.FloatField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['course_name']
        verbose_name = 'User GPA Entry'
        verbose_name_plural = 'User GPA Entries'
    
    def __str__(self):
        return f"{self.user.username} - {self.course_name} ({self.grade})"


class UserDebaterProgress(models.Model):
    """Stores Debater game progress for users to enable cross-device sync."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debater_progress'
    )
    
    # High scores for each difficulty level
    beginner_score = models.IntegerField(default=0)
    intermediate_score = models.IntegerField(default=0)
    advanced_score = models.IntegerField(default=0)
    expert_score = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Debater Progress'
        verbose_name_plural = 'User Debater Progress'
    
    def __str__(self):
        return f"{self.user.username}'s Debater Progress"
