from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_remove_order_zone'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='rider_latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='rider_longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='rider_heading',
            field=models.FloatField(blank=True, help_text='Degrees clockwise from north.', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='rider_location_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
