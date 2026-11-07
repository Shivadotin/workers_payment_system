from django.test import TestCase
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from attendance.models import Attendance
from .models import BankDetails, PayoutBatch, WorkerSalaryRecord
from .services import build_breakdown, create_batch, process_batch, current_week
import hmac, hashlib

User = get_user_model()

START = date(2026, 10, 19)  # Monday
END = date(2026, 10, 24)    # Saturday


def make_user(username, role, superwiser=None):
    return User.objects.create_user(
        username=username, password="pass12345", role=role, superwiser=superwiser
    )


def mark(worker, day, status="PRESENT"):
    return Attendance.objects.create(worker=worker, date=day, status=status)


def add_bank(user):
    return BankDetails.objects.create(
        user=user, account_holder_name=user.username,
        account_number="123456789012", ifsc="SBIN0001234",
    )

@override_settings(DAILY_WAGE=300, REQUIRE_FUNDING=False, MOCK_PAYMENTS=True)
class PayoutTestBase(TestCase):
    def setUp(self):
        self.admin = make_user("admin1", "ADMIN")
        self.sup = make_user("sup1", "SUPERWISER")
        self.other_sup = make_user("sup2", "SUPERWISER")

        self.w1 = make_user("w1", "WORKER", self.sup)
        self.w2 = make_user("w2", "WORKER", self.sup)
        self.w3 = make_user("w3", "WORKER", self.sup)       # never present
        self.outsider = make_user("outsider", "WORKER", self.other_sup)

        for d in (19, 20, 21):
            mark(self.w1, date(2026, 10, d))                 # 3 days present
        mark(self.w2, date(2026, 10, 19))                    # 1 day present
        mark(self.w2, date(2026, 10, 20))                    # 1 day present
        mark(self.w2, date(2026, 10, 21), "ABSENT")          # absent, not paid
        mark(self.w1, date(2026, 10, 26))                    # outside the week
        mark(self.outsider, date(2026, 10, 19))              # other team# other team

    def make_batch(self):
        breakdown, total = build_breakdown(self.sup, START, END)
        return create_batch(self.admin, self.sup, START, END, breakdown, total)


class BuildBreakdownTests(PayoutTestBase):
    def test_total_counts_only_present_days_in_range(self):
        breakdown, total = build_breakdown(self.sup, START, END)
        print([(i["worker"].username, i["days"], i["amount"]) for i in breakdown], total)
        # w1: 3 days, w2: 2 days -> 5 days * 300
        self.assertEqual(total, Decimal("1500"))
        by_worker = {item["worker"].username: item for item in breakdown}
        self.assertEqual(by_worker["w1"]["days"], 3)
        self.assertEqual(by_worker["w2"]["days"], 2)

    def test_workers_with_no_present_days_are_left_out(self):
        breakdown, _ = build_breakdown(self.sup, START, END)
        names = [item["worker"].username for item in breakdown]
        self.assertNotIn("w3", names)

    def test_other_teams_are_never_included(self):
        breakdown, _ = build_breakdown(self.sup, START, END)
        names = [item["worker"].username for item in breakdown]
        self.assertNotIn("outsider", names)


@override_settings(MOCK_PAYMENTS=True)
class ProcessBatchTests(PayoutTestBase):
    def test_all_workers_with_bank_details_are_paid(self):
        add_bank(self.w1)
        add_bank(self.w2)
        batch = self.make_batch()

        process_batch(batch)

        batch.refresh_from_db()
        self.assertEqual(batch.status, "SUCCESS")
        for record in batch.worker_records.all():
            self.assertEqual(record.status, "SUCCESS")
            self.assertTrue(record.transfer_id.startswith("mock_tr_"))

    # def test_missing_bank_details_gives_partial(self):
    #     add_bank(self.w1)            # w2 has no bank details
    #     batch = self.make_batch()

    #     process_batch(batch)

    #     batch.refresh_from_db()
    #     self.assertEqual(batch.status, "PARTIAL")
    #     failed = batch.worker_records.get(worker=self.w2)
    #     self.assertEqual(failed.status, "FAILED")
    #     self.assertIn("no bank details", failed.failure_reason)

    def test_everyone_failing_gives_failed(self):
        batch = self.make_batch()    # nobody has bank details
        process_batch(batch)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "FAILED")

    def test_retry_pays_only_the_unpaid_worker(self):
        add_bank(self.w1)
        batch = self.make_batch()
        process_batch(batch)
        paid_id = batch.worker_records.get(worker=self.w1).transfer_id

        add_bank(self.w2)            # the missing worker fixes their details
        process_batch(batch)         # retry

        batch.refresh_from_db()
        self.assertEqual(batch.status, "SUCCESS")
        # w1 was not paid a second time: same transfer id as before
        self.assertEqual(batch.worker_records.get(worker=self.w1).transfer_id, paid_id)
        self.assertEqual(batch.worker_records.get(worker=self.w2).status, "SUCCESS")

    def test_batch_total_matches_sum_of_records(self):
        batch = self.make_batch()
        record_sum = sum(r.amount for r in batch.worker_records.all())
        self.assertEqual(batch.total_amount, record_sum)


