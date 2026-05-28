# Generated manually for PromptmaX Razorpay payment orders.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enhancer', '0003_userplan'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan', models.CharField(choices=[('free', 'Free'), ('pro', 'Pro'), ('pro_plus', 'Pro+')], max_length=20)),
                ('amount_rs', models.PositiveIntegerField()),
                ('amount_paise', models.PositiveIntegerField()),
                ('currency', models.CharField(default='INR', max_length=8)),
                ('razorpay_order_id', models.CharField(max_length=120, unique=True)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=120)),
                ('razorpay_signature', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('created', 'Created'), ('paid', 'Paid'), ('failed', 'Failed')], default='created', max_length=16)),
                ('raw_response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promptmax_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
