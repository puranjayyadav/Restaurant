from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

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


class ScrapedRestaurant(models.Model):
    """
    Stores restaurant data scraped from multiple sources (Yelp, Google Maps, etc.)
    Designed for efficient geospatial queries and deduplication.
    """
    
    SOURCE_CHOICES = [
        ('yelp', 'Yelp'),
        ('google', 'Google Maps'),
        ('tripadvisor', 'TripAdvisor'),
        ('foursquare', 'Foursquare'),
        ('opentable', 'OpenTable'),
        ('other', 'Other'),
    ]
    
    # ========== Source Attribution ==========
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, db_index=True)
    source_id = models.CharField(max_length=200, help_text="Original ID from source platform")
    source_url = models.URLField(max_length=500, null=True, blank=True)
    
    # ========== Basic Information ==========
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(null=True, blank=True)
    
    # ========== Location Data ==========
    address = models.TextField()
    street_address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=50, db_index=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=50, default='USA', db_index=True)
    
    # Coordinates for geospatial queries
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # ========== Ratings & Reviews ==========
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.IntegerField(default=0)
    price_range = models.CharField(max_length=10, null=True, blank=True)  # $, $$, $$$, $$$$
    
    # ========== Contact Information ==========
    phone = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(max_length=500, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # ========== Flexible Data (JSON Fields) ==========
    # Operating hours - flexible format: {"monday": "9:00 AM - 10:00 PM", ...}
    hours = models.JSONField(default=dict, blank=True)
    
    # Categories/Tags: ["Italian", "Pizza", "Restaurant"]
    categories = models.JSONField(default=list, blank=True)
    
    # Features: ["outdoor_seating", "wifi", "parking", "wheelchair_accessible"]
    features = models.JSONField(default=list, blank=True)
    
    # Photo URLs: ["https://...", "https://..."]
    photos = models.JSONField(default=list, blank=True)
    
    # Menu items (if available): [{"name": "Pizza", "price": "$15"}, ...]
    menu_items = models.JSONField(default=list, blank=True)
    
    # Social media links
    social_media = models.JSONField(default=dict, blank=True)  # {"instagram": "...", "facebook": "..."}
    
    # Additional metadata from source
    raw_data = models.JSONField(default=dict, blank=True, help_text="Store original scraped data for reference")
    
    # ========== Data Quality & Management ==========
    is_verified = models.BooleanField(default=False, help_text="Manually verified restaurant")
    is_active = models.BooleanField(default=True, help_text="Restaurant is still open")
    data_quality_score = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Data completeness score (0-100)"
    )
    
    # Deduplication - link to canonical restaurant if this is a duplicate
    duplicate_of = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='duplicates',
        help_text="If this is a duplicate, link to the canonical restaurant"
    )
    
    # ========== Timestamps ==========
    scraped_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        # Prevent duplicate entries from same source
        unique_together = ('source', 'source_id')
        
        # Ordering
        ordering = ['-data_quality_score', '-rating', 'name']
        
        # Indexes for performance
        indexes = [
            # Geospatial queries (latitude, longitude)
            models.Index(fields=['latitude', 'longitude'], name='restaurant_location_idx'),
            
            # Location filtering
            models.Index(fields=['city', 'state'], name='restaurant_city_state_idx'),
            
            # Rating queries
            models.Index(fields=['rating'], name='restaurant_rating_idx'),
            
            # Source queries
            models.Index(fields=['source', 'is_active'], name='restaurant_source_active_idx'),
            
            # Quality and verification
            models.Index(fields=['data_quality_score', 'is_verified'], name='restaurant_quality_idx'),
            
            # Name search
            models.Index(fields=['name'], name='restaurant_name_idx'),
        ]
        
        verbose_name = "Scraped Restaurant"
        verbose_name_plural = "Scraped Restaurants"
    
    def __str__(self):
        return f"{self.name} ({self.source}) - {self.city}, {self.state}"
    
    def calculate_quality_score(self):
        """Calculate data quality score based on completeness"""
        score = 0
        max_score = 100
        
        # Basic info (30 points)
        if self.name: score += 10
        if self.address: score += 10
        if self.latitude and self.longitude: score += 10
        
        # Contact info (20 points)
        if self.phone: score += 10
        if self.website: score += 10
        
        # Ratings (20 points)
        if self.rating: score += 10
        if self.total_reviews > 0: score += 10
        
        # Rich data (30 points)
        if self.hours: score += 10
        if self.categories: score += 10
        if self.photos: score += 10
        
        self.data_quality_score = score
        return score
    
    def save(self, *args, **kwargs):
        # Auto-calculate quality score if not set
        if self.data_quality_score == 0:
            self.calculate_quality_score()
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [self.street_address or self.address, self.city, self.state, self.zip_code]
        return ", ".join([p for p in parts if p])


class PreCreatedItinerary(models.Model):
    """
    Stores pre-created itineraries for quick discovery.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Filters used to create this itinerary
    cuisine = models.CharField(max_length=100, blank=True)
    price_range = models.CharField(max_length=50, blank=True)
    min_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    tags = models.JSONField(default=list, blank=True)  # List of tags
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=3.0)
    neighborhood = models.CharField(max_length=100, blank=True)
    
    # Itinerary data
    itinerary_data = models.JSONField(help_text="Full itinerary with restaurants and enrichment data")
    
    # Statistics
    total_restaurants = models.IntegerField(default=0)
    enriched_count = models.IntegerField(default=0)
    enrichment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Metadata
    is_featured = models.BooleanField(default=False, help_text="Show on home page")
    sample_image_url = models.URLField(max_length=500, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['cuisine', 'price_range', 'is_featured']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.neighborhood})"


class RestaurantDeduplication(models.Model):
    """
    Tracks potential duplicates and merge decisions
    """
    restaurant1 = models.ForeignKey(
        ScrapedRestaurant, 
        on_delete=models.CASCADE, 
        related_name='dup_as_restaurant1'
    )
    restaurant2 = models.ForeignKey(
        ScrapedRestaurant, 
        on_delete=models.CASCADE, 
        related_name='dup_as_restaurant2'
    )
    similarity_score = models.FloatField(help_text="Similarity score (0-1)")
    is_duplicate = models.BooleanField(null=True, blank=True, help_text="Manual verification")
    merged_into = models.ForeignKey(
        ScrapedRestaurant, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='merged_duplicates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('restaurant1', 'restaurant2')
        ordering = ['-similarity_score']
    
    def __str__(self):
        return f"{self.restaurant1.name} <-> {self.restaurant2.name} ({self.similarity_score:.2f})"