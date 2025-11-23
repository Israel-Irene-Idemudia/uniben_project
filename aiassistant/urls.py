from django.urls import path
from .views import upload_file, LumoraChatView, CbtExplanationView, PdfSummaryView

urlpatterns = [
    path("upload/", upload_file, name="upload_file"),
    path("lumora-chat/", LumoraChatView.as_view(), name="lumora-chat"),
    path("cbt-explanation/", CbtExplanationView.as_view(), name="cbt-explanation"),
    path("pdf-summary/", PdfSummaryView.as_view(), name="pdf-summary"),
]
