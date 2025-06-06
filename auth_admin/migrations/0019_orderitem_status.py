# Generated by Django 5.1.1 on 2025-03-26 05:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_admin', '0018_remove_order_razorpay_payment_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('canceled', 'Canceled')], default='pending', max_length=20),
        ),
    ]
