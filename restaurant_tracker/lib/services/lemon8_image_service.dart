import 'dart:math';

class Lemon8ImageService {
  // Curated stock images of Soho/NYC for a premium feel
  static const List<String> _sohoImages = [
    'https://images.unsplash.com/photo-1541336032412-2048a6789400?q=80&w=800&auto=format&fit=crop', // Cobblestone street Soho
    'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?q=80&w=800&auto=format&fit=crop', // NYC street dusk
    'https://images.unsplash.com/photo-1514565131-fce0801e5785?q=80&w=800&auto=format&fit=crop', // Soho brick building
    'https://images.unsplash.com/photo-1485871981521-5b1fd3805eee?q=80&w=800&auto=format&fit=crop', // NYC street nighttime
    'https://images.unsplash.com/photo-1518391846015-55a9cc003b25?q=80&w=800&auto=format&fit=crop', // NYC atmosphere
    'https://images.unsplash.com/photo-1538330627166-33d1908c210d?q=80&w=800&auto=format&fit=crop', // Soho architecture
  ];

  static const List<String> _foodImages = [
    'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=800&auto=format&fit=crop', // Omakase/Sushi
    'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=800&auto=format&fit=crop', // Upscale restaurant
    'https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=800&auto=format&fit=crop', // Wine/Cocktails
  ];

  static String getRandomSohoImage(String? query) {
    // Attempt to match query for better contextual imagery
    final lowerQuery = query?.toLowerCase() ?? '';
    if (lowerQuery.contains('sushi') || lowerQuery.contains('food') || lowerQuery.contains('dinner')) {
      return _foodImages[Random().nextInt(_foodImages.length)];
    }
    
    // Default to Soho street aesthetics
    return _sohoImages[Random().nextInt(_sohoImages.length)];
  }

  static String getItineraryImage(Map<String, dynamic> result) {
    final title = (result['title'] ?? '').toString().toLowerCase();
    final vibes = (result['contained_vibes'] ?? []).toString().toLowerCase();
    
    if (title.contains('sushi') || vibes.contains('sushi') || title.contains('omakase')) {
      return 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=800&auto=format&fit=crop';
    }
    
    if (title.contains('wine') || vibes.contains('wine') || vibes.contains('bar')) {
      return 'https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=800&auto=format&fit=crop';
    }

    if (title.contains('soho')) {
      return _sohoImages[0]; // Classic Soho street
    }

    return _sohoImages[Random().nextInt(_sohoImages.length)];
  }
}
