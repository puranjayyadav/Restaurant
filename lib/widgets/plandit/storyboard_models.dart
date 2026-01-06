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
  final String? opentableUrl;
  final String? resyUrl;
  final bool acceptsReservations;

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
    this.opentableUrl,
    this.resyUrl,
    this.acceptsReservations = false,
  });

  factory VenueVariant.fromJson(Map<String, dynamic> json) {
    // Extract coordinates from the API response
    final coords = json['coordinates'] as Map<String, dynamic>?;
    
    // Support multiple coordinate formats
    double? latitude = coords != null ? (coords['lat'] as num?)?.toDouble() : (json['latitude'] as num?)?.toDouble();
    double? longitude = coords != null ? (coords['lng'] as num?)?.toDouble() : (json['longitude'] as num?)?.toDouble();

    // Fallback for some scrapers that use 'lat'/'lng' at top level
    latitude ??= (json['lat'] as num?)?.toDouble();
    longitude ??= (json['lng'] as num?)?.toDouble();
    
    return VenueVariant(
      placeId: json['place_id']?.toString(),
      venue: json['name'] ?? 'Unknown Venue',
      venueType: json['category'] ?? 'Venue',
      description: json['reason'] ?? 'A great spot for your itinerary',
      aiNote: json['reason'] ?? 'Selected for your journey',
      rating: (json['rating'] ?? 4.5).toDouble(),
      price: _formatPrice(json['price_range'] ?? '\$\$'),
      lat: latitude,
      lng: longitude,
      insiderProfile: json['insider_profile'] as Map<String, dynamic>?,
      opentableUrl: json['opentable_url']?.toString(),
      resyUrl: json['resy_url']?.toString(),
      acceptsReservations: json['accepts_reservations'] == true,
    );
  }

  static String _formatPrice(String? price) {
    if (price == null || price.isEmpty) return '\$\$';
    return price;
  }
  
  // Getters for compatibility with BookingOptionsSheet
  String get name => venue;
  String? get phone => null; // Phone number not currently stored in VenueVariant
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
