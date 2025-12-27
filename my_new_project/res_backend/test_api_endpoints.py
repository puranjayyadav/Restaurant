from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from res_backend.models import PreCreatedItinerary, ScrapedRestaurant
import json
import uuid

class APIPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create a large dummy payload to simulate heavy restaurant data
        # 50KB of text per restaurant
        heavy_text = "x" * 50000

        # Create a mock itinerary data structure with 10 restaurants
        self.heavy_itinerary_data = {
            "itinerary": []
        }

        for i in range(10):
            restaurant = {
                "place_name": f"Restaurant {i}",
                "postgres_data": {
                    "reviews": [heavy_text], # Massive review
                    "photos": [heavy_text],  # Massive photo string (base64 sim)
                    "menu_items": [{"name": "Item", "desc": heavy_text}]
                }
            }
            self.heavy_itinerary_data["itinerary"].append(restaurant)

        # Create 5 featured itineraries
        for i in range(5):
            PreCreatedItinerary.objects.create(
                title=f"Heavy Itinerary {i}",
                description="Testing payload size",
                latitude=40.7,
                longitude=-74.0,
                radius_km=1.0,
                is_featured=True,
                itinerary_data=self.heavy_itinerary_data,
                total_restaurants=10,
                enriched_count=10,
                enrichment_percentage=100.0
            )

    def test_get_featured_itineraries_payload_size(self):
        """
        Test that fetches the list of featured itineraries and measures response size.
        This demonstrates the 'huge egress' issue.
        """
        print("\n--- PERFORMANCE TEST: get_featured_itineraries ---")
        response = self.client.get('/api/discovery/featured-itineraries/?limit=5')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Calculate size in MB
        size_bytes = len(response.content)
        size_mb = size_bytes / (1024 * 1024)

        print(f"Response Status: {response.status_code}")
        print(f"Response Size: {size_bytes} bytes ({size_mb:.2f} MB)")

        # Check if we actually got the data back
        data = response.json()
        self.assertEqual(len(data['featured_itineraries']), 5)

        # Verify that the heavy data is indeed inside the list response
        first_item = data['featured_itineraries'][0]
        self.assertIn('itinerary_data', first_item)
        self.assertIn('itinerary', first_item['itinerary_data'])
        self.assertTrue(len(first_item['itinerary_data']['itinerary']) > 0)

        # Assert that the size is "large" (e.g., > 1MB) to prove the point
        # 5 itineraries * 10 restaurants * 50KB * 3 fields ~= 7.5MB
        # We expect around that size.
        if size_mb > 1.0:
            print("⚠️  WARNING: Response size is very large (> 1MB). This confirms the egress issue.")
        else:
            print("✅ Response size is manageable.")

    def test_get_pre_created_itinerary_detail(self):
        """
        Test fetching a single itinerary detail.
        This is where the heavy data SHOULD be.
        """
        print("\n--- FUNCTIONAL TEST: get_pre_created_itinerary_detail ---")
        itinerary = PreCreatedItinerary.objects.first()
        response = self.client.get(f'/api/discovery/pre-created-itineraries/{itinerary.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['id'], itinerary.id)
        self.assertIn('itinerary_data', data)
        print("✅ Detail endpoint works correctly.")
