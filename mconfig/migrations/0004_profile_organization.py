# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-13 07:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mconfig', '0003_auto_20161213_0850'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='organization',
            field=models.CharField(default='', max_length=60),
            preserve_default=False,
        ),
    ]
