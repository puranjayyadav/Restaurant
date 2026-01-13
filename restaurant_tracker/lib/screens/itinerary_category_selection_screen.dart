import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:location/location.dart' as loc;
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'dart:async';
import '../theme/design_system.dart';
import '../api_service.dart';
import '../widgets/location_autocomplete.dart' as location_autocomplete;
import 'package:firebase_auth/firebase_auth.dart';
import 'curated_journey_preview_screen.dart';

class ItineraryCategorySelectionScreen extends StatefulWidget {
  const ItineraryCategorySelectionScreen({super.key});

  @override
  State<ItineraryCategorySelectionScreen> createState() =>
      _ItineraryCategorySelectionScreenState();
}

class _ItineraryCategorySelectionScreenState
    extends State<ItineraryCategorySelectionScreen> {
  final Map<String, bool> _selectedCategories = {
    'restaurants': true,
    'cafes': true,
    'museums': false,
    'parks': false,
    'shopping': false,
    'bars': false,
    'dessert': true,
  };

  final Map<String, IconData> _categoryIcons = {
    'restaurants': Icons.restaurant,
    'cafes': Icons.local_cafe,
    'museums': Icons.museum,
    'parks': Icons.park,
    'shopping': Icons.shopping_bag,
    'bars': Icons.local_bar,
    'dessert': Icons.cake,
  };

  final Map<String, String> _categoryLabels = {
    'restaurants': 'Restaurants',
    'cafes': 'Cafes & Coffee',
    'museums': 'Museums & Galleries',
    'parks': 'Parks & Outdoor',
    'shopping': 'Shopping',
    'bars': 'Bars & Nightlife',
    'dessert': 'Dessert & Ice Cream',
  };

  // NEW: Location state
  final TextEditingController _locationController = TextEditingController();
  final ApiService _apiService = ApiService();
  double? _selectedLat;
  double? _selectedLon;
  String? _selectedLocationName;
  bool _useCurrentLocation = true;
  double? _currentLat;
  double? _currentLon;
  bool _isLoadingLocation = false;

  // NEW: Radius state
  double _explorationRadius = 2.0; // Default 2km
  final double _minRadius = 1.0;
  final double _maxRadius = 10.0;

  // NEW: Map state
  final MapController _mapController = MapController();
  List<CircleMarker> _circles = [];
  List<Marker> _markers = [];

  // Background generation state
  bool _isGenerating = false;
  Future<Map<String, dynamic>?>? _generationFuture;

  // Vegetarian filter
  bool _vegetarianFilter = false;

  @override
  void initState() {
    super.initState();
    _getCurrentLocation();
  }

  @override
  void dispose() {
    _locationController.dispose();
    _mapController.dispose();
    super.dispose();
  }

  Future<void> _getCurrentLocation() async {
    setState(() => _isLoadingLocation = true);
    try {
      final location = loc.Location();
      final locationData = await location.getLocation();
      setState(() {
        _currentLat = locationData.latitude;
        _currentLon = locationData.longitude;
        _isLoadingLocation = false;
      });
      _updateMapLocation(_currentLat, _currentLon);
    } catch (e) {
      print('Error getting current location: $e');
      setState(() => _isLoadingLocation = false);
    }
  }

  void _updateMapLocation(double? lat, double? lon) {
    if (lat == null || lon == null) return;

    final position = LatLng(lat, lon);

    // Update map camera (FlutterMap uses different API)
    _mapController.move(position, 13.0);

    // Update marker
    setState(() {
      _markers = [
        Marker(
          point: position,
          width: 40,
          height: 40,
          child: Icon(
            Icons.location_on,
            color: AppColors.primary,
            size: 40,
          ),
        ),
      ];

      // Update circle to show radius
      _circles = [
        CircleMarker(
          point: position,
          radius: _explorationRadius * 1000, // Convert km to meters
          color: AppColors.primary.withOpacity(0.15),
          borderColor: AppColors.primary.withOpacity(0.5),
          borderStrokeWidth: 2,
        ),
      ];
    });
  }

  void _toggleCategory(String category) {
    setState(() {
      _selectedCategories[category] = !_selectedCategories[category]!;
    });
  }

  void _selectAll() {
    setState(() {
      _selectedCategories.forEach((key, value) {
        _selectedCategories[key] = true;
      });
    });
  }

  void _deselectAll() {
    setState(() {
      _selectedCategories.forEach((key, value) {
        _selectedCategories[key] = false;
      });
    });
  }

  List<String> get _selectedCategoryList {
    return _selectedCategories.entries
        .where((entry) => entry.value)
        .map((entry) => entry.key)
        .toList();
  }

  // Location selection is now handled by FoursquareAutocompleteTextField's onPlaceSelected callback

  Future<void> _useMyLocation() async {
    setState(() {
      _useCurrentLocation = true;
      _selectedLat = null;
      _selectedLon = null;
      _selectedLocationName = null;
      _locationController.clear();
    });

    _updateMapLocation(_currentLat, _currentLon);

    if (mounted) {
      ShadToaster.of(context).show(
        const ShadToast(
          title: Text('Using your current location'),
          description: Text('We\'ll find places near you'),
        ),
      );
    }
  }

  void _onRadiusChanged(double value) {
    setState(() {
      _explorationRadius = value;
    });
    _updateMapLocation(
      _selectedLat ?? _currentLat,
      _selectedLon ?? _currentLon,
    );
  }

  // NEW: Build interactive map with overlay search bar
  Widget _buildInteractiveMap() {
    final lat = _selectedLat ?? _currentLat ?? 40.7128; // Default to NYC
    final lon = _selectedLon ?? _currentLon ?? -74.0060;

    return SizedBox(
      height:
          MediaQuery.of(context).size.height * 0.5, // Reduced from 0.75 to 0.5
      child: Stack(
        children: [
          // Interactive OpenStreetMap (FlutterMap)
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: LatLng(lat, lon),
              initialZoom: 13.0,
              onTap: (tapPosition, point) {
                setState(() {
                  _selectedLat = point.latitude;
                  _selectedLon = point.longitude;
                  _useCurrentLocation = false;
                  _locationController.text =
                      '${point.latitude.toStringAsFixed(4)}, ${point.longitude.toStringAsFixed(4)}';
                });
                _updateMapLocation(point.latitude, point.longitude);
              },
            ),
            children: [
              // OpenStreetMap tile layer
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.yourcompany.restaurant_tracker',
                maxZoom: 19,
              ),
              // Circle layer (exploration radius)
              CircleLayer(
                circles: _circles,
              ),
              // Marker layer
              MarkerLayer(
                markers: _markers,
              ),
            ],
          ),

          // Transparent search bar overlay at top
          Positioned(
            top: AppSpacing.xl * 2, // Moved down from AppSpacing.md
            left: AppSpacing.md,
            right: AppSpacing.md,
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1), // 90% transparent
                borderRadius: BorderRadius.circular(AppBorderRadius.medium),
                border: Border.all(
                  color: Colors.white.withOpacity(0.3),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: location_autocomplete.LocationAutocompleteTextField(
                controller: _locationController,
                hintText: 'Search location...',
                lat: _currentLat,
                lon: _currentLon,
                inputDecoration: InputDecoration(
                  hintText: 'Search location...',
                  hintStyle: TextStyle(
                    color: Colors.white.withOpacity(0.8),
                    fontSize: AppTypography.bodyMedium,
                  ),
                  prefixIcon: Icon(
                    Icons.search,
                    color: Colors.white.withOpacity(0.9),
                  ),
                  suffixIcon: _locationController.text.isNotEmpty
                      ? IconButton(
                          icon: Icon(
                            Icons.clear,
                            color: Colors.white.withOpacity(0.9),
                          ),
                          onPressed: () {
                            _locationController.clear();
                            _useMyLocation();
                          },
                        )
                      : null,
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.md,
                  ),
                ),
                textStyle: TextStyle(
                  color: Colors.white,
                  fontSize: AppTypography.bodyMedium,
                ),
                onPlaceSelected: (place) {
                  final geometry = place['geometry'] as Map<String, dynamic>?;
                  final location =
                      geometry?['location'] as Map<String, dynamic>?;
                  if (location != null) {
                    setState(() {
                      _selectedLat = location['lat'] as double?;
                      _selectedLon = location['lng'] as double?;
                      _useCurrentLocation = false;
                      _selectedLocationName = place['description'] as String?;
                    });
                    _updateMapLocation(_selectedLat, _selectedLon);
                  }
                },
              ),
            ),
          ),

          // My Location button overlay
          Positioned(
            top: AppSpacing.xl * 2 + 60, // Aligned with search bar position
            right: AppSpacing.md,
            child: FloatingActionButton.small(
              backgroundColor: Colors.white.withOpacity(0.95),
              onPressed: _isLoadingLocation ? null : _useMyLocation,
              child: _isLoadingLocation
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation(AppColors.primary),
                      ),
                    )
                  : Icon(
                      Icons.my_location,
                      color: AppColors.primary,
                    ),
            ),
          ),

          // Radius info overlay at bottom of map (compact transparent design)
          Positioned(
            bottom: AppSpacing.sm,
            left: AppSpacing.lg,
            right: AppSpacing.lg,
            child: Container(
              padding: EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xs,
              ),
              decoration: BoxDecoration(
                color: Colors.white
                    .withOpacity(0.2), // 80% transparent (10% more visible)
                borderRadius: BorderRadius.circular(AppBorderRadius.small),
                border: Border.all(
                  color: Colors.white.withOpacity(0.3),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Compact text
                  Text(
                    '📏 ${_explorationRadius.toStringAsFixed(1)} km',
                    style: TextStyle(
                      fontSize: AppTypography.bodySmall,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(width: AppSpacing.sm),
                  // Compact slider
                  Expanded(
                    child: SliderTheme(
                      data: SliderThemeData(
                        trackHeight: 2,
                        thumbShape:
                            RoundSliderThumbShape(enabledThumbRadius: 6),
                        overlayShape:
                            RoundSliderOverlayShape(overlayRadius: 12),
                      ),
                      child: Slider(
                        value: _explorationRadius,
                        min: _minRadius,
                        max: _maxRadius,
                        divisions: 18,
                        activeColor: Colors.white,
                        inactiveColor: Colors.white.withOpacity(0.3),
                        onChanged: _onRadiusChanged,
                      ),
                    ),
                  ),
                  SizedBox(width: AppSpacing.sm),
                  // Compact preset buttons
                  ...[2.0, 5.0, 10.0].map((radius) {
                    final isSelected = _explorationRadius == radius;
                    return Padding(
                      padding: EdgeInsets.only(left: AppSpacing.xs / 2),
                      child: InkWell(
                        onTap: () => _onRadiusChanged(radius),
                        borderRadius:
                            BorderRadius.circular(AppBorderRadius.small),
                        child: Container(
                          padding: EdgeInsets.symmetric(
                            horizontal: AppSpacing.xs,
                            vertical: AppSpacing.xs / 2,
                          ),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? AppColors.primary
                                : Colors.white.withOpacity(0.15),
                            borderRadius:
                                BorderRadius.circular(AppBorderRadius.small),
                          ),
                          child: Text(
                            '${radius.toInt()}',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: AppTypography.labelSmall - 2,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasSelection = _selectedCategoryList.isNotEmpty;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          // Interactive Map at top (75% of screen)
          _buildInteractiveMap(),

          // Bottom section (remaining 50% of screen)
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(AppBorderRadius.large),
                ),
              ),
              child: Column(
                children: [
                  Expanded(
                    child: ListView(
                      padding: EdgeInsets.all(AppSpacing.md),
                      children: [
                        // Categories Header
                        Text(
                          '🏷️ Select Categories',
                          style: TextStyle(
                            fontSize: AppTypography.titleMedium,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        SizedBox(height: AppSpacing.sm),
                        // Select All / Deselect All buttons
                        Row(
                          children: [
                            Expanded(
                              child: ShadButton(
                                size: ShadButtonSize.sm,
                                onPressed: _selectAll,
                                backgroundColor: AppColors.surface,
                                child: Text(
                                  'Select All',
                                  style:
                                      TextStyle(color: AppColors.textPrimary),
                                ),
                              ),
                            ),
                            SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: ShadButton(
                                size: ShadButtonSize.sm,
                                onPressed: _deselectAll,
                                backgroundColor: AppColors.surface,
                                child: Text(
                                  'Clear All',
                                  style:
                                      TextStyle(color: AppColors.textPrimary),
                                ),
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: AppSpacing.md),

                        // Category checkboxes
                        ..._selectedCategories.keys.map((category) {
                          final isSelected = _selectedCategories[category]!;
                          return Padding(
                            padding: EdgeInsets.only(bottom: AppSpacing.sm),
                            child: InkWell(
                              onTap: () => _toggleCategory(category),
                              borderRadius:
                                  BorderRadius.circular(AppBorderRadius.medium),
                              child: Container(
                                decoration: BoxDecoration(
                                  color: isSelected
                                      ? AppColors.primary.withOpacity(0.08)
                                      : AppColors.surfaceElevated,
                                  borderRadius: BorderRadius.circular(
                                      AppBorderRadius.medium),
                                  border: Border.all(
                                    color: isSelected
                                        ? AppColors.primary
                                        : AppColors.border,
                                    width: isSelected ? 2 : 1,
                                  ),
                                ),
                                child: Padding(
                                  padding: EdgeInsets.all(AppSpacing.md),
                                  child: Row(
                                    children: [
                                      Container(
                                        padding: EdgeInsets.all(AppSpacing.sm),
                                        decoration: BoxDecoration(
                                          color: isSelected
                                              ? AppColors.primary
                                                  .withOpacity(0.1)
                                              : AppColors.surface,
                                          borderRadius: BorderRadius.circular(
                                              AppBorderRadius.small),
                                        ),
                                        child: Icon(
                                          _categoryIcons[category],
                                          color: isSelected
                                              ? AppColors.primary
                                              : AppColors.textSecondary,
                                          size: 24,
                                        ),
                                      ),
                                      SizedBox(width: AppSpacing.md),
                                      Expanded(
                                        child: Text(
                                          _categoryLabels[category]!,
                                          style: TextStyle(
                                            fontSize: AppTypography.bodyLarge,
                                            fontWeight: isSelected
                                                ? FontWeight.w600
                                                : FontWeight.w500,
                                            color: isSelected
                                                ? AppColors.textPrimary
                                                : AppColors.textSecondary,
                                          ),
                                        ),
                                      ),
                                      if (isSelected)
                                        Icon(
                                          Icons.check_circle,
                                          color: AppColors.primary,
                                          size: 24,
                                        ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          );
                        }).toList(),
                        SizedBox(height: AppSpacing.lg),

                        // Vegetarian filter section
                        Container(
                          padding: EdgeInsets.all(AppSpacing.md),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceElevated,
                            borderRadius:
                                BorderRadius.circular(AppBorderRadius.medium),
                            border: Border.all(
                              color: AppColors.border,
                              width: 1,
                            ),
                          ),
                          child: Row(
                            children: [
                              Container(
                                padding: EdgeInsets.all(AppSpacing.sm),
                                decoration: BoxDecoration(
                                  color: _vegetarianFilter
                                      ? AppColors.success.withOpacity(0.1)
                                      : AppColors.surface,
                                  borderRadius: BorderRadius.circular(
                                      AppBorderRadius.small),
                                ),
                                child: Icon(
                                  Icons.eco,
                                  color: _vegetarianFilter
                                      ? AppColors.success
                                      : AppColors.textSecondary,
                                  size: 24,
                                ),
                              ),
                              SizedBox(width: AppSpacing.md),
                              Expanded(
                                child: Text(
                                  'Vegetarian Options Available',
                                  style: TextStyle(
                                    fontSize: AppTypography.bodyLarge,
                                    fontWeight: _vegetarianFilter
                                        ? FontWeight.w600
                                        : FontWeight.w500,
                                    color: _vegetarianFilter
                                        ? AppColors.textPrimary
                                        : AppColors.textSecondary,
                                  ),
                                ),
                              ),
                              Switch(
                                value: _vegetarianFilter,
                                onChanged: (value) {
                                  setState(() {
                                    _vegetarianFilter = value;
                                  });
                                },
                                activeColor: AppColors.success,
                              ),
                            ],
                          ),
                        ),
                        SizedBox(height: AppSpacing.lg),

                        // Generate button at bottom (scrollable with content)
                        SizedBox(
                          width: double.infinity,
                          child: ShadButton(
                            size: ShadButtonSize.lg,
                            backgroundColor: (hasSelection && !_isGenerating)
                                ? AppColors.primary
                                : AppColors.border,
                            onPressed: (hasSelection && !_isGenerating)
                                ? () {
                                    _startBackgroundGeneration();
                                  }
                                : null,
                            child: _isGenerating
                                ? Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          valueColor:
                                              AlwaysStoppedAnimation<Color>(
                                                  Colors.white),
                                        ),
                                      ),
                                      SizedBox(width: AppSpacing.sm),
                                      Text(
                                        'Generating...',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 16,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                    ],
                                  )
                                : Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        hasSelection
                                            ? 'Generate My Day (${_selectedCategoryList.length})'
                                            : 'Select at least one',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 16,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                      if (hasSelection) ...[
                                        SizedBox(width: AppSpacing.sm),
                                        const Icon(Icons.arrow_forward,
                                            size: 20, color: Colors.white),
                                      ],
                                    ],
                                  ),
                          ),
                        ),
                        SizedBox(height: AppSpacing.xl), // Bottom padding
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _startBackgroundGeneration() async {
    if (_isGenerating) return;

    setState(() {
      _isGenerating = true;
    });

    try {
      // Start generation in background
      _generationFuture = _generateItineraryInBackground();

      // Monitor completion and navigate
      final result = await _generationFuture;

      setState(() {
        _isGenerating = false;
      });

      if (result != null && result['itinerary'] != null) {
        final itinerary = result['itinerary'] as List<dynamic>;

        if (itinerary.isNotEmpty && mounted) {
          // Transform result to match preview screen format
          final previewItinerary = {
            'title': 'Your Curated Journey',
            'new_title': 'Your Curated Journey',
            'subtitle': _getSubtitleFromCategories(
                result['selectedCategories'] as List<String>? ?? []),
            'description':
                'An experience curated just for you, designed to unfold like the best stories do...',
            'itinerary_data': {
              'itinerary': itinerary,
            },
          };

          // Navigate to CuratedJourneyPreviewScreen
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => CuratedJourneyPreviewScreen(
                itinerary: previewItinerary,
                onClose: () => Navigator.pop(context),
              ),
              fullscreenDialog: true,
            ),
          );
        } else {
          // Show error if no itinerary generated
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                    'Could not generate itinerary. Please try again with different settings.'),
                backgroundColor: Colors.red,
              ),
            );
          }
        }
      } else {
        // Show error if generation failed
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                  'Failed to generate itinerary. Please check your location and try again.'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (error) {
      print('Background generation error: $error');
      setState(() {
        _isGenerating = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${error.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  String _getSubtitleFromCategories(List<String> categories) {
    if (categories.isEmpty) return 'A Curated Experience';
    final categoryDisplayNames = {
      'restaurants': 'Restaurant',
      'cafes': 'Cafe',
      'museums': 'Museum',
      'parks': 'Park',
      'shopping': 'Shopping',
      'bars': 'Bar',
      'dessert': 'Dessert',
    };
    final categoryNames =
        categories.map((c) => categoryDisplayNames[c] ?? c).toList();
    if (categoryNames.length == 1) {
      return 'A ${categoryNames.first} Experience';
    } else if (categoryNames.length == 2) {
      return '${categoryNames.first} & ${categoryNames.last}';
    } else {
      return '${categoryNames.take(2).join(', ')} & More';
    }
  }

  Future<Map<String, dynamic>?> _generateItineraryInBackground() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return null;

      // Get location
      loc.LocationData? location;
      if (_useCurrentLocation) {
        location = await loc.Location().getLocation();
      } else if (_selectedLat != null && _selectedLon != null) {
        location = loc.LocationData.fromMap({
          'latitude': _selectedLat,
          'longitude': _selectedLon,
        });
      } else {
        return null;
      }

      if (location.latitude == null || location.longitude == null) {
        return null;
      }

      // Determine additional keywords
      final List<String> additionalKeywords = [];
      if (_selectedCategoryList.contains('museums')) {
        additionalKeywords.addAll(['museum', 'art_gallery']);
      }
      if (_selectedCategoryList.contains('parks')) {
        additionalKeywords.add('park');
      }
      if (_selectedCategoryList.contains('shopping')) {
        additionalKeywords.addAll(['shopping_mall', 'store']);
      }
      if (_selectedCategoryList.contains('bars')) {
        additionalKeywords.addAll(['bar', 'night_club']);
      }

      final radius = _explorationRadius.toInt() * 1000;

      // Fetch places
      final places = await _apiService.fetchNearbyPlacesUnified(
        location.latitude!,
        location.longitude!,
        radius: radius,
        additionalKeywords: additionalKeywords,
        useGoogleMapsScraping: true,
      );

      if (places.isEmpty) return null;

      // Generate itinerary
      final result = await _apiService.generateDayItinerary(
        lat: location.latitude!,
        lon: location.longitude!,
        selectedCategories: _selectedCategoryList,
        places: places,
        maxDistanceKm: 1.0,
        vegetarianFilter: _vegetarianFilter,
      );

      return {
        'itinerary': result['itinerary'],
        'neighborhood': result['neighborhood'],
        'selectedCategories': _selectedCategoryList,
        'customLocation': _useCurrentLocation
            ? null
            : {
                'lat': _selectedLat,
                'lon': _selectedLon,
                'name': _selectedLocationName,
              },
        'explorationRadius': _explorationRadius * 1000,
      };
    } catch (e) {
      print('Error in background generation: $e');
      return null;
    }
  }
}
