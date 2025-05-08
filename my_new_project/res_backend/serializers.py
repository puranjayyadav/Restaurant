from rest_framework import serializers
from .models import Establishment, EstablishmentFeature

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