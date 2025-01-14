# Generated by Django 5.1.3 on 2024-12-30 04:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_pickupgame_all_members'),
    ]

    operations = [
        migrations.AddField(
            model_name='pickupgame',
            name='ballers_score',
            field=models.PositiveSmallIntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='pickupgame',
            name='ringers_score',
            field=models.PositiveSmallIntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='pickupgame',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Pending'), (2, 'Completed'), (3, 'Canceled')], default=1),
        ),
    ]
