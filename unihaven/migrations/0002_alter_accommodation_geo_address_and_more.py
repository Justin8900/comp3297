# Generated by Django 5.1.7 on 2025-03-29 08:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('unihaven', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accommodation',
            name='geo_address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='accommodation',
            name='latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='accommodation',
            name='longitude',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
