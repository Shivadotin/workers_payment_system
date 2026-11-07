from django.shortcuts import render
from django.db import models
from django.db.models import Sum
from decimal import Decimal

# Create your views here.
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404

from .models import BankDetails
from payments.models import PayoutBatch, WorkerSalaryRecord, BankDetails
from .services import current_week, build_breakdown, create_batch, process_batch
from .forms import BankDetailsForm
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_POST
from .funding import create_order, verify_signature, FundingError
from datetime import date
from decimal import Decimal

from django.db.models import Sum

User = get_user_model()


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return redirect('authenti:login')
        return view(request, *args, **kwargs)
    return wrapper


@admin_required
def select_superwiser(request):
    start, end = current_week()
    data = []

    for sup in User.objects.filter(role="SUPERWISER"):
        breakdown, total = build_breakdown(sup, start, end)

        batch = PayoutBatch.objects.filter(
            superwiser=sup,
            period_start=start,
            period_end=end
        ).first()

        data.append({
            "superwiser": sup,
            "worker_count": len(breakdown),
            "pending_total": total,
            "batch": batch,
        })

    total_workers = sum(row["worker_count"] for row in data)
    total_weekly_wages = sum(row["pending_total"] for row in data)

    return render(request, "payments/select_superwiser.html", {
        "data": data,
        "start": start,
        "end": end,
        "total_workers": total_workers,
        "total_weekly_wages": total_weekly_wages,
    })


@admin_required
def confirm_payout(request, superwiser_id):
    superwiser = get_object_or_404(User, id=superwiser_id, role="SUPERWISER")
    start, end = current_week()

    existing = PayoutBatch.objects.filter(
        superwiser=superwiser, period_start=start, period_end=end
    ).first()
    if existing:
        messages.info(request, "This team already has a payout for this week.")
        return redirect('payments:batch-detail', batch_id=existing.id)

    breakdown, total = build_breakdown(superwiser, start, end)

    if request.method == "POST":
        if not breakdown:
            messages.error(request, "No present days this week, nothing to pay.")
            return redirect('payments:select-superwiser')
        try:
            batch = create_batch(request.user, superwiser, start, end, breakdown, total)
        except IntegrityError:  # double click or two admins at once
            messages.error(request, "A payout for this week already exists.")
            return redirect('payments:select-superwiser')
        # process_batch(batch)
        # return redirect('payments:batch-detail', batch_id=batch.id)
        if settings.REQUIRE_FUNDING:
            return redirect('payments:fund-batch', batch_id=batch.id)
        process_batch(batch)

    return render(request, "payments/confirm_payout.html", {
        "superwiser": superwiser, "breakdown": breakdown,
        "total": total, "start": start, "end": end,
    })


@admin_required
def batch_detail(request, batch_id):
    batch = get_object_or_404(PayoutBatch, id=batch_id)

    if request.method == "POST" and batch.status in ("PARTIAL", "FAILED"):
        process_batch(batch)  # retries only the workers not yet paid
        messages.info(request, "Retry finished.")
        return redirect('payments:batch-detail', batch_id=batch.id)

    return render(request, "payments/batch_detail.html", {
        "batch": batch, "records": batch.worker_records.select_related("worker"),
    })


@login_required
def my_bank_details(request):
    if request.user.role != "WORKER":
        return redirect('authenti:login')

    instance = BankDetails.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = BankDetailsForm(request.POST, instance=instance)
        if form.is_valid():
            details = form.save(commit=False)
            details.user = request.user   # always the logged-in worker, never from the form
            details.save()
            messages.success(request, "Bank details saved.")
            return redirect('authenti:worker-dashboard')
    else:
        form = BankDetailsForm(instance=instance)

    return render(request, "payments/bank_details.html", {"form": form, "has_details": bool(instance)})


