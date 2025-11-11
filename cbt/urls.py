from django.urls import path
from .views import (
    ExamListView, 
    StartExamView, 
    AutoSaveView, 
    SubmitView,
    UserSubscribedCoursesWithQuizzes
)

urlpatterns = [
    # MODIFIED: Changed the URL to be nested under a course
    path('courses/<int:course_id>/exams/', ExamListView.as_view(), name='cbt-exam-list'),
    # This URL is for getting the user's courses that have quizzes
    path('my-courses/', UserSubscribedCoursesWithQuizzes.as_view(), name='cbt-my-courses'),
    
    path('<int:exam_id>/start/', StartExamView.as_view(), name='cbt-exam-start'),
    path('sessions/<str:token>/autosave/', AutoSaveView.as_view(), name='cbt-autosave'),
    path('sessions/<str:token>/submit/', SubmitView.as_view(), name='cbt-submit'),
]
