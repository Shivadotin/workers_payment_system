from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from attendance.models import Attendance
from .gateway import create_transfer, PaymentGatewayError
from .models import PayoutBatch, WorkerSalaryRecord
from django.conf import settings



def daily_wage():
    return Decimal(settings.DAILY_WAGE)


def current_week():
    
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=5)


def build_breakdown(superwiser, start, end):
    breakdown = []
    total = Decimal('0')
    for worker in superwiser.workers.all():
        days = Attendance.objects.filter(
            worker=worker, date__range=[start, end], status="PRESENT"
        ).count()
        if days:
            amount = days * daily_wage()
            breakdown.append({
                "worker": worker, "days": days, "amount": amount,
                "has_bank": hasattr(worker, "bank_details"),
            })
            total += amount
    return breakdown, total


@transaction.atomic
def create_batch(admin, superwiser, start, end, breakdown, total):
    batch = PayoutBatch.objects.create(
        admin=admin, superwiser=superwiser,
        period_start=start, period_end=end, total_amount=total,
    )
    WorkerSalaryRecord.objects.bulk_create([
        WorkerSalaryRecord(
            batch=batch, worker=item["worker"],
            days_present=item["days"], amount=item["amount"],
        )
        for item in breakdown
    ])
    return batch


def process_batch(batch):
    batch.status = "PROCESSING"
    batch.save(update_fields=["status"])

    for record in batch.worker_records.exclude(status="SUCCESS").select_related("worker"):
        bank = getattr(record.worker, "bank_details", None)
        try:
            result = create_transfer(bank, record.amount, str(record.idempotency_key))
            record.transfer_id = result["id"]
            record.status = "SUCCESS" if result["status"] == "succeeded" else "FAILED"
            record.failure_reason = ""
        except PaymentGatewayError as e:
            record.status = "FAILED"
            record.failure_reason = str(e)
        record.save()

    statuses = set(batch.worker_records.values_list("status", flat=True))
    if statuses == {"SUCCESS"}:
        batch.status = "SUCCESS"
    elif "SUCCESS" in statuses:
        batch.status = "PARTIAL"
    else:
        batch.status = "FAILED"
    batch.save(update_fields=["status"])