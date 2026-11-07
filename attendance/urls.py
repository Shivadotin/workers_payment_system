from django.urls import path 
from . import views

app_name = "attendance"

urlpatterns = [
    path("mark_attendance/" , views.mark_attendance , name = 'mark-attendance'),
    path("attendance_history/" , views.attendance_history , name = 'attendance-history'),
    path("worker_attendance_history/" , views.worker_attendance , name = 'worker-attendance')
]