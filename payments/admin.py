from django.contrib import admin
from .models import BankDetails, PayoutBatch, WorkerSalaryRecord

admin.site.register(BankDetails)
admin.site.register(PayoutBatch)
admin.site.register(WorkerSalaryRecord)