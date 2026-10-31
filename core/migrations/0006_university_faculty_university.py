# Additive: new table and a nullable FK. Safe on a live database.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_department_code_department_is_active_faculty_code_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='University',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('code', models.SlugField(max_length=20, unique=True)),
                ('short_name', models.CharField(blank=True, max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'universities',
                'ordering': ['name', 'id'],
            },
        ),
        migrations.AddField(
            model_name='faculty',
            name='university',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='faculties', to='core.university'),
        ),
    ]
