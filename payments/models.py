from django.db import models

import uuid
from django.db import models
from django.conf import settings


class BankDetails(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bank_details'
    )
    account_holder_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    ifsc = models.CharField(max_length=11)
    upi_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Bank details for {self.user.username}"


class PayoutBatch(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('PARTIAL', 'Partially paid'),
        ('FAILED', 'Failed'),
    )

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payouts_made'
    )
    superwiser = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payouts_received'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    razorpay_order_id = models.CharField(max_length=40, blank=True, default="")
    razorpay_payment_id = models.CharField(max_length=40, blank=True, default="")
    funded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['superwiser', 'period_start', 'period_end'],
                name='one_batch_per_superwiser_per_period',
            )
        ]

    def __str__(self):
        return f"Payout for {self.superwiser.username}'s team - {self.total_amount} ({self.status})"


class WorkerSalaryRecord(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    batch = models.ForeignKey(PayoutBatch, on_delete=models.CASCADE, related_name='worker_records')
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    days_present = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    transfer_id = models.CharField(max_length=60, blank=True, null=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return f"{self.worker.username} - {self.amount} ({self.status})"