class BatchConstraintTests(PayoutTestBase):
    def test_same_team_same_week_cannot_have_two_batches(self):
        self.make_batch()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_batch()
        self.assertEqual(PayoutBatch.objects.count(), 1)


@override_settings(MOCK_PAYMENTS=True)
class PayoutViewTests(PayoutTestBase):
    def setUp(self):
        super().setUp()
        # start from a clean slate so these tests don't depend on today's date
        Attendance.objects.all().delete()
        monday, _ = current_week()
        mark(self.w1, monday)
        add_bank(self.w1)

    def test_worker_cannot_open_payout_pages(self):
        self.client.login(username="w1", password="pass12345")
        response = self.client.get(reverse("payments:select-superwiser"))
        self.assertRedirects(response, reverse("authenti:login"), fetch_redirect_response=False)

    def test_supervisor_cannot_open_payout_pages(self):
        self.client.login(username="sup1", password="pass12345")
        response = self.client.get(reverse("payments:select-superwiser"))
        self.assertRedirects(response, reverse("authenti:login"), fetch_redirect_response=False)

    def test_get_request_never_creates_a_payout(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.get(reverse("payments:confirm-payout", args=[self.sup.id]))
        self.assertEqual(PayoutBatch.objects.count(), 0)

    def test_admin_post_pays_the_team(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.post(reverse("payments:confirm-payout", args=[self.sup.id]))
        batch = PayoutBatch.objects.get()
        self.assertEqual(batch.status, "SUCCESS")
        self.assertEqual(batch.total_amount, Decimal("300"))

    def test_second_post_does_not_pay_again(self):
        self.client.login(username="admin1", password="pass12345")
        url = reverse("payments:confirm-payout", args=[self.sup.id])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(PayoutBatch.objects.count(), 1)
        self.assertEqual(WorkerSalaryRecord.objects.count(), 1)


def sign(order_id, payment_id, secret="secret"):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


@override_settings(MOCK_PAYMENTS=True, REQUIRE_FUNDING=True,
                   RAZORPAY_KEY_ID="rzp_test_abc", RAZORPAY_KEY_SECRET="secret")
class FundingTests(PayoutTestBase):
    def setUp(self):
        super().setUp()
        add_bank(self.w1)
        add_bank(self.w2)
        self.batch = self.make_batch()
        self.batch.razorpay_order_id = "order_1"
        self.batch.save()
        self.client.login(username="admin1", password="pass12345")
        self.url = reverse("payments:verify-payment", args=[self.batch.id])

    def test_valid_signature_releases_payouts(self):
        self.client.post(self.url, {
            "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1",
            "razorpay_signature": sign("order_1", "pay_1"),
        })
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "SUCCESS")
        self.assertEqual(self.batch.razorpay_payment_id, "pay_1")

    def test_forged_signature_releases_nothing(self):
        self.client.post(self.url, {
            "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1",
            "razorpay_signature": "forged",
        })
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "PENDING")
        self.assertEqual(self.batch.razorpay_payment_id, "")

    def test_order_id_from_another_order_is_rejected(self):
        self.client.post(self.url, {
            "razorpay_order_id": "order_OTHER", "razorpay_payment_id": "pay_1",
            "razorpay_signature": sign("order_OTHER", "pay_1"),
        })
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "PENDING")

    def test_replaying_a_verified_payment_does_nothing_new(self):
        data = {"razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1",
                "razorpay_signature": sign("order_1", "pay_1")}
        self.client.post(self.url, data)
        first_ids = set(self.batch.worker_records.values_list("transfer_id", flat=True))
        self.client.post(self.url, data)
        second_ids = set(self.batch.worker_records.values_list("transfer_id", flat=True))
        self.assertEqual(first_ids, second_ids)