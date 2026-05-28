# Generated manually for PromptmaX account plans.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enhancer', '0002_promptproject_promptasset_promptversion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan', models.CharField(choices=[('free', 'Free'), ('pro', 'Pro'), ('pro_plus', 'Pro+')], max_length=20)),
                ('price_rs', models.PositiveIntegerField(default=0)),
                ('selected_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='promptmax_plan', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-selected_at'],
            },
        ),
    ]
