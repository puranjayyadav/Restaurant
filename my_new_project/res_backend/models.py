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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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

class UserInteraction(models.Model):
    """Tracks user interactions with establishments for recommendation system.
    
    This model stores different types of interactions users have with restaurants,
    such as viewing details, saving to favorites, visiting, or rating.
    These interactions are used to build user profiles for personalized recommendations.
    """
    INTERACTION_TYPES = [
        ('VIEW', 'Viewed'),
        ('SAVE', 'Saved to favorites'),
        ('VISIT', 'Visited'),
        ('RATE', 'Rated'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions')
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='user_interactions')
    interaction_type = models.CharField(max_length=10, choices=INTERACTION_TYPES)
    rating = models.IntegerField(null=True, blank=True)  # For 'RATE' interactions (1-5)
    
    # Instead of a direct foreign key, store trip ID as a string
    trip_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID of the associated trip")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Order by most recent first
        ordering = ['-timestamp']
        # Prevent duplicate entries of same type in short period
        # index_together = [['user', 'establishment', 'interaction_type']]
    
    def __str__(self):
        return f"{self.user.username} {self.get_interaction_type_display()} {self.establishment.name}"
    
    def save(self, *args, **kwargs):
        # Validate rating if provided
        if self.interaction_type == 'RATE' and self.rating is not None:
            if not (1 <= self.rating <= 5):
                raise ValueError("Rating must be between 1 and 5")
        
        super().save(*args, **kwargs)

class PublicItinerary(models.Model):
    """Model for public itineraries stored in Firestore.
    
    This model represents the structure of public itineraries in Firestore.
    The actual data is stored in Firestore, but this model helps with
    type checking and documentation.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Firestore document ID (stored as string)
    firestore_id = models.CharField(max_length=200, unique=True, null=True, blank=True)
    
    # User information
    user_id = models.CharField(max_length=200)
    user_name = models.CharField(max_length=200)
    user_photo_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Itinerary details
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    neighborhood = models.CharField(max_length=200)
    categories = models.JSONField(default=list)  # Array of category strings
    
    # Status and moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=200, null=True, blank=True)
    
    # Engagement metrics
    likes_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    added_to_schedule_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.user_name} ({self.status})"

class ItineraryLike(models.Model):
    """Tracks likes on public itineraries.
    
    This model represents likes stored in Firestore subcollection.
    """
    # Firestore document IDs
    itinerary_firestore_id = models.CharField(max_length=200)
    user_id = models.CharField(max_length=200)
    liked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('itinerary_firestore_id', 'user_id')
        ordering = ['-liked_at']
    
    def __str__(self):
        return f"Like by {self.user_id} on {self.itinerary_firestore_id}"

class UserStats(models.Model):
    """User statistics for public itineraries.
    
    Tracks user's public itinerary count and total likes received.
    """
    user_id = models.CharField(max_length=200, unique=True)
    total_public_itineraries = models.IntegerField(default=0)
    total_likes_received = models.IntegerField(default=0)
    profile_photo_url = models.URLField(max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_likes_received']
    
    def __str__(self):
        return f"Stats for {self.user_id}: {self.total_public_itineraries} itineraries, {self.total_likes_received} likes"