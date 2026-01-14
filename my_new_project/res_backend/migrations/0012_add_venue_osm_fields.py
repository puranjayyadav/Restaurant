# Generated manually for OSM integration

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('res_backend', '0006_scrapedplacecache'),
    ]

    operations = [
        # Add OSM fields to ScrapedRestaurant model
        migrations.AddField(
            model_name='scrapedrestaurant',
            name='osm_type',
            field=models.CharField(max_length=10, null=True, blank=True, help_text='OSM type: node, way, relation'),
        ),
        migrations.AddField(
            model_name='scrapedrestaurant',
            name='osm_id',
            field=models.BigIntegerField(null=True, blank=True, help_text='OSM ID'),
        ),
        migrations.AddField(
            model_name='scrapedrestaurant',
            name='raw_osm_data',
            field=models.JSONField(default=dict, blank=True, help_text='Raw OSM data'),
        ),
        
        # Add unique constraint for OSM data (only when both fields are not null)
        migrations.AddConstraint(
            model_name='scrapedrestaurant',
            constraint=models.UniqueConstraint(
                fields=['osm_type', 'osm_id'],
                name='venues_osm_unique',
                condition=Q(osm_type__isnull=False, osm_id__isnull=False)
            ),
        ),
        
        # Create a regular index for faster lookups
        migrations.AddIndex(
            model_name='scrapedrestaurant',
            index=models.Index(fields=['osm_type', 'osm_id'], name='venues_osm_lookup_idx'),
        ),
        
        # Add full-text search capabilities
        migrations.RunSQL(
            sql="""
            -- Create GIN indexes for full-text search
            CREATE INDEX IF NOT EXISTS venues_name_fts_idx ON res_backend_scrapedrestaurant USING gin(to_tsvector('english', name));
            CREATE INDEX IF NOT EXISTS venues_address_fts_idx ON res_backend_scrapedrestaurant USING gin(to_tsvector('english', address));
            CREATE INDEX IF NOT EXISTS venues_city_fts_idx ON res_backend_scrapedrestaurant USING gin(to_tsvector('english', city));
            CREATE INDEX IF NOT EXISTS venues_state_fts_idx ON res_backend_scrapedrestaurant USING gin(to_tsvector('english', state));
            CREATE INDEX IF NOT EXISTS venues_zip_fts_idx ON res_backend_scrapedrestaurant USING gin(to_tsvector('english', zip_code));
            
            -- Create trigram indexes for fuzzy search
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            CREATE INDEX IF NOT EXISTS venues_name_trgm_idx ON res_backend_scrapedrestaurant USING gin(name gin_trgm_ops);
            CREATE INDEX IF NOT EXISTS venues_address_trgm_idx ON res_backend_scrapedrestaurant USING gin(address gin_trgm_ops);
            """
        ),
    ]