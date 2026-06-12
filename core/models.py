from django.db import models
from django.conf import settings

class Faculty(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=200)
    faculty = models.ForeignKey('core.Faculty', on_delete=models.CASCADE, related_name='departments')

    def __str__(self):
        return f"{self.faculty.name} - {self.name}"


class CourseArea(models.Model):  # optional (for departments that have areas)
    name = models.CharField(max_length=200)
    department = models.ForeignKey('core.Department', on_delete=models.CASCADE, related_name='course_areas')

    def __str__(self):
        return f"{self.department.name} - {self.name}"


class Level(models.Model):
    name = models.CharField(max_length=20)  # e.g. "100L", "200L"
    department = models.ForeignKey('core.Department', on_delete=models.CASCADE, related_name='levels')
    course_area = models.ForeignKey('core.CourseArea', on_delete=models.CASCADE, null=True, blank=True, related_name='levels')

    def __str__(self):
        return f"{self.department.name} - {self.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['department', 'course_area', 'name'],
                name='uniq_level_per_dept_area_name',
            )
        ]


class Course(models.Model):
    code = models.CharField(max_length=20)   # e.g. "MTH101"
    title = models.CharField(max_length=200)
    # ADDED: semester field as an integer.
    semester = models.IntegerField(default=1) # Using 1 for 1st semester, 2 for 2nd
    level = models.ForeignKey('core.Level', on_delete=models.CASCADE, related_name='courses')

    def __str__(self):
        return f"{self.code} - {self.title} ({self.semester} Semester)"

    class Meta:
        constraints = [
             # UPDATED: The constraint now includes 'semester' to ensure a course
             # code is unique within a specific level and semester.
            models.UniqueConstraint(
                fields=['level', 'code', 'semester'],
                name='uniq_course_per_level_semester',
            )
        ]

class ContactMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject


class CampusLocation(models.Model):
    """
    Represents a point of interest on the campus map.
    Managed via admin panel - no app updates needed for new locations.
    """
    CATEGORY_CHOICES = [
        ('faculty', 'Faculty'),
        ('hostel', 'Hostel'),
        ('admin', 'Admin'),
        ('landmark', 'Landmark'),
        ('sports', 'Sports'),
        ('health', 'Health'),
        ('religious', 'Religious'),
        ('commercial', 'Commercial'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='landmark')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    description = models.TextField(blank=True, help_text="Optional description or directions")
    is_active = models.BooleanField(default=True, help_text="Inactive locations won't show on the map")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class GlobalPrompt(models.Model):
    """
    Singleton model to control the global 'Windows Prompt' or countdown alert.
    """
    PROMPT_TYPES = [
        ('STANDARD', 'Standard Announcement'),
        ('UPDATE', 'Actionable Update'),
        ('COUNTDOWN', 'Live Countdown'),
        ('CRITICAL', 'Critical/Non-dismissible Alert'),
    ]

    is_active = models.BooleanField(default=False)
    prompt_type = models.CharField(max_length=20, choices=PROMPT_TYPES, default='STANDARD')
    title = models.CharField(max_length=255)
    message = models.TextField()
    button_text = models.CharField(max_length=50, blank=True)
    action_route = models.CharField(max_length=255, blank=True)
    target_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Global Prompt'
        verbose_name_plural = 'Global Prompts'

    def save(self, *args, **kwargs):
        self.pk = 1 # Ensure this is a singleton
        super(GlobalPrompt, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1, defaults={'title': 'Welcome', 'message': 'Welcome to Skholar!'})
        return obj

    def __str__(self):
        return f"Global Prompt: {self.title} ({self.prompt_type})"
