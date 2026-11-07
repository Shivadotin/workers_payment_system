from django.shortcuts import render ,redirect , get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import authenticate , login , logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from .models import ResetPasword
from accounts.forms import SuperwiserCreatinForm ,WorkerCreationForm ,WorkerUpdateForm
from attendance.models import Attendance
from datetime import date, timedelta
from payments.models import WorkerSalaryRecord
from django.db.models import Sum
from attendance.models import Attendance
from payments.models import WorkerSalaryRecord



User = get_user_model()

@login_required
def home(request):
    return render(request ,"index.html")

def register(request):  
    if request.method == 'POST' :
        user_name = request.POST['username']
        first_name = request.POST['First_name']
        last_name = request.POST['Last_name']
        email = request.POST['Email']
        password = request.POST['password']
        password1 = request.POST['password1']

        user_has_error = False

        if User.objects.filter(username = user_name).exists():
            user_has_error =True 
            messages.error(request , "user already exists")
            return redirect('authenti:register')

        if User.objects.filter(email = email).exists():
            user_has_error = True
            messages.error(request ,f"user with { email} already exists")
            return redirect('authenti:register')

        if password != password1:
            user_has_error = True
            messages.error(request , "recheck your password")
            return redirect('authenti:register')

        if len(password) <= 4 :
            user_has_error = True
            messages.error(request , "password must contain 4 characters")
            return redirect('authenti:register')

        if not user_has_error:
            new_user = User.objects.create_user(
                username= user_name,
                first_name = first_name,
                last_name = last_name ,
                email = email,
                password= password,
            )
            messages.success(request , f"{user_name } create successfully!")
            return redirect('authenti:login')

    return render(request , 'register.html')



def loginView(request):
    if request.method == "POST" :
        user_name = request.POST['username']
        password = request.POST['password']

        user = authenticate(request = request , username = user_name , password = password)

        if user is not None:
            login(request,user)
            messages.success(request , "user logged in successfully!    ")

            if user.role == "ADMIN":
                return redirect('authenti:admin-dashboard')

            elif user.role == "SUPERWISER":
                return redirect('authenti:superwiser-dashboard')

            elif user.role == "WORKER":                
                return redirect('authenti:worker-dashboard')
            
            # return redirect('authenti:home')

        else:
            messages.error(request , "invalid username or password")
    return render(request , 'login.html')

