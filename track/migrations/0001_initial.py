# Generated by Django 3.0.2 on 2020-02-25 11:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UrlHit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('hits', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['-hits'],
            },
        ),
        migrations.CreateModel(
            name='HitCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.CharField(max_length=40)),
                ('session', models.CharField(max_length=40)),
                ('date', models.DateTimeField(auto_now=True)),
                ('url_hit', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='track.UrlHit')),
            ],
            options={
                'ordering': ['url_hit'],
            },
        ),
    ]
