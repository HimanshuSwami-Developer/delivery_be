from django.conf import settings
from django.db import models

from core.helper.base import BaseModel


class SupportTicket(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="support_tickets"
    )
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    admin_reply = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} ({self.user.mobile_number})"


class SupportConfig(BaseModel):
    """Singleton — the one admin-editable row of customer-support contact
    info the app's "Help & support" screen fetches (call + WhatsApp only).
    Always exactly one row (pk=1); `load()` creates it on first access if
    missing, so the app's GET never 404s even before an admin fills it in
    (buttons just render disabled until real values are set)."""

    phone_number = models.CharField(
        max_length=20, blank=True,
        help_text="With country code, e.g. +919718751020 — used for the 'Call support' tel: link.",
    )
    whatsapp_number = models.CharField(
        max_length=20, blank=True,
        help_text="Digits only with country code, e.g. 919718751020 — used to build the wa.me link.",
    )
    whatsapp_message = models.CharField(
        max_length=300, blank=True, default="Hey, I am {name} and I need help.",
        help_text="Pre-filled text the WhatsApp chat opens with. Include the literal "
                  "'{name}' placeholder to have it replaced with the signed-in customer's "
                  "own name (see SupportConfigSerializer.get_whatsapp_link).",
    )
    reply_time_label = models.CharField(max_length=60, blank=True, default="Typical reply in under 2 min")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Support contact config"


class SupportFAQ(BaseModel):
    """Admin-editable Q&A shown on the customer app's "Help & support"
    screen — public read, admin write, ordered by `order` then insertion."""

    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Support FAQ"
        verbose_name_plural = "Support FAQs"

    def __str__(self):
        return self.question