def logoutView(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("authenti:login")

    


def ForgotPassword(request):
    if request.method == 'POST':
        Email = request.POST['Email']
        try:
            user = User.objects.get(email=Email)

            new_password_reset = ResetPasword(user = user)
            new_password_reset.save()

            password_reset_url = reverse('authenti:reset-password' , kwargs={'reset_id' : new_password_reset.reset_id})
            full_password_reset_url = f"{request.scheme}://{request.get_host()}{password_reset_url}"
            email_body = f"welcome to the login system \n\n please reset your password to login by using the link given below\n\n {full_password_reset_url}" 

            email_message = EmailMessage(
                'Reset your Password' ,
                email_body ,
                settings.EMAIL_HOST_USER ,
                [Email] ,
            )

            email_message.fail_silently = True
            email_message.send()
            messages.success(request , "check your email")
            return redirect("authenti:forgot-password" )


        except User.DoesNotExist:
            messages.error(request , f"No User With Email '{Email}' found ")
            return redirect("authenti:forgot-password")

        

    return render(request , 'forgot_password.html')


def PasswordResetSent(request , reset_id):
    if ResetPasword.objects.filter(reset_id = reset_id).exists():
        return render(request , 'reset_password_sent.html')

    else:
        messages.error(request , "invalid reset id")
        return redirect('authenti:forgot-password')
    


def RestPassword(request , reset_id):

    try:
        password_reset_id = ResetPasword.objects.get(reset_id=reset_id)

        if request.method == 'POST':
            password = request.POST['password']
            confirm_password = request.POST['confirm_password']

            passwords_has_erorr= False

            if password != confirm_password:
                passwords_has_erorr =True
                messages.error(request , "re-check your entered password")

            if len(password) <=4 :
                passwords_has_erorr =True 
                messages.error(request , "password must be atleast 4 characters")


            expiration_time = password_reset_id.created_at + timezone.timedelta(minutes = 10)

            if timezone.now() > expiration_time :
                passwords_has_erorr = True
                messages.error(request , "Rest link has expired")

                password_reset_id.delete()


            if not passwords_has_erorr:
                user = password_reset_id.user
                user.set_password(password)
                user.save()

                password_reset_id.delete()

                messages.success(request , "password is reseted . now user can login ")
                return redirect('authenti:login')

            else:
                return redirect('authenti:reset-password' , reset_id = reset_id)


    except ResetPasword.DoesNotExist:
        messages.error(request , "invalid reset Id")
        return redirect("authenti:forgot-password")
    return render(request , 'reset_pasword.html')


@login_required
def AdminDashboard(request):
    if request.user.role != "ADMIN":
        return redirect('authenti:login')
    
    return render(request , 'admin_dashboard.html')

@login_required
def SuperwiserDashboard(request):
    if request.user.role != "SUPERWISER":
        return redirect('authenti:login')

    workers = request.user.workers.all()

    
    return render(request , 'superwiser_dashboard.html' , {'workers': workers})

@login_required
def WorkerDashboard(request):
    if request.user.role != "WORKER":
        return redirect('authenti:login')

    today =timezone.localdate()
    monday = today - timedelta(days = today.weekday())
    saturday = monday + timedelta(days = 5)


    # attendance = Attendance.objects.filter( worker = request.user, date__range = [monday , saturday]    ).order_by("-date" )
    attendance = Attendance.objects.filter(worker=request.user).order_by("-date")

    daily_wage = settings.DAILY_WAGE

    weekly_attendance = attendance.filter(date__range=[monday, saturday])
    weekly_present = weekly_attendance.filter( status="PRESENT" ).count()
    weekly_earnings = weekly_present * daily_wage
    present_days = attendance.filter(status = "PRESENT").count()
    absent_days = attendance.filter(status = "ABSENT").count()
    total_days = present_days + absent_days
    weekly_present = weekly_attendance.filter(status = "PRESENT").count()
    weekly_absent = weekly_attendance.filter(status = "ABSENT").count() 
    total_salary = present_days * daily_wage
    total_lifetime_earnings = present_days * daily_wage
    all_payments = WorkerSalaryRecord.objects.filter( worker=request.user)

    payments = all_payments.select_related("batch", "batch__superwiser").order_by("-batch__created_at")[:10]

    # Actual payment totals, based on individual payment statuses.
    payment_totals = all_payments.aggregate(
        paid=Sum("amount", filter=__import__("django.db.models", fromlist=["Q"]).Q(status="SUCCESS")),
        pending=Sum("amount", filter=__import__("django.db.models", fromlist=["Q"]).Q(status="PENDING")),
        failed=Sum("amount", filter=__import__("django.db.models", fromlist=["Q"]).Q(status="FAILED")), )

    total_paid = payment_totals["paid"] or 0
    total_pending = payment_totals["pending"] or 0
    total_failed = payment_totals["failed"] or 0
   # payments = (WorkerSalaryRecord.objects.filter(worker = request.user).select_related("batch").order_by("-batch__created_at")[:10])
    has_bank_details = hasattr(request.user, "bank_details")
    return render(request , 'worker_dashboard.html' , { "attendance": attendance ,"present_days" : present_days ,  "absent_days": absent_days , "total_days": total_days ,  "weekly_present" :weekly_present, "weekly_absent" : weekly_absent ,"weekly_earnings": weekly_earnings,"total_salary" : total_salary ,"daily_wage" : daily_wage , "monday" : monday ,  "saturay" : saturday ,"payments" : payments ,"has_bank_details": has_bank_details ,"total_lifetime_earnings": total_lifetime_earnings, "total_paid" : total_paid , "total_failed" : total_failed , "total_pending":total_pending, }  )

@login_required
def create_superwiser(request):
    
    if request.user.role != "ADMIN":
        return redirect("authenti:login")

    form = SuperwiserCreatinForm()
    
    if request.method == 'POST':
        form = SuperwiserCreatinForm(request.POST)

        if form.is_valid():
            superwiser = form.save(commit=False)
            superwiser.role = "SUPERWISER"                      

            superwiser.set_password(form.cleaned_data["password"])

            superwiser.save()
            messages.success(request , "supervisor created successfully")
            return redirect('authenti:admin-dashboard')

        else:

            form = SuperwiserCreatinForm()

    return render(request , 'create_superwiser.html' , {'form':form})

@login_required
def create_worker(request):

    if request.user.role not in  ["ADMIN" , "SUPERWISER"]:
        return redirect('authenti:login')

    

    if request.method  == "POST" :
        form =  WorkerCreationForm(request.POST)

        if form.is_valid():
            worker = form.save(commit = False)
            worker.role = "WORKER"
            worker.superwiser = request.user
            worker.set_password(form.cleaned_data['password'])
            worker.save()
            messages.success(request , "worker created successfully")

            if request.user.role == "ADMIN" :
                return redirect('authenti:admin-dashboard')

            if request.user.role == "SUPERWISER" : 
                return redirect('authenti:superwiser-dashboard')

    else:
        form = WorkerCreationForm()

    return render(request , 'create_worker.html' , {'form':form})

@login_required
def worker_profile(request , id):
    if request.user.role != "SUPERWISER":
        return redirect('authenti:login')

    worker =  get_object_or_404(User,id = id,role = "WORKER" , superwiser = request.user)

    return render(request , 'worker_profile.html' , {'worker':worker})

@login_required
def edit_worker(request , id):
    if request.user.role != "SUPERWISER":
        return redirect('authenti:login')

    worker =  get_object_or_404(User,id = id,role = "WORKER" , superwiser = request.user)   
    if request.method == "POST":
        form = WorkerUpdateForm( request.POST , instance = worker)

        if form.is_valid():
            worker = form.save(commit=False)
            worker.role ="WORKER"
            worker.save()
            messages.success(request , "updated successfully!")
            return redirect("authenti:worker-profile"  , id = worker.id)

    else:

        form = WorkerUpdateForm(instance=worker)
            # return redirect('authenti:edit-worker' , id = worker.id)

    return render(request , "edit_worker.html"  , {"form" : form , "worker":worker})

@login_required
def delete_worker(request ,id):
    if request.user.role != "SUPERWISER":
        return redirect('authenti:login')

    worker =  get_object_or_404(User,id = id,role = "WORKER" , superwiser = request.user)
    if request.method == 'POST':
        worker.delete()
        messages.success(request , "woker deleted successfully")
        return redirect("authenti:superwiser-dashboard")

    return render(request , 'delete_worker.html' , {'worker':worker})


    