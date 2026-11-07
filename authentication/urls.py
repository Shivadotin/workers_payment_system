from django.urls import path
from . import views

app_name = "authenti"

urlpatterns = [
        path('' , views.home , name = "home" ),
        path('login/' , views.loginView, name = "login"),
        path('register/' , views.register , name = "register"),
        path('logout/' ,  views.logoutView , name = "logout"),
        path('forgot_password/' , views.ForgotPassword , name = "forgot-password"),
        path('passwordresetsent/<str:reset_id>/' , views.PasswordResetSent , name = "password-reset-sent"),
        path('reset_password/<str:reset_id>/' , views.RestPassword , name = "reset-password"),
        path('admin_dashboard/' , views.AdminDashboard , name = "admin-dashboard"),
        path('superwiser_dashboard/' , views.SuperwiserDashboard , name = "superwiser-dashboard"),
        path('worker_dashboard/' , views.WorkerDashboard , name = "worker-dashboard"),
        path('create_superwiser/' , views.create_superwiser , name = "create-superwiser"),
        path('create_worker/' , views.create_worker , name = "create-worker"),
        path('worker/<int:id>/view' , views.worker_profile , name = "worker-profile"),
        path('worker/<int:id>/edit' , views.edit_worker , name= "edit-worker"),
        path('worker/<int:id>/delete' , views.delete_worker , name= "delete-worker"),

]