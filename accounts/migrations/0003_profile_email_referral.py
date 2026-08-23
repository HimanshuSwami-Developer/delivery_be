import random
import string

from django.db import migrations, models
import django.db.models.deletion


def _generate_code(existing):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=8))
        if code not in existing:
            return code


def backfill_referral_codes(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    existing = set()
    for profile in Profile.objects.all():
        code = _generate_code(existing)
        existing.add(code)
        profile.referral_code = code
        profile.save(update_fields=["referral_code"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_devicetoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="referral_code",
            field=models.CharField(blank=True, editable=False, max_length=12, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="referred_by",
            field=models.ForeignKey(
                blank=True,
                help_text="The profile whose referral code this user signed up with, if any.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referrals",
                to="accounts.profile",
            ),
        ),
        migrations.RunPython(backfill_referral_codes, noop_reverse),
        migrations.AlterField(
            model_name="profile",
            name="referral_code",
            field=models.CharField(editable=False, max_length=12, unique=True),
        ),
    ]
