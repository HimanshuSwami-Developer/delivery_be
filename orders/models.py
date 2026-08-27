import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.helper.base import BaseModel


def generate_order_number():
    return "BSK-" + "".join(random.choices(string.digits, k=4))


class Order(BaseModel):
    # Grace window from "out for delivery" to "delivered" used by
    # DeliveryPartner.on_time_pct and the admin dashboard's on-time KPI.
    ON_TIME_MINUTES = 20

    class Status(models.TextChoices):
        NEW = "new", "New"
        PACKED = "packed", "Packed"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMode(models.TextChoices):
        COD = "cod", "COD"
        QR = "qr", "QR"
        # Legacy modes from the old Razorpay gateway checkout — kept only so
        # historical orders placed under them still display correctly.
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        WALLET = "wallet", "Wallet"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    zone = models.ForeignKey("zones.Zone", on_delete=models.PROTECT, related_name="orders")
    delivery_partner = models.ForeignKey(
        "delivery.DeliveryPartner", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    coupon = models.ForeignKey(
        "promotions.Coupon", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    payment_mode = models.CharField(max_length=10, choices=PaymentMode.choices, default=PaymentMode.QR)

    # Separate from `status` (the delivery lifecycle) since a Cash on
    # Delivery or QR order is legitimately "new" while payment_status stays
    # "pending" for a while — QR payments are UPI-app-to-UPI-app with no
    # gateway callback. `PlaceOrderSerializer._verify_qr_payment` reads the
    # uploaded screenshot via Groq and auto-flips this to PAID when it finds
    # both a transaction ID and a matching amount; anything less certain
    # (Groq not configured, an unreadable screenshot, an amount mismatch)
    # leaves it here for an admin to verify by hand from the order admin.
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING,
    )
    payment_screenshot_url = models.URLField(max_length=500, blank=True, default="")
    # UPI transaction ID / UTR read off the screenshot by Groq (or entered
    # by an admin) — empty until then.
    payment_transaction_id = models.CharField(max_length=64, blank=True, default="")

    # Address snapshot — addresses live as JSON on accounts.Profile (not a
    # table), and an order must keep the address it was placed against even
    # if the customer edits/deletes that saved address later.
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    # Drop-pin coordinates, snapshotted the same way as the address text
    # above (from the saved address, if it has one) — the delivery
    # partner's map view (see `orders.serializers.OrderListSerializer`)
    # falls back to the address text alone when these are null, which is
    # always true for orders placed before this field existed.
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    gstin = models.CharField(max_length=20, blank=True, help_text="Buyer GSTIN for a B2B invoice; blank = B2C.")

    delivery_slot_date = models.DateField(null=True, blank=True)
    delivery_slot_label = models.CharField(max_length=50, blank=True)

    subtotal = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)
    cgst = models.PositiveIntegerField(default=0)
    sgst = models.PositiveIntegerField(default=0)
    delivery_fee = models.PositiveIntegerField(default=19)
    total = models.PositiveIntegerField(default=0)

    packed_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    @property
    def item_count(self):
        return sum(i.qty for i in self.items.all())

    def recalculate_totals(self, save=True):
        """Sums each line's own GST slab (snapshotted onto `OrderItem.gst_slab`
        at order-placement time) rather than one flat rate — this is what
        lets the admin GST report break tax down by slab. The coupon
        discount reduces the payable total but isn't apportioned back across
        lines for tax purposes (a deliberate simplification)."""
        items = list(self.items.all())
        subtotal = sum(i.amount for i in items)
        cgst = sum(i.cgst for i in items)
        sgst = sum(i.sgst for i in items)
        discount = self.coupon.discount_for(subtotal) if self.coupon_id else self.discount

        self.subtotal = subtotal
        self.discount = discount
        self.cgst = cgst
        self.sgst = sgst
        self.total = max(subtotal - discount, 0) + cgst + sgst + self.delivery_fee
        if save:
            self.save(update_fields=["subtotal", "discount", "cgst", "sgst", "total", "updated_at"])

    _STATUS_TIMESTAMP_FIELD = {
        Status.PACKED: "packed_at",
        Status.OUT_FOR_DELIVERY: "out_for_delivery_at",
        Status.DELIVERED: "delivered_at",
        Status.CANCELLED: "cancelled_at",
    }

    # Only the two terminal/outcome statuses push — "successful" (delivered)
    # or "failed" (cancelled). The in-between statuses (packed, out for
    # delivery) are tracking updates, not an outcome, so they stay silent.
    _STATUS_PUSH_COPY = {
        Status.DELIVERED: ("Order delivered", "Your order {order_number} has been delivered. Enjoy!"),
        Status.CANCELLED: ("Order cancelled", "Your order {order_number} has been cancelled."),
    }

    def set_status(self, new_status, save=True):
        self.status = new_status
        field = self._STATUS_TIMESTAMP_FIELD.get(new_status)
        update_fields = ["status", "updated_at"]
        if field and not getattr(self, field):
            setattr(self, field, timezone.now())
            update_fields.append(field)
        if save:
            self.save(update_fields=update_fields)
        self._send_push(*self._STATUS_PUSH_COPY.get(new_status, (None, None)))

    def send_placed_push(self):
        """Called once, right after `OrderViewSet.place` creates the order —
        the "order successful" (placed) notification, distinct from the
        later "delivered" one `set_status` sends."""
        self._send_push("Order placed", "Your order {order_number} has been placed successfully.")

    def send_order_invoice_sms(self):
        """Called once, right after `OrderViewSet.place` creates the order —
        notifies the business's own mobile (settings.ORDER_NOTIFY_MOBILE_NUMBER)
        with the full invoice, so every order (QR or COD) gets flagged there
        immediately regardless of payment_status. Best-effort: `SMSService`
        never raises, so a misconfigured/unreachable send can't fail order
        placement itself."""
        from core.service.sms_service import SMSService

        SMSService.send_order_invoice_sms(self._invoice_text())

    def _invoice_text(self):
        lines = [
            f"New order {self.order_number}",
            f"{self.customer.name or 'Customer'} · {self.customer.mobile_number}",
            "",
        ]
        for item in self.items.all():
            lines.append(f"{item.product_name} x{item.qty} = Rs {item.amount}")
        lines.append("")
        if self.discount:
            lines.append(f"Subtotal: Rs {self.subtotal}  Discount: -Rs {self.discount}")
        else:
            lines.append(f"Subtotal: Rs {self.subtotal}")
        lines.append(f"GST: Rs {self.cgst + self.sgst}  Delivery: Rs {self.delivery_fee}")
        lines.append(f"Total: Rs {self.total}")
        lines.append("")
        payment_line = f"Payment: {self.get_payment_mode_display()} ({self.get_payment_status_display()})"
        if self.payment_transaction_id:
            payment_line += f" · Txn {self.payment_transaction_id}"
        lines.append(payment_line)
        lines.append(f"Deliver to: {self.address_line1}, {self.address_line2}, {self.city}, {self.state} {self.pincode}".replace(", ,", ","))
        return "\n".join(lines)

    def _send_push(self, title, body_template):
        if not title:
            return
        from accounts.models import DeviceToken
        from core.service.push_service import PushService

        tokens = DeviceToken.objects.filter(user=self.customer).values_list("token", flat=True)
        _, invalid_tokens = PushService.send_to_tokens(
            tokens,
            title,
            body_template.format(order_number=self.order_number),
            data={"type": "order_status", "order_id": str(self.id), "status": self.status},
        )
        if invalid_tokens:
            DeviceToken.objects.filter(token__in=invalid_tokens).delete()


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")

    # Snapshots so a historical order's receipt never changes if the
    # product is later renamed, re-priced, or moved to a different slab.
    product_name = models.CharField(max_length=255)
    pack = models.CharField(max_length=50, blank=True)
    rate = models.PositiveIntegerField()
    gst_slab = models.CharField(max_length=2, default="5")
    qty = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product_name} x{self.qty}"

    @property
    def amount(self):
        return self.rate * self.qty

    @property
    def gst_amount(self):
        return round(self.amount * float(self.gst_slab) / 100)

    @property
    def cgst(self):
        return self.gst_amount // 2

    @property
    def sgst(self):
        return self.gst_amount - self.cgst
