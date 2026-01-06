import 'package:flutter/material.dart';

class VenueVariant {
  final String? placeId;
  final String venue;
  final String venueType;
  final String description;
  final String aiNote;
  final double rating;
  final String price;
  final double? lat;
  final double? lng;
  final Map<String, dynamic>? insiderProfile;

  VenueVariant({
    this.placeId,
    required this.venue,
    required this.venueType,
    required this.description,
    required this.aiNote,
    required this.rating,
    required this.price,
    this.lat,
    this.lng,
    this.insiderProfile,
  });

  factory VenueVariant.fromJson(Map<String, dynamic> json) {
    // Extract coordinates from the API response
    final coords = json['coordinates'] as Map<String, dynamic>?;
    
    return VenueVariant(
      placeId: json['place_id']?.toString(),
      venue: json['name'] ?? 'Unknown Venue',
      venueType: json['category'] ?? 'Venue',
      description: json['reason'] ?? 'A great spot for your itinerary',
      aiNote: json['reason'] ?? 'Selected for your journey',
      rating: (json['rating'] ?? 4.5).toDouble(),
      price: _formatPrice(json['price_range'] ?? '\$\$'),
      lat: coords != null ? (coords['lat'] as num?)?.toDouble() : null,
      lng: coords != null ? (coords['lng'] as num?)?.toDouble() : null,
      insiderProfile: json['insider_profile'] as Map<String, dynamic>?,
    );
  }

  static String _formatPrice(String? price) {
    if (price == null || price.isEmpty) return '\$\$';
    return price;
  }
}

class Chapter {
  final String id;
  final String time;
  final String title;
  final IconData icon;
  final String image;
  final String? duration;
  final String? walkInfo;
  final Map<String, VenueVariant> variants;
  final Map<String, VenueVariant> budgetVariants;

  Chapter({
    required this.id,
    required this.time,
    required this.title,
    required this.icon,
    required this.image,
    this.duration,
    this.walkInfo,
    required this.variants,
    required this.budgetVariants,
  });
}
