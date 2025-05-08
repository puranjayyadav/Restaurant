from django.db import models
from django.contrib.auth.models import User

class Establishment(models.Model):
    PRICE_RANGES = [
        ('$', '$'),
        ('$$', '$$'),
        ('$$$', '$$$'),
        ('$$$$', '$$$$'),
    ]

    DINING_STYLES = [
        ('FAST_FOOD', 'Fast Food'),
        ('CAFE', 'Café'),
        ('CASUAL', 'Casual Dining'),
        ('FINE', 'Fine Dining'),
        ('BUFFET', 'Buffet'),
        ('FOOD_TRUCK', 'Food Truck'),
    ]

    name = models.CharField(max_length=200)
    address = models.TextField()
    price_range = models.CharField(max_length=4, choices=PRICE_RANGES)
    dining_style = models.CharField(max_length=20, choices=DINING_STYLES)
    location_region = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class EstablishmentFeature(models.Model):
    FEATURE_TYPES = [
        ('VEGAN', 'Vegan-friendly'),
        ('FAMILY', 'Family-friendly'),
        ('OUTDOOR', 'Outdoor Seating'),
        ('PET', 'Pet-friendly'),
        ('DELIVERY', 'Delivery'),
        ('HALAL', 'Halal'),
        ('LATE', 'Open Late'),
        ('TAKEOUT', 'Takeout'),
    ]

    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='features')
    feature_type = models.CharField(max_length=20, choices=FEATURE_TYPES)

    class Meta:
        unique_together = ('establishment', 'feature_type')

    def __str__(self):
        return f"{self.establishment.name} - {self.get_feature_type_display()}"
