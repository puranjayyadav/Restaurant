from django.core.management.base import BaseCommand
from res_backend.models import ScrapedRestaurant
import json
import os


class Command(BaseCommand):
    help = 'Import scraped restaurant data from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file with restaurant data')
        parser.add_argument('--source', type=str, required=True, 
                          choices=['yelp', 'google', 'tripadvisor', 'foursquare', 'opentable', 'other'],
                          help='Source name (yelp, google, etc.)')
        parser.add_argument('--dry-run', action='store_true', 
                          help='Show what would be imported without actually importing')

    def handle(self, *args, **options):
        json_file = options['json_file']
        source = options['source']
        dry_run = options['dry_run']
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
            return
        
        self.stdout.write(f'Reading restaurant data from {json_file}...')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                restaurants = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON file: {e}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
            return
        
        if not isinstance(restaurants, list):
            self.stdout.write(self.style.ERROR('JSON file must contain an array of restaurant objects'))
            return
        
        self.stdout.write(f'Found {len(restaurants)} restaurants to import')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
        
        created = 0
        updated = 0
        errors = 0
        
        for idx, data in enumerate(restaurants, 1):
            try:
                # Extract source_id from various possible fields
                source_id = (
                    data.get('source_id') or 
                    data.get('place_id') or 
                    data.get('id') or 
                    data.get('yelp_id') or
                    data.get('restaurant_id') or
                    f"{source}_{idx}"
                )
                source_id = str(source_id)  # Ensure it's a string
                
                # Extract name
                name = data.get('name') or data.get('place_name') or 'Unknown Restaurant'
                
                # Extract address components - parse from full address if needed
                address = data.get('address') or data.get('full_address') or data.get('formatted_address') or ''
                
                # Try to parse city, state, zip from address if not provided
                street_address = data.get('street_address') or data.get('street')
                city = data.get('city') or ''
                state = data.get('state') or ''
                zip_code = data.get('zip_code') or data.get('zip') or data.get('postal_code') or ''
                country = data.get('country') or data.get('country_code') or 'USA'
                
                # Parse address if it contains city/state info (e.g., "5 Beekman Street, New York, NY 10038")
                if address and not city:
                    import re
                    # Try to extract city, state, zip from address
                    # Pattern: "..., City, ST ZIP" or "..., City, ST"
                    match = re.search(r',\s*([^,]+?),\s*([A-Z]{2})(?:\s+(\d{5}))?$', address)
                    if match:
                        city = match.group(1).strip()
                        state = match.group(2).strip()
                        if match.group(3):
                            zip_code = match.group(3).strip()
                        # Extract street address (everything before the last comma)
                        street_address = address.rsplit(',', 2)[0].strip() if ',' in address else address
                
                # Extract coordinates - handle string to float conversion
                latitude = data.get('latitude') or data.get('lat')
                if latitude is not None:
                    try:
                        latitude = float(str(latitude))
                    except (ValueError, TypeError):
                        latitude = None
                
                longitude = data.get('longitude') or data.get('long') or data.get('lng')
                if longitude is not None:
                    try:
                        longitude = float(str(longitude))
                    except (ValueError, TypeError):
                        longitude = None
                
                # Extract rating - handle both string and numeric
                rating = data.get('rating') or data.get('avg_rating') or data.get('average_rating')
                if rating is not None:
                    try:
                        rating = float(str(rating))
                    except (ValueError, TypeError):
                        rating = None
                
                total_reviews = data.get('total_reviews') or data.get('review_count') or 0
                if total_reviews is not None:
                    try:
                        total_reviews = int(str(total_reviews))
                    except (ValueError, TypeError):
                        total_reviews = 0
                
                # Extract price range
                price_range = (
                    data.get('price_range') or 
                    data.get('price_level') or 
                    data.get('price')
                )
                
                # Extract contact info
                phone = data.get('phone') or data.get('phone_number')
                website = data.get('website') or data.get('url')
                email = data.get('email')
                
                # Extract JSON fields
                hours = data.get('hours', {}) or data.get('working_hours', {})
                
                # Handle categories - could be string, list, or cuisine field
                categories = data.get('categories') or data.get('tags') or data.get('types', [])
                if not categories:
                    # Try cuisine field (OpenTable format)
                    cuisine = data.get('cuisine')
                    if cuisine:
                        categories = [cuisine] if isinstance(cuisine, str) else cuisine
                
                features = data.get('features', [])
                
                # Handle photos - could be 'images' or 'photos'
                photos = data.get('photos', []) or data.get('photo_urls', []) or data.get('images', [])
                
                menu_items = data.get('menu_items', []) or data.get('menu', [])
                social_media = data.get('social_media', {})
                
                # Ensure categories is a list
                if isinstance(categories, str):
                    categories = [categories]
                
                # Prepare defaults for update_or_create
                defaults = {
                    'name': name,
                    'description': data.get('description'),
                    'source_url': data.get('source_url') or data.get('url'),
                    'address': address,
                    'street_address': street_address,
                    'city': city,
                    'state': state,
                    'zip_code': zip_code,
                    'country': country,
                    'latitude': latitude,
                    'longitude': longitude,
                    'phone': phone,
                    'website': website,
                    'email': email,
                    'rating': rating,
                    'total_reviews': total_reviews,
                    'price_range': price_range,
                    'hours': hours if isinstance(hours, dict) else {},
                    'categories': categories if isinstance(categories, list) else [],
                    'features': features if isinstance(features, list) else [],
                    'photos': photos if isinstance(photos, list) else [],
                    'menu_items': menu_items if isinstance(menu_items, list) else [],
                    'social_media': social_media if isinstance(social_media, dict) else {},
                    'raw_data': data,  # Store original data
                }
                
                if dry_run:
                    self.stdout.write(f'  [{idx}] Would import: {name} ({source_id})')
                else:
                    restaurant, created_flag = ScrapedRestaurant.objects.update_or_create(
                        source=source,
                        source_id=str(source_id),
                        defaults=defaults
                    )
                    
                    if created_flag:
                        created += 1
                        self.stdout.write(f'  [{idx}] Created: {name}')
                    else:
                        updated += 1
                        self.stdout.write(f'  [{idx}] Updated: {name}')
                        
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  [{idx}] Error processing restaurant: {e}')
                )
                continue
        
        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'DRY RUN: Would import {len(restaurants)} restaurants'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Successfully imported {created} new restaurants, updated {updated} existing'
            ))
            if errors > 0:
                self.stdout.write(self.style.WARNING(f'Encountered {errors} errors'))

