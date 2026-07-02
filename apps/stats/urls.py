from django.urls import path

from .views import DashboardView, WorkEntryListView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("entries/", WorkEntryListView.as_view(), name="work-entry-list"),
]
