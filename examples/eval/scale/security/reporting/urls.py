from django.urls import path

from .views import ReportListView

app_name = "reporting"

urlpatterns = [
    path("reports/", ReportListView.as_view(), name="report-list"),
]
