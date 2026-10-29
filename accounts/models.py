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

    # Points & Rewards fields
    points = models.IntegerField(default=0)
    phone = models.CharField(max_length=20, blank=True, default='')
    network = models.CharField(max_length=15, blank=True, default='')
    student_id = models.CharField(max_length=50, blank=True, default='')
    matric_number = models.CharField(max_length=50, blank=True, default='')

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


class AccountDeletionRequest(models.Model):
    """Stores user requests for account deletion (Soft Delete)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deletion_request'
    )
    reason = models.TextField(blank=True, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    
    # If approved, the user (and this request) is deleted.
    # If rejected, this request object is deleted.
    # So we mainly use this to track PENDING requests.
    
    class Meta:
        verbose_name = 'Account Deletion Request'
        verbose_name_plural = 'Account Deletion Requests'
        ordering = ['-request_date']

    def __str__(self):
        return f"Deletion Request: {self.user.username}"
class AuthEvent(models.Model):
    """Attempt log used for database-backed limits (works across workers).

    Phase 2.8 reuses this model for login lockout and the auth log.
    key_hash is a SHA-256 of the email, never the email itself.
    """

    KIND_RESET_REQUEST = "reset_request"
    KIND_RESET_CONFIRM = "reset_confirm"  # confirm and validate_token share this

    kind = models.CharField(max_length=30)
    key_hash = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["kind", "created_at"])]


class StudentDepartmentHistory(models.Model):
    """Which department a student belonged to, and when (DATA-02, BE-02.2).

    Past season results read this, so a department change never rewrites
    history. The user FK is PROTECT on purpose: history must survive. Names
    are snapshotted so a later rename does not alter the past. Faculty and
    department FKs are SET_NULL so nothing here can block registry cleanup.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="department_history"
    )
    faculty = models.ForeignKey(
        "core.Faculty", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    department = models.ForeignKey(
        "core.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    faculty_name = models.CharField(max_length=200, blank=True)
    department_name = models.CharField(max_length=200, blank=True)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)  # null = current
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-effective_from", "-id"]
        constraints = [
            # At most one current department per student.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(effective_to__isnull=True),
                name="uniq_open_department_history_per_user",
            )
        ]
        indexes = [models.Index(fields=["user", "effective_from"])]

    def __str__(self):
        return f"{self.user_id}: {self.department_name} ({self.effective_from:%Y-%m-%d})"

class DepartmentChangeApproval(models.Model):
    """An admin's one-time permission for a student to change department
    again within the same semester (BE-02.2). Consumed by the next change.

    CASCADE is fine here: it is a disposable permission, not history. The
    audit log keeps the permanent record of who approved what.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="department_change_approvals"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} approved ({'used' if self.used_at else 'unused'})"


class WorldHandoffToken(models.Model):
    """One-time key that carries a signed-in student from the Flutter app into
    the web world (BE-01.3, decision D-8).

    Only the SHA-256 hash of the key is stored, never the key itself. It is
    bound to one user, lives a few seconds, and works once. CASCADE is fine:
    it is a disposable credential, not history (the audit log keeps the record).
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"handoff for user {self.user_id} ({'used' if self.used_at else 'unused'})"