@admin_required
def fund_batch(request, batch_id):
    batch = get_object_or_404(PayoutBatch, id=batch_id)
    if batch.status != "PENDING":
        return redirect('payments:batch-detail', batch_id=batch.id)

    if not batch.razorpay_order_id:
        try:
            batch.razorpay_order_id = create_order(batch)
            batch.save(update_fields=["razorpay_order_id"])
        except FundingError as e:
            messages.error(request, str(e))
            return redirect('payments:batch-detail', batch_id=batch.id)

    return render(request, "payments/fund_batch.html", {
        "batch": batch,
        "key_id": settings.RAZORPAY_KEY_ID,
        "amount_paise": int(batch.total_amount * 100),
    })


@admin_required
@require_POST
def verify_payment(request, batch_id):
    batch = get_object_or_404(PayoutBatch, id=batch_id)
    if batch.status != "PENDING" or batch.razorpay_payment_id:
        return redirect('payments:batch-detail', batch_id=batch.id)   # already handled

    order_id = request.POST.get("razorpay_order_id", "")
    payment_id = request.POST.get("razorpay_payment_id", "")
    signature = request.POST.get("razorpay_signature", "")

    # the order id must be the one WE created for this batch, and the signature must match
    if order_id != batch.razorpay_order_id or not verify_signature(order_id, payment_id, signature):
        messages.error(request, "Payment could not be verified. No money was released.")
        return redirect('payments:batch-detail', batch_id=batch.id)

    batch.razorpay_payment_id = payment_id
    batch.funded_at = timezone.now()
    batch.save(update_fields=["razorpay_payment_id", "funded_at"])
    process_batch(batch)
    return redirect('payments:batch-detail', batch_id=batch.id)


@admin_required
def payment_reports(request):
    today = timezone.localdate()
    default_start = today.replace(day=1)

    # Read the selected reporting period.
    try:
        start_date = date.fromisoformat(
            request.GET.get("start_date", "")
        )
    except (ValueError, TypeError):
        start_date = default_start

    try:
        end_date = date.fromisoformat(
            request.GET.get("end_date", "")
        )
    except (ValueError, TypeError):
        end_date = today

    # Prevent an invalid date range.
    if start_date > end_date:
        messages.error(request, "Start date cannot be after end date.")
        start_date = default_start
        end_date = today

    # Select batches whose start date falls in the chosen period.
    batches = PayoutBatch.objects.filter(
        period_start__gte=start_date,
        period_start__lte=end_date,
    ).select_related("superwiser", "admin")

    records = WorkerSalaryRecord.objects.filter(
        batch__in=batches
    ).select_related(
        "worker", "batch", "batch__superwiser"
    ).order_by(
        "-batch__period_start", "worker__username"
    )

    # Calculate totals from individual worker payment records.
    totals = records.aggregate(
        paid=Sum("amount", filter=models.Q(status="SUCCESS")),
        pending=Sum("amount", filter=models.Q(status="PENDING")),
        failed=Sum("amount", filter=models.Q(status="FAILED")),
    )

    total_paid = totals["paid"] or Decimal("0.00")
    total_pending = totals["pending"] or Decimal("0.00")
    total_failed = totals["failed"] or Decimal("0.00")

    # Summarize payments for each Superwiser.
    superwiser_ids = batches.values_list(
        "superwiser_id", flat=True
    ).distinct()

    superwiser_reports = []

    for superwiser_id in superwiser_ids:
        supervisor_records = records.filter(
            batch__superwiser_id=superwiser_id
        )

        amounts = supervisor_records.aggregate(
            paid=Sum("amount", filter=models.Q(status="SUCCESS")),
            pending=Sum("amount", filter=models.Q(status="PENDING")),
            failed=Sum("amount", filter=models.Q(status="FAILED")),
        )

        superwiser_reports.append({
            "superwiser": batches.filter(
                superwiser_id=superwiser_id
            ).first().superwiser,
            "paid": amounts["paid"] or Decimal("0.00"),
            "pending": amounts["pending"] or Decimal("0.00"),
            "failed": amounts["failed"] or Decimal("0.00"),
            "worker_count": supervisor_records.values(
                "worker_id"
            ).distinct().count(),
        })

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "total_failed": total_failed,
        "worker_count": records.values("worker_id").distinct().count(),
        "superwiser_reports": superwiser_reports,
        "records": records,
    }

    return render(request, "payments/reports.html", context)
