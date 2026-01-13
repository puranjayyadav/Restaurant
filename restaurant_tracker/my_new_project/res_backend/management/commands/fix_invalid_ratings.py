from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix invalid rating values in ScrapedRestaurant model'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # First, find all restaurants with ratings
            cursor.execute("SELECT id, name, rating FROM res_backend_scrapedrestaurant WHERE rating IS NOT NULL")
            rows = cursor.fetchall()
            
            self.stdout.write(f'Checking {len(rows)} restaurants with ratings...')
            fixed = 0
            
            for row_id, name, rating in rows:
                try:
                    # Try to convert to float first to validate
                    rating_float = float(rating)
                    
                    # Check if it's in valid range
                    if rating_float < 0 or rating_float > 5:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Invalid rating {rating} for {name} (ID: {row_id}) - setting to NULL'
                            )
                        )
                        cursor.execute(
                            "UPDATE res_backend_scrapedrestaurant SET rating = NULL WHERE id = %s",
                            [row_id]
                        )
                        fixed += 1
                    else:
                        # Try to convert to proper decimal format
                        from decimal import Decimal
                        try:
                            Decimal(str(rating))
                        except:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  Cannot convert rating {rating} for {name} (ID: {row_id}) - setting to NULL'
                                )
                            )
                            cursor.execute(
                                "UPDATE res_backend_scrapedrestaurant SET rating = NULL WHERE id = %s",
                                [row_id]
                            )
                            fixed += 1
                except (ValueError, TypeError) as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  Error with rating "{rating}" for {name} (ID: {row_id}): {e} - setting to NULL'
                        )
                    )
                    cursor.execute(
                        "UPDATE res_backend_scrapedrestaurant SET rating = NULL WHERE id = %s",
                        [row_id]
                    )
                    fixed += 1
            
            connection.commit()
        
        self.stdout.write(
            self.style.SUCCESS(f'Fixed {fixed} restaurants with invalid ratings')
        )
