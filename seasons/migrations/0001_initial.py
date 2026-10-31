# Additive: one new table. Safe on a live database.
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('kind', models.CharField(choices=[('week', 'Week'), ('term', 'Term')], max_length=10)),
                ('starts_at', models.DateTimeField(help_text='Stored in UTC. Pick the Lagos time you want.')),
                ('ends_at', models.DateTimeField(help_text='Exclusive end. Stored in UTC.')),
                ('state', models.CharField(choices=[('scheduled', 'Scheduled'), ('open', 'Open'), ('closed', 'Closed')], default='scheduled', max_length=10)),
                ('opened_at', models.DateTimeField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-starts_at', '-id'],
                'indexes': [models.Index(fields=['kind', 'state'], name='season_kind_state_idx')],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('ends_at__gt', models.F('starts_at'))), name='season_ends_after_start'),
                    models.UniqueConstraint(condition=models.Q(('state', 'open')), fields=('kind',), name='uniq_open_season_per_kind'),
                ],
            },
        ),
    ]
