from django.db import models

class Course(models.Model):
    # Core course information
    code = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    
    # Academic level and semester
    level = models.IntegerField(null=True, blank=True, help_text="Academic level (100, 200, 300, 400, 500)")
    semester = models.IntegerField(null=True, blank=True, help_text="Semester number (1, 2, 3)")
    
    # Faculty information
    faculty_code = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    faculty_title = models.CharField(max_length=255, null=True, blank=True)
    
    # Department information
    department_code = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    department_title = models.CharField(max_length=255, null=True, blank=True)
    
    # Certificate/Program information
    certificate_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    certificate_title = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['faculty_code', 'department_code', 'level', 'semester', 'code']
        indexes = [
            models.Index(fields=['faculty_code', 'department_code']),
            models.Index(fields=['level', 'semester']),
        ]

    def __str__(self):
        if self.title:
            return f"{self.code} - {self.title}"
        return self.code
    
    def get_full_info(self):
        """Returns a dictionary with complete course information"""
        return {
            'code': self.code,
            'title': self.title,
            'level': self.level,
            'semester': self.semester,
            'faculty': {
                'code': self.faculty_code,
                'title': self.faculty_title,
            },
            'department': {
                'code': self.department_code,
                'title': self.department_title,
            },
            'certificate': {
                'code': self.certificate_code,
                'title': self.certificate_title,
            }
        }
