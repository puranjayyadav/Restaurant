from rest_framework import serializers
from .models import Establishment, EstablishmentFeature, ScrapedRestaurant, RestaurantDeduplication

class EstablishmentFeatureSerializer(serializers.ModelSerializer):
    feature_type_display = serializers.CharField(source='get_feature_type_display', read_only=True)

    class Meta:
        model = EstablishmentFeature
        fields = ['feature_type', 'feature_type_display']

class EstablishmentSerializer(serializers.ModelSerializer):
    features = EstablishmentFeatureSerializer(many=True, read_only=True)
    price_range_display = serializers.CharField(source='get_price_range_display', read_only=True)
    dining_style_display = serializers.CharField(source='get_dining_style_display', read_only=True)

    class Meta:
        model = Establishment
        fields = [
            'id', 'name', 'address', 'price_range', 'price_range_display',
            'dining_style', 'dining_style_display', 'location_region',
            'latitude', 'longitude', 'features', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user']


class ScrapedRestaurantSerializer(serializers.ModelSerializer):
    """Serializer for scraped restaurant data"""
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    full_address = serializers.CharField(read_only=True)
    
    class Meta:
        model = ScrapedRestaurant
        fields = [
            'id', 'source', 'source_display', 'source_id', 'source_url',
            'name', 'description', 'address', 'street_address', 'city', 'state', 
            'zip_code', 'country', 'latitude', 'longitude', 'full_address',
            'rating', 'total_reviews', 'price_range', 'phone', 'website', 'email',
            'hours', 'categories', 'features', 'photos', 'menu_items', 'social_media',
            'is_verified', 'is_active', 'data_quality_score', 'duplicate_of',
            'scraped_at', 'last_updated', 'last_verified'
        ]
        read_only_fields = ['scraped_at', 'last_updated', 'data_quality_score']


class ScrapedRestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = ScrapedRestaurant
        fields = [
            'id', 'name', 'source', 'source_display', 'city', 'state',
            'latitude', 'longitude', 'rating', 'total_reviews', 'price_range',
            'is_verified', 'data_quality_score'
        ] 