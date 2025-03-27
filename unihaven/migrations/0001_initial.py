# Generated by Django 5.1.7 on 2025-03-27 15:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CEDARSSpecialist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='HKUMember',
            fields=[
                ('uid', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='PropertyOwner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('contact_info', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Accommodation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('apartment', 'Apartment'), ('house', 'House'), ('villa', 'Villa'), ('studio', 'Studio'), ('hostel', 'Hostel')], max_length=50)),
                ('address', models.CharField(max_length=255)),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('geo_address', models.CharField(max_length=255)),
                ('available_from', models.DateField()),
                ('available_until', models.DateField()),
                ('beds', models.IntegerField()),
                ('bedrooms', models.IntegerField()),
                ('rating', models.FloatField()),
                ('daily_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accommodations', to='unihaven.propertyowner')),
            ],
        ),
    ]
