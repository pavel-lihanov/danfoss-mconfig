# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-13 08:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mconfig', '0005_auto_20161213_1051'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'permissions': (('view_details', 'Can see price details'), ('view_price', 'Can view prices'), ('view_delivery', 'Can view delivery time'))},
        ),
        migrations.AlterModelOptions(
            name='profile',
            options={'permissions': (('register_users', 'Can add sales users'), ('test', 'Test permission'))},
        ),
    ]
