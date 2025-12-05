from django.contrib import admin
from .models import (
    Establishment, EstablishmentFeature, UserInteraction,
    PublicItinerary, ItineraryLike, UserStats,
    ScrapedRestaurant, RestaurantDeduplication
)

@admin.register(ScrapedRestaurant)
class ScrapedRestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'source', 'city', 'state', 'safe_rating', 'data_quality_score', 'is_verified', 'scraped_at')
    list_filter = ('source', 'is_verified', 'is_active', 'city', 'state', 'country')
    search_fields = ('name', 'address', 'city', 'state', 'source_id')
    readonly_fields = ('scraped_at', 'last_updated', 'data_quality_score')
    list_per_page = 50
    
    def safe_rating(self, obj):
        """Safely display rating, handling any conversion errors"""
        try:
            if obj.rating is not None:
                return f"{float(obj.rating):.2f}"
            return "-"
        except (ValueError, TypeError, AttributeError):
            return "-"
    safe_rating.short_description = 'Rating'
    safe_rating.admin_order_field = 'rating'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'source', 'source_id', 'source_url')
        }),
        ('Location', {
            'fields': ('address', 'street_address', 'city', 'state', 'zip_code', 'country', 'latitude', 'longitude')
        }),
        ('Ratings & Contact', {
            'fields': ('rating', 'total_reviews', 'price_range', 'phone', 'website', 'email')
        }),
        ('Rich Data', {
            'fields': ('hours', 'categories', 'features', 'photos', 'menu_items', 'social_media', 'raw_data'),
            'classes': ('collapse',)
        }),
        ('Management', {
            'fields': ('is_verified', 'is_active', 'data_quality_score', 'duplicate_of', 'last_verified')
        }),
        ('Timestamps', {
            'fields': ('scraped_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RestaurantDeduplication)
class RestaurantDeduplicationAdmin(admin.ModelAdmin):
    list_display = ('restaurant1', 'restaurant2', 'similarity_score', 'is_duplicate', 'merged_into', 'created_at')
    list_filter = ('is_duplicate', 'created_at', 'reviewed_at')
    search_fields = ('restaurant1__name', 'restaurant2__name')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Restaurants', {
            'fields': ('restaurant1', 'restaurant2')
        }),
        ('Deduplication', {
            'fields': ('similarity_score', 'is_duplicate', 'merged_into', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

# Register existing models if not already registered
if not admin.site.is_registered(Establishment):
    admin.site.register(Establishment)
if not admin.site.is_registered(EstablishmentFeature):
    admin.site.register(EstablishmentFeature)
if not admin.site.is_registered(UserInteraction):
    admin.site.register(UserInteraction)
if not admin.site.is_registered(PublicItinerary):
    admin.site.register(PublicItinerary)
if not admin.site.is_registered(ItineraryLike):
    admin.site.register(ItineraryLike)
if not admin.site.is_registered(UserStats):
    admin.site.register(UserStats)
