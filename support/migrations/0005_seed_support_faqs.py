from django.db import migrations

# Mirrors the 5 topics the customer app's "Help & support" screen used to
# show as static, non-functional placeholder text (no answers, no tap
# action) — now real Q&A an admin can edit going forward.
_SEED = [
    dict(
        order=0,
        question="An item is missing from my order",
        answer="Sorry about that! Open the order from My Orders, tap \"Report an issue\" and let us know "
               "which item was missing — our team will review it and arrange a refund or replacement for "
               "that item.",
    ),
    dict(
        order=1,
        question="How do returns and refunds work?",
        answer="Once an order is marked Delivered, open it from My Orders and choose the return option for "
               "the item(s) you want to send back. A refund is processed to your original payment method "
               "after the return is picked up and checked.",
    ),
    dict(
        order=2,
        question="Change my delivery slot",
        answer="You can pick your delivery day and time slot while placing the order, on the slot-selection "
               "step. If your order is already placed and hasn't left the store yet, contact us via Call or "
               "WhatsApp and we'll try to reschedule it for you.",
    ),
    dict(
        order=3,
        question="Where is my order receipt?",
        answer="Open the order from My Orders and tap \"Download invoice\" (or \"Download receipt\") to get "
               "a PDF with the full item, tax, and payment breakdown — available as soon as the order is "
               "placed.",
    ),
    dict(
        order=4,
        question="Delete my account",
        answer="We handle account deletion requests by hand to make sure your data is removed safely. "
               "Message us on Call or WhatsApp with your registered mobile number and we'll take care of it.",
    ),
]


def seed_support_faqs(apps, schema_editor):
    SupportFAQ = apps.get_model("support", "SupportFAQ")
    for row in _SEED:
        SupportFAQ.objects.get_or_create(question=row["question"], defaults=row)


def remove_support_faqs(apps, schema_editor):
    SupportFAQ = apps.get_model("support", "SupportFAQ")
    SupportFAQ.objects.filter(question__in=[row["question"] for row in _SEED]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0004_supportfaq_alter_supportconfig_whatsapp_message'),
    ]

    operations = [
        migrations.RunPython(seed_support_faqs, remove_support_faqs),
    ]
