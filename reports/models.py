from django.conf import settings
from django.db import models


class StoreSettings(models.Model):
    """Singleton row holding the seller's own GST profile — business name,
    address and GSTIN — printed on every generated invoice and the
    GSTR-3B summary. Editable from the admin console's GST settings panel
    instead of only via server env vars (`INVOICE_SELLER_*`), which stay
    as the fallback for any field left blank here so nothing breaks before
    an admin has filled this in."""

    business_name = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=500, blank=True, default="")
    gstin = models.CharField(max_length=20, blank=True, default="")
    # Invoice numbers look like `<prefix>/<FY>/<0001>`, e.g. LTC/26-27/0001,
    # restarting at 0001 every financial year (April–March).
    invoice_prefix = models.CharField(max_length=10, blank=True, default="LTC")

    # Delivery charges — edited from the admin console's "Delivery charges"
    # page and applied by both the cart (`CartSerializer`) and order
    # placement (`PlaceOrderSerializer`) via `delivery_fee_for`, so the fee
    # the customer sees is the fee they're charged.
    delivery_fee = models.PositiveIntegerField(default=19, help_text="Flat fee (₹) per order.")
    free_delivery_enabled = models.BooleanField(default=True)
    free_delivery_above = models.PositiveIntegerField(
        default=199, help_text="Item total (₹) at or above which delivery is free."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Store settings"

    def __str__(self):
        return self.resolved_business_name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def delivery_fee_for(self, item_total: int) -> int:
        """Fee for a basket whose items add up to [item_total] (before any
        coupon) — free once it reaches the threshold, and never charged on
        an empty basket."""
        if item_total <= 0:
            return 0
        if self.free_delivery_enabled and item_total >= self.free_delivery_above:
            return 0
        return self.delivery_fee

    @property
    def resolved_business_name(self):
        return self.business_name or settings.INVOICE_SELLER_NAME

    @property
    def resolved_address(self):
        return self.address or settings.INVOICE_SELLER_ADDRESS

    @property
    def resolved_gstin(self):
        return self.gstin or settings.INVOICE_SELLER_GSTIN


class InvoiceSequence(models.Model):
    """Last invoice number issued per financial year (e.g. "26-27") —
    incremented under a row lock so concurrent orders never share or skip
    a number. See `next_invoice_number`."""

    financial_year = models.CharField(max_length=5, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.financial_year}: {self.last_number}"


def financial_year_label(day) -> str:
    """Indian FY (April–March) for a date: 31 Oct 2026 -> "26-27"."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start % 100:02d}-{(start + 1) % 100:02d}"


def next_invoice_number(day) -> str:
    """Issues the next number in the series, e.g. LTC/26-27/0001. Must be
    called inside a transaction (order placement is)."""
    fy = financial_year_label(day)
    seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(financial_year=fy)
    seq.last_number += 1
    seq.save(update_fields=["last_number"])
    prefix = (StoreSettings.load().invoice_prefix or "LTC").strip().strip("/")
    return f"{prefix}/{fy}/{seq.last_number:04d}"
