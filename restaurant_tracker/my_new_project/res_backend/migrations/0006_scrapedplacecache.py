# Generated manually for JIT Real-Time Location System

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('res_backend', '0005_precreateditinerary'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapedPlaceCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('geohash', models.CharField(db_index=True, help_text='Geohash cell ID (precision 7 = ~153m)', max_length=12)),
                ('query_context', models.CharField(db_index=True, help_text="Time context (e.g., 'lunch', 'morning')", max_length=100)),
                ('places_data', models.JSONField(help_text='Cached scraped places')),
                ('scraped_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Used for TTL check (24 hours)')),
                ('hit_count', models.IntegerField(default=0, help_text='Number of cache hits')),
            ],
            options={
                'ordering': ['-scraped_at'],
            },
        ),
        migrations.AddIndex(
            model_name='scrapedplacecache',
            index=models.Index(fields=['geohash', 'query_context', 'scraped_at'], name='cache_lookup_idx'),
        ),
        migrations.AddIndex(
            model_name='scrapedplacecache',
            index=models.Index(fields=['scraped_at'], name='cache_cleanup_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='scrapedplacecache',
            unique_together={('geohash', 'query_context')},
        ),
    ]

