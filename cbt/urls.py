from django.urls import path
from .views import ExamListView, StartExamView, AutoSaveView, SubmitView

urlpatterns = [
    path('', ExamListView.as_view(), name='cbt-exam-list'),
    path('<int:exam_id>/start/', StartExamView.as_view(), name='cbt-exam-start'),
    path('sessions/<str:token>/autosave/', AutoSaveView.as_view(), name='cbt-autosave'),
    path('sessions/<str:token>/submit/', SubmitView.as_view(), name='cbt-submit'),
]
