from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path('select-superwiser/', views.select_superwiser, name='select-superwiser'),
    path('confirm/<int:superwiser_id>/', views.confirm_payout, name='confirm-payout'),
    path('batch/<int:batch_id>/', views.batch_detail, name='batch-detail'),
    path('my-bank-details/', views.my_bank_details, name='my-bank-details'),
    path('batch/<int:batch_id>/fund/', views.fund_batch, name='fund-batch'),
    path('batch/<int:batch_id>/verify/', views.verify_payment, name='verify-payment'),
    path("reports/", views.payment_reports, name="reports"),
]