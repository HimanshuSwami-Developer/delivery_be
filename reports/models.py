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
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Store settings"

    def __str__(self):
        return self.resolved_business_name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def resolved_business_name(self):
        return self.business_name or settings.INVOICE_SELLER_NAME

    @property
    def resolved_address(self):
        return self.address or settings.INVOICE_SELLER_ADDRESS

    @property
    def resolved_gstin(self):
        return self.gstin or settings.INVOICE_SELLER_GSTIN
