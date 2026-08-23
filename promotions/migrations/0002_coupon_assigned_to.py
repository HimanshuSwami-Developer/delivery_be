from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_devicetoken'),
        ('promotions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True,
                help_text='Set for personal one-time coupons (e.g. referral rewards) — only this user may apply it, and only once.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='personal_coupons',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
