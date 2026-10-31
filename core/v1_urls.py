from django.urls import path

from core.v1_views import DepartmentListView, FacultyListView, UniversityListView

urlpatterns = [
    path("universities", UniversityListView.as_view(), name="v1-universities"),
    path("universities/", UniversityListView.as_view()),
    path("faculties", FacultyListView.as_view(), name="v1-faculties"),
    path("faculties/", FacultyListView.as_view()),
    path("departments", DepartmentListView.as_view(), name="v1-departments"),
    path("departments/", DepartmentListView.as_view()),
]