from django.contrib import admin
from .models import Exam, Question, Option, ExamQuestion, ExamSession, DebaterQuestion

class OptionInline(admin.TabularInline):
    model = Option
    extra = 2

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'qtype', 'marks', 'created_at')
    search_fields = ('text',)
    inlines = [OptionInline]

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id','title','duration_minutes','is_published','created_at')
    search_fields = ('title',)
    filter_horizontal = ()  # if you add ManyToMany members later

@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ('exam','question','order')

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ('token','exam','student','status','score','started_at','submitted_at')
    readonly_fields = ('answers_json',)


@admin.register(DebaterQuestion)
class DebaterQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'statement_preview', 'answer', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'answer')
    search_fields = ('statement',)
    list_editable = ('is_active',)
    
    def statement_preview(self, obj):
        return obj.statement[:60] + '...' if len(obj.statement) > 60 else obj.statement
    statement_preview.short_description = 'Statement'
