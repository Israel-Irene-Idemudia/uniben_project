import secrets
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

def gen_token():
    return secrets.token_urlsafe(48)

class Exam(models.Model):
    title = models.CharField(max_length=255)
    course = models.ForeignKey('core.Course', on_delete=models.CASCADE, null=True, blank=True)  # change if no courses app
    instructions = models.TextField(blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    shuffle_questions = models.BooleanField(default=True)
    negative_mark = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0'))
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    QTYPE_MCQ = 'mcq'
    QTYPE_MULTI = 'multi'
    QTYPE_TEXT = 'text'
    QTYPE_CHOICES = [
        (QTYPE_MCQ, 'Single choice'),
        (QTYPE_MULTI, 'Multiple choice'),
        (QTYPE_TEXT, 'Text answer'),
    ]

    text = models.TextField()
    qtype = models.CharField(max_length=10, choices=QTYPE_CHOICES, default=QTYPE_MCQ)
    marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1'))
    attachment = models.FileField(upload_to='question_files/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        txt = self.text[:75]
        return f"Q{self.id}: {txt}"

class Option(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=2000)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text[:80]

class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_questions', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class ExamSession(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_GRADED = 'graded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In progress'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_GRADED, 'Graded'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=128, unique=True, default=gen_token)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    answers_json = models.JSONField(default=dict, blank=True)  # {"<question_id>": {"selected_option_ids":[..], "text":".."}}
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=512, blank=True)

    def remaining_seconds(self):
        if not self.started_at:
            return self.exam.duration_minutes * 60
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, self.exam.duration_minutes * 60 - int(elapsed))

    def __str__(self):
        return f"Session {self.token[:8]} for {self.student}"

