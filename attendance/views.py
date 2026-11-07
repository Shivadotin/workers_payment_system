from django.shortcuts import render , redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Attendance
from accounts.models import User
from datetime import date , datetime
from collections import defaultdict
from datetime import date as date_class
from django.utils import timezone
from django.contrib import messages 

user = get_user_model()

@login_required
def mark_attendance(request):

    if request.user.role != "SUPERWISER":
        return redirect("authenti:login")

    # workers = user.objects.filter(role = "WORKER"  , superwiser= request.user)
    workers = request.user.workers.all()

    if request.method == 'POST':
        date_input = request.POST.get('date')

        try:
            date = date_class.fromisoformat(date_input)
        except (ValueError, TypeError):
            messages.error(request, "Please select a valid date.")
            return redirect('attendance:mark-attendance')

        if date > timezone.localdate():
            messages.error(request, "Future attendance dates are not allowed.")
            return redirect('attendance:mark-attendance')

        if date < timezone.localdate():
            messages.error(request , "past attendance dates are not allowed")
            return redirect('attendance:mark-attendance')

        for worker in workers:
            status = request.POST.get(f"attendance_{worker.id}")

            if status in ["PRESENT" , "ABSENT"]:
                Attendance.objects.update_or_create(worker = worker , date = date ,  defaults = {"status" : status})

        return redirect('attendance:attendance-history')


    return render(request , "mark_attendance.html" , {"workers" : workers})




@login_required
def attendance_history(request):

    if request.user.role != "SUPERWISER":
        return redirect("authenti:login")

    workers = user.objects.filter( role = "WORKER" , superwiser = request.user)

    attendance = Attendance.objects.filter(worker__in = workers).order_by("-date" )
    dates = attendance.values_list('date' , flat= True).distinct().order_by("-date" )


    daily_data = []

    for date in dates:

        records = attendance.filter(date=date)

        absent = records.filter(status="ABSENT").count()
        present = records.filter(status = "PRESENT").count()

        daily_data.append({  "date": date, "records": records, "absent": absent,"present" : present,   })

    return render(request , "attendance_history.html" , {'attendance' : attendance , 'dates': dates ,"daily_data" : daily_data })





@login_required
def worker_attendance(request):
    if request.user.role != "SUPERWISER":
        return redirect("authenti:login")

    attendance = Attendance.objects.filter(worker = request.user).order_by("-date")
    return render(request, "worker_attendance_history.html" , {"attendance": attendance})
