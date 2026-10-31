from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='storesettings',
            name='delivery_fee',
            field=models.PositiveIntegerField(default=19, help_text='Flat fee (₹) per order.'),
        ),
        migrations.AddField(
            model_name='storesettings',
            name='free_delivery_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='storesettings',
            name='free_delivery_above',
            field=models.PositiveIntegerField(default=199, help_text='Item total (₹) at or above which delivery is free.'),
        ),
    ]
