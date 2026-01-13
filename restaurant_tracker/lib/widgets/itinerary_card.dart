import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import '../theme/design_system.dart';

/// Card widget for displaying pre-created itinerary
class ItineraryCard extends StatelessWidget {
  final Map<String, dynamic> itinerary;
  final VoidCallback? onTap;

  static const _bannedPhotoKeywords = [
    'menu',
    'parking',
    'map',
    'floorplan',
    'logo',
    'qr',
    'takeout',
    'delivery',
    'doordash',
    'ubereats',
    'grubhub',
  ];

  const ItineraryCard({
    super.key,
    required this.itinerary,
    this.onTap,
  });

  /// Collect all valid photos from all restaurants in the itinerary
  List<String> _collectAllPhotos() {
    final List<String> allPhotos = [];
    final itineraryId = itinerary['id'] ?? 'unknown';

    try {
      final itineraryData = itinerary['itinerary_data'];
      if (itineraryData == null) {
        print('DEBUG: Itinerary $itineraryId has no itinerary_data');
        return allPhotos;
      }

      if (itineraryData is! Map<String, dynamic>) {
        print('DEBUG: Itinerary $itineraryId itinerary_data is not a Map');
        return allPhotos;
      }

      final itineraryItems = itineraryData['itinerary'];
      if (itineraryItems == null) {
        print('DEBUG: Itinerary $itineraryId has no itinerary_data.itinerary');
        return allPhotos;
      }

      if (itineraryItems is! List) {
        print(
            'DEBUG: Itinerary $itineraryId itinerary_data.itinerary is not a List');
        return allPhotos;
      }

      print('DEBUG: Itinerary $itineraryId has ${itineraryItems.length} items');

      for (var i = 0; i < itineraryItems.length; i++) {
        final item = itineraryItems[i];
        if (item == null || item is! Map<String, dynamic>) {
          continue;
        }

        final itemMap = Map<String, dynamic>.from(item);
        final placeName = itemMap['place_name']?.toString() ?? 'Unknown';

        // Try postgres_data photos
        final postgresData = itemMap['postgres_data'];
        if (postgresData != null && postgresData is Map<String, dynamic>) {
          final photos = postgresData['photos'];
          if (photos != null && photos is List) {
            print(
                'DEBUG: Item $i ($placeName) has ${photos.length} photos in postgres_data');
            for (var j = 0; j < photos.length && j < 5; j++) {
              final photo = photos[j];
              String? urlString;

              if (photo is String) {
                urlString = photo.trim();
              } else if (photo is Map) {
                // Try multiple possible keys
                urlString = photo['url']?.toString().trim() ??
                    photo['photo_reference']?.toString().trim() ??
                    photo['link']?.toString().trim();
              }

              if (urlString != null &&
                  urlString.isNotEmpty &&
                  urlString != 'null' &&
                  urlString != 'None' &&
                  (urlString.startsWith('http://') ||
                      urlString.startsWith('https://'))) {
                if (!allPhotos.contains(urlString)) {
                  allPhotos.add(urlString);
                  print('DEBUG: Added photo $j from $placeName: $urlString');
                }
              } else {
                print('DEBUG: Photo $j from $placeName is invalid: $photo');
              }
            }
          } else {
            print(
                'DEBUG: Item $i ($placeName) has no photos list in postgres_data');
          }
        } else {
          print('DEBUG: Item $i ($placeName) has no postgres_data');
        }

        // Try google_data photos as fallback
        final googleData = itemMap['google_data'];
        if (googleData != null && googleData is Map<String, dynamic>) {
          final photos = googleData['photos'];
          if (photos != null && photos is List) {
            print(
                'DEBUG: Item $i ($placeName) has ${photos.length} photos in google_data');
            for (var j = 0; j < photos.length && j < 5; j++) {
              final photo = photos[j];
              String? urlString;

              if (photo is String) {
                urlString = photo.trim();
              } else if (photo is Map) {
                // Try multiple possible keys
                urlString = photo['url']?.toString().trim() ??
                    photo['photo_reference']?.toString().trim() ??
                    photo['link']?.toString().trim();
              }

              if (urlString != null &&
                  urlString.isNotEmpty &&
                  urlString != 'null' &&
                  urlString != 'None' &&
                  (urlString.startsWith('http://') ||
                      urlString.startsWith('https://'))) {
                if (!allPhotos.contains(urlString)) {
                  allPhotos.add(urlString);
                  print(
                      'DEBUG: Added photo $j from google_data for $placeName: $urlString');
                }
              }
            }
          }
        }

        // Try direct photos field (some items might have photos at root level)
        final directPhotos = itemMap['photos'];
        if (directPhotos != null && directPhotos is List) {
          print(
              'DEBUG: Item $i ($placeName) has ${directPhotos.length} photos at root level');
          for (var j = 0; j < directPhotos.length && j < 5; j++) {
            final photo = directPhotos[j];
            String? urlString;

            if (photo is String) {
              urlString = photo.trim();
            } else if (photo is Map) {
              urlString = photo['url']?.toString().trim() ??
                  photo['photo_reference']?.toString().trim() ??
                  photo['link']?.toString().trim();
            }

            if (urlString != null &&
                urlString.isNotEmpty &&
                urlString != 'null' &&
                urlString != 'None' &&
                (urlString.startsWith('http://') ||
                    urlString.startsWith('https://'))) {
              if (!allPhotos.contains(urlString)) {
                allPhotos.add(urlString);
                print(
                    'DEBUG: Added photo $j from root level for $placeName: $urlString');
              }
            }
          }
        }
      }

      print(
          'DEBUG: Itinerary $itineraryId collected ${allPhotos.length} total photos');
    } catch (e, stackTrace) {
      print(
          'ERROR: Exception in _collectAllPhotos for itinerary $itineraryId: $e');
      print('ERROR: Stack trace: $stackTrace');
    }

    return allPhotos;
  }

  int _scorePhoto(String url, String title) {
    var score = 0;
    final lower = url.toLowerCase();

    // Penalize banned keywords
    for (final bad in _bannedPhotoKeywords) {
      if (lower.contains(bad)) {
        score -= 50;
      }
    }

    // Prefer common photo extensions
    if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) score += 10;
    if (lower.contains('photo')) score += 5;

    // Prefer https
    if (lower.startsWith('https://')) score += 5;

    // Light title match (vibe/cuisine)
    final titleWords = title.toLowerCase().split(RegExp(r'\s+'));
    for (final w in titleWords) {
      if (w.length >= 4 && lower.contains(w)) score += 3;
    }

    return score;
  }

  String? _selectBestPhoto(List<String> photos, String title) {
    if (photos.isEmpty) return null;
    var best = photos.first;
    var bestScore = _scorePhoto(best, title);

    for (var i = 1; i < photos.length; i++) {
      final score = _scorePhoto(photos[i], title);
      if (score > bestScore) {
        bestScore = score;
        best = photos[i];
      }
    }
    return best;
  }

  /// Choose the best photo from the itinerary pool using simple quality heuristics
  String? _getImageUrl() {
    try {
      final title = itinerary['title']?.toString() ?? '';
      // Collect all photos from all restaurants
      final allPhotos = _collectAllPhotos();

      if (allPhotos.isEmpty) {
        // Fallback to sample_image_url if no photos found in itinerary
        final sampleImageUrl = itinerary['sample_image_url'];
        if (sampleImageUrl != null) {
          final urlString = sampleImageUrl.toString().trim();
          if (urlString.isNotEmpty &&
              urlString != 'null' &&
              urlString != 'None' &&
              (urlString.startsWith('http://') ||
                  urlString.startsWith('https://'))) {
            return urlString;
          }
        }
        return null;
      }

      // Filter and score for best match
      final best = _selectBestPhoto(allPhotos, title);
      print('DEBUG: Selected best photo for "$title": $best');
      return best;
    } catch (e, stackTrace) {
      print('ERROR: Exception in _getImageUrl: $e');
      print('ERROR: Stack trace: $stackTrace');
    }

    return null;
  }

  String _getTagText() {
    try {
      // Safely get tags
      final tagsRaw = itinerary['tags'];
      List<dynamic> tags = [];
      if (tagsRaw != null) {
        if (tagsRaw is List) {
          tags = tagsRaw;
        } else {
          tags = [];
        }
      }

      final cuisine = (itinerary['cuisine'] as String?) ?? '';
      final neighborhood = (itinerary['neighborhood'] as String?) ?? '';

      // Priority: tags > cuisine > neighborhood
      if (tags.isNotEmpty) {
        final tag = tags[0]?.toString() ?? '';
        if (tag.isNotEmpty) {
          // Map common tags to shorter display names
          final tagLower = tag.toLowerCase();
          if (tagLower.contains('breakfast') || tagLower.contains('brunch')) {
            return 'Breakfast';
          }
          if (tagLower.contains('romantic')) {
            return 'Romantic';
          }
          if (tagLower.contains('outdoor')) {
            return 'Outdoor';
          }
          return tag.length > 12 ? tag.substring(0, 12) : tag;
        }
      }
      if (cuisine.isNotEmpty) {
        return cuisine;
      }
      if (neighborhood.isNotEmpty) {
        return neighborhood;
      }
    } catch (e) {
      print('ERROR: Exception in _getTagText: $e');
    }
    return '';
  }

  Color _getTagColor() {
    final tagText = _getTagText().toLowerCase();

    // Orange for breakfast/brunch
    if (tagText.contains('breakfast') || tagText.contains('brunch')) {
      return AppColors.orange;
    }
    // Teal for everything else (art, romantic, etc.)
    return AppColors.teal;
  }

  @override
  Widget build(BuildContext context) {
    try {
      final textTheme = Theme.of(context).textTheme;
      final title = itinerary['title'] as String? ?? 'Untitled Itinerary';
      final imageUrl = _getImageUrl();
      final tagText = _getTagText();
      final tagColor = _getTagColor();

      return ShadCard(
        backgroundColor: AppColors.surfaceElevated,
        padding: EdgeInsets.zero,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppBorderRadius.large),
          child: Container(
            height: 300,
            width: double.infinity,
            child: Stack(
              children: [
                // Full size image
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppBorderRadius.large),
                  child: Container(
                    width: double.infinity,
                    height: double.infinity,
                    color: AppColors.surface,
                    child: imageUrl != null
                        ? Image.network(
                            imageUrl,
                            fit: BoxFit.cover,
                            width: double.infinity,
                            height: double.infinity,
                            loadingBuilder: (context, child, loadingProgress) {
                              if (loadingProgress == null) return child;
                              return Container(
                                color: AppColors.surface,
                                child: Center(
                                  child: CircularProgressIndicator(
                                    value: loadingProgress.expectedTotalBytes !=
                                            null
                                        ? loadingProgress
                                                .cumulativeBytesLoaded /
                                            loadingProgress.expectedTotalBytes!
                                        : null,
                                    color: AppColors.orange,
                                  ),
                                ),
                              );
                            },
                            errorBuilder: (context, error, stackTrace) {
                              return _buildPlaceholderImage();
                            },
                          )
                        : _buildPlaceholderImage(),
                  ),
                ),
                // Gradient fade effect from bottom to top
                Positioned.fill(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(AppBorderRadius.large),
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [
                            Colors.black
                                .withOpacity(0.8), // Fully opaque at bottom
                            Colors.black.withOpacity(0.6),
                            Colors.black.withOpacity(0.4),
                            Colors.black.withOpacity(0.2),
                            Colors.black
                                .withOpacity(0.0), // Fully transparent at top
                          ],
                          stops: [0.0, 0.3, 0.5, 0.7, 1.0],
                        ),
                      ),
                    ),
                  ),
                ),
                // Title text at bottom
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: Padding(
                    padding: EdgeInsets.all(AppSpacing.md),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Tag at top of text area
                        if (tagText.isNotEmpty)
                          Padding(
                            padding: EdgeInsets.only(bottom: AppSpacing.xs),
                            child: Container(
                              padding: EdgeInsets.symmetric(
                                horizontal: AppSpacing.sm,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: tagColor.withOpacity(0.95),
                                borderRadius: BorderRadius.circular(
                                    AppBorderRadius.small),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withOpacity(0.3),
                                    blurRadius: 4,
                                    offset: Offset(0, 2),
                                  ),
                                ],
                              ),
                              child: Text(
                                tagText,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.5,
                                  fontFamily: 'MeeraInimai',
                                ),
                              ),
                            ),
                          ),
                        // Title text
                        Text(
                          title,
                          style: textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            fontSize: 18,
                            shadows: [
                              Shadow(
                                color: Colors.black.withOpacity(0.5),
                                blurRadius: 4,
                                offset: Offset(0, 2),
                              ),
                            ],
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    } catch (e, stackTrace) {
      print('ERROR: Exception building ItineraryCard: $e');
      print('ERROR: Stack trace: $stackTrace');
      print('ERROR: Itinerary data: $itinerary');
      // Return a safe fallback widget
      return ShadCard(
        backgroundColor: AppColors.surfaceElevated,
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.md),
          child: Column(
            children: [
              Icon(Icons.error_outline, color: AppColors.error),
              SizedBox(height: AppSpacing.sm),
              Text(
                'Error loading itinerary',
                style: TextStyle(color: AppColors.error),
              ),
            ],
          ),
        ),
      );
    }
  }

  Widget _buildPlaceholderImage() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.orange.withOpacity(0.1),
            AppColors.teal.withOpacity(0.1),
          ],
        ),
      ),
      child: Center(
        child: Icon(
          Icons.restaurant_menu,
          size: 56,
          color: AppColors.textSecondary.withOpacity(0.5),
        ),
      ),
    );
  }
}
