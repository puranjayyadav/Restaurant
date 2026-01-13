import 'dart:async';
// For min function
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:location/location.dart' as loc;
import 'package:geocoding/geocoding.dart';
import 'package:url_launcher/url_launcher.dart'; // For launching maps
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'widgets/location_autocomplete.dart' as location_autocomplete;
import "firebase_service.dart";
import "api_service.dart";
import "main.dart";
import 'utils/itinerary_helper.dart';
import 'theme/design_system.dart';
import 'screens/submit_itinerary_screen.dart';
import 'screens/itinerary_map_screen.dart';
import 'screens/place_detail_screen.dart';

class ScoutModeScreen extends StatefulWidget {
  final List<String> selectedCategories;
  final List<dynamic>? initialItinerary;
  final bool isLoadingSavedItinerary;
  final bool isEditMode;
  final String? editDocId;
  final Map<String, dynamic>? customLocation; // NEW: Custom location
  final double? explorationRadius; // NEW: Exploration radius in meters

  const ScoutModeScreen({
    super.key,
    this.selectedCategories = const [],
    this.initialItinerary,
    this.isLoadingSavedItinerary = false,
    this.isEditMode = false,
    this.editDocId,
    this.customLocation, // NEW
    this.explorationRadius, // NEW
  });

  @override
  _ScoutModeScreenState createState() => _ScoutModeScreenState();
}

class _ScoutModeScreenState extends State<ScoutModeScreen>
    with SingleTickerProviderStateMixin {
  final ApiService apiService = ApiService();
  final FirebaseService firebaseService = FirebaseService();
  List<dynamic> itinerary = []; // Changed from separate time slot lists
  loc.LocationData? currentLocation;
  loc.LocationData? previousLocation; // For heading calculation
  double? currentHeading; // User's heading in degrees (0-360, North=0)
  String? fullAddress;
  bool isLoading = true;
  double loadingProgress = 0.0; // Track loading progress (0.0 to 1.0)
  String loadingMessage = 'Initializing...'; // Current loading step message
  String? firebaseSessionId;
  String? djangoSessionId;
  Timer? periodicTimer;
  Timer? nbaTimer; // Timer for NBA endpoint calls
  String? neighborhood;
  bool hasUnsavedChanges = false; // Track if user made manual changes
  Map<String, dynamic>? nextBestAction; // Current NBA result

  late AnimationController _animationController;

  // Map state management
  List<Map<String, dynamic>> _mapPlaces = [];
  bool _showMapPreview = false;
  final MapController _itineraryMapController = MapController();
  bool _isMapReady = false;

  // Store originally fetched places for swap suggestions
  List<Map<String, dynamic>> _originalPlaces = [];

  // Scroll controller for itinerary list
  final ScrollController _itineraryScrollController = ScrollController();

  double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  double? _getLat(Map<String, dynamic> place) {
    return _toDouble(place['latitude']) ?? _toDouble(place['lat']);
  }

  double? _getLon(Map<String, dynamic> place) {
    return _toDouble(place['longitude']) ?? _toDouble(place['lng']) ?? _toDouble(place['long']);
  }

  @override
  void initState() {
    super.initState();

    // If loading a saved itinerary, load it directly
    if (widget.isLoadingSavedItinerary && widget.initialItinerary != null) {
      _loadSavedItinerary();
    } else if (widget.initialItinerary != null) {
      // If initialItinerary is provided but not a saved one, load it as a generated itinerary
      _loadGeneratedItinerary();
    } else {
      _initializeScoutMode();
    }

    periodicTimer = Timer.periodic(const Duration(minutes: 5), (timer) async {
      await _updateLocationWithoutMap();
    });
    
    // Call NBA endpoint every 60 seconds for real-time suggestions
    nbaTimer = Timer.periodic(const Duration(seconds: 60), (timer) async {
      await _updateNextBestAction();
    });
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
  }

  @override
  void dispose() {
    periodicTimer?.cancel();
    nbaTimer?.cancel();
    _animationController.dispose();
    _itineraryMapController.dispose();
    _itineraryScrollController.dispose();
    super.dispose();
  }

  Future<void> _stopScoutMode() async {
    if (hasUnsavedChanges) {
      final shouldExit = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Unsaved Changes'),
          content: const Text(
              'You have unsaved changes. Do you want to exit without saving?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Exit'),
            ),
          ],
        ),
      );
      if (shouldExit != true) return;
    }

    periodicTimer?.cancel();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => const MainScreen()),
    );
  }

  Future<void> _loadGeneratedItinerary() async {
    setState(() {
      isLoading = true;
      loadingProgress = 0.1;
      loadingMessage = 'Loading your itinerary...';
    });

    try {
      // Load the generated itinerary
      itinerary = List.from(widget.initialItinerary!);

      // Automatically add all itinerary places to map and show preview
      setState(() {
        _mapPlaces = List.from(widget.initialItinerary!);
        _showMapPreview = widget.initialItinerary!.isNotEmpty;
        loadingProgress = 0.5;
        loadingMessage = 'Getting your location...';
        hasUnsavedChanges = true; // Mark as unsaved since it's a new generation
      });

      // Get current location for location-based features
      loc.LocationData? location;
      if (widget.customLocation != null) {
        location = loc.LocationData.fromMap({
          'latitude': widget.customLocation!['lat'],
          'longitude': widget.customLocation!['lon'],
        });
        fullAddress = widget.customLocation!['name'];
      } else {
        location = await loc.Location().getLocation();
      }
      currentLocation = location;

      if (currentLocation != null && fullAddress == null) {
        setState(() {
          loadingProgress = 0.8;
          loadingMessage = 'Finalizing...';
        });
        try {
          List<Placemark> placemarks = await placemarkFromCoordinates(
            currentLocation!.latitude!,
            currentLocation!.longitude!,
          );
          if (placemarks.isNotEmpty) {
            Placemark place = placemarks[0];
            neighborhood = place.subLocality ?? place.locality;
            fullAddress =
                "${place.street ?? ''}, ${place.locality ?? ''}, ${place.administrativeArea ?? ''}";
          }
        } catch (e) {
          print("Error getting address: $e");
        }
      }

      setState(() {
        loadingProgress = 1.0;
        isLoading = false;
      });

      // Map will auto-fit when it becomes ready (via onMapReady callback)
    } catch (e) {
      print("Error loading generated itinerary: $e");
      setState(() {
        isLoading = false;
      });
    }
  }

  Future<void> _loadSavedItinerary() async {
    setState(() {
      isLoading = true;
      loadingProgress = 0.1;
      loadingMessage = 'Loading saved itinerary...';
    });

    try {
      // Load the saved itinerary
      itinerary = List.from(widget.initialItinerary!);

      // Automatically add all itinerary places to map and show preview
      setState(() {
        _mapPlaces = List.from(widget.initialItinerary!);
        _showMapPreview = widget.initialItinerary!.isNotEmpty;
        loadingProgress = 0.5;
        loadingMessage = 'Getting your location...';
      });

      // Get current location for location-based features
      currentLocation = await loc.Location().getLocation();

      if (currentLocation != null) {
        setState(() {
          loadingProgress = 0.8;
          loadingMessage = 'Finalizing...';
        });
        try {
          List<Placemark> placemarks = await placemarkFromCoordinates(
            currentLocation!.latitude!,
            currentLocation!.longitude!,
          );
          if (placemarks.isNotEmpty) {
            Placemark place = placemarks[0];
            neighborhood = place.subLocality ?? place.locality;
            fullAddress =
                "${place.street ?? ''}, ${place.locality ?? ''}, ${place.administrativeArea ?? ''}";
          }
        } catch (e) {
          print("Error getting address: $e");
        }
      }

      // Set hasUnsavedChanges to false since we just loaded
      hasUnsavedChanges = false;

      setState(() {
        loadingProgress = 1.0;
        isLoading = false;
      });

      // Map will auto-fit when it becomes ready (via onMapReady callback)
    } catch (e) {
      print("Error loading saved itinerary: $e");
      setState(() {
        isLoading = false;
      });
    }
  }

  void _removeItineraryItem(int index) {
    final removedItem = itinerary[index]; // Store for undo

    setState(() {
      itinerary.removeAt(index);
      hasUnsavedChanges = true;
    });

    // Show ShadToast with undo option
    final theme = ShadTheme.of(context);
    ShadToaster.of(context).show(
      ShadToast.destructive(
        title: const Text('Place removed'),
        description:
            Text('${removedItem['place_name']} deleted from your itinerary'),
        action: ShadButton.outline(
          child: Text(
            'Undo',
            style: TextStyle(color: theme.colorScheme.destructiveForeground),
          ),
          decoration: ShadDecoration(
            border: ShadBorder.all(
              color: theme.colorScheme.destructiveForeground,
              width: 1,
            ),
          ),
          onPressed: () {
            setState(() {
              itinerary.insert(index, removedItem);
              hasUnsavedChanges = true;
            });
            ShadToaster.of(context).hide();
          },
        ),
      ),
    );
  }

  Future<void> _showAddPlaceDialog() async {
    await showDialog(
      context: context,
      builder: (context) => _AddPlaceDialog(
        currentLocation: currentLocation,
        onPlaceSelected: (place) {
          setState(() {
            // Add to the end of itinerary
            itinerary.add({
              'slot_name': 'custom',
              'start_time': 'Custom',
              'place_name': place['name'],
              'place_id': place['place_id'],
              'address': place['formatted_address'] ?? place['vicinity'] ?? '',
              'latitude': place['geometry']?['location']?['lat'],
              'longitude': place['geometry']?['location']?['lng'],
              'types': place['types'] ?? [],
              'distance_from_previous': null,
              'estimated_walk_time': null,
              'is_custom': true,
            });
            hasUnsavedChanges = true;
          });

          ShadToaster.of(context).show(
            ShadToast(
              title: const Text('Place added'),
              description: Text('${place['name']} added to your itinerary'),
            ),
          );
        },
      ),
    );
  }

  Future<void> _showSwapPlaceDialog(
      int index, Map<String, dynamic> oldItem) async {
    final oldPlaceName = oldItem['place_name'] as String? ?? 'this place';
    final oldPlaceId = oldItem['place_id']?.toString();

    // Get places that are not already in the itinerary
    final availablePlaces = _originalPlaces.where((place) {
      final placeId = place['place_id']?.toString();
      // Exclude current place and places already in itinerary
      if (placeId == oldPlaceId) return false;
      return !itinerary.any((item) => item['place_id']?.toString() == placeId);
    }).toList();

    // Shuffle for variety
    availablePlaces.shuffle();
    // Limit to 10 suggestions
    final suggestions = availablePlaces.take(10).toList();

    if (suggestions.isEmpty) {
      // Fallback to search dialog if no suggestions available
      await showDialog(
        context: context,
        builder: (context) => _AddPlaceDialog(
          currentLocation: currentLocation,
          title: 'Swap Place',
          infoText:
              'No suggestions available. Search for a replacement for $oldPlaceName',
          icon: Icons.swap_horiz,
          onPlaceSelected: (place) => _performSwap(index, oldItem, place),
        ),
      );
      return;
    }

    await showDialog(
      context: context,
      builder: (context) => _SwapPlaceSuggestionsDialog(
        oldPlaceName: oldPlaceName,
        suggestions: suggestions,
        onPlaceSelected: (place) => _performSwap(index, oldItem, place),
      ),
    );
  }

  void _performSwap(
      int index, Map<String, dynamic> oldItem, Map<String, dynamic> place) {
    final oldPlaceName = oldItem['place_name'] as String? ?? 'Unknown';
    final newPlaceName =
        place['name'] as String? ?? place['description'] ?? 'Unknown';

    // Check if old place was in map
    final wasInMap = _isPlaceInMap(oldItem);
    final oldPlaceId = oldItem['place_id']?.toString();

    setState(() {
      // Replace the item at the given index, preserving slot info
      final slotName = oldItem['slot_name'] as String? ?? 'custom';
      final startTime = oldItem['start_time'] as String? ?? 'Custom';

      // Convert place format to itinerary format
      final geometry = place['geometry'] as Map<String, dynamic>?;
      final location = geometry?['location'] as Map<String, dynamic>?;

      final newItem = {
        'slot_name': slotName,
        'start_time': startTime,
        'place_name': place['name'] ?? place['description'] ?? 'Unknown',
        'place_id': place['place_id'],
        'address': place['formatted_address'] ??
            place['vicinity'] ??
            place['structured_formatting']?['secondary_text'] ??
            '',
        'latitude': location?['lat'] ?? place['latitude'],
        'longitude': location?['lng'] ?? place['longitude'],
        'types': place['types'] ?? [],
        'distance_from_previous': oldItem['distance_from_previous'],
        'estimated_walk_time': oldItem['estimated_walk_time'],
        'is_custom': true,
      };

      itinerary[index] = newItem;
      hasUnsavedChanges = true;

      // Update map if old place was in map
      if (wasInMap && oldPlaceId != null) {
        // Find the index of old place in map to maintain order
        final oldMapIndex = _mapPlaces
            .indexWhere((p) => p['place_id']?.toString() == oldPlaceId);

        if (oldMapIndex != -1) {
          // Replace at the same position to maintain order
          _mapPlaces[oldMapIndex] = newItem;
        } else {
          // If not found (shouldn't happen), just add it
          _mapPlaces.add(newItem);
        }
      }
    });

    // Fit map to show all places after swap (if map is ready)
    if (wasInMap && _isMapReady) {
      Future.delayed(const Duration(milliseconds: 300), () {
        _fitMapToPlaces();
      });
    }

    ShadToaster.of(context).show(
      ShadToast(
        title: const Text('Place swapped'),
        description: Text('$oldPlaceName replaced with $newPlaceName'),
      ),
    );
  }

  Future<void> _saveItinerary() async {
    if (itinerary.isEmpty) {
      if (!mounted) return;
      ShadToaster.of(context).show(
        const ShadToast.destructive(
          title: Text('Nothing to save'),
          description: Text('Generate an itinerary first'),
        ),
      );
      return;
    }

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        if (!mounted) return;
        ShadToaster.of(context).show(
          const ShadToast.destructive(
            title: Text('Authentication required'),
            description: Text('Please sign in to save itineraries'),
          ),
        );
        return;
      }

      print('DEBUG: Saving itinerary for user ${user.uid}');
      print('DEBUG: Itinerary items: ${itinerary.length}');

      // Convert itinerary to serializable format
      final itineraryData = itinerary.map((item) {
        return {
          'slot_name': item['slot_name']?.toString() ?? '',
          'start_time': item['start_time']?.toString() ?? '',
          'place_name': item['place_name']?.toString() ?? '',
          'place_id': item['place_id']?.toString() ?? '',
          'address': item['address']?.toString() ?? '',
          'latitude': item['latitude'],
          'longitude': item['longitude'],
          'types': item['types'] ?? [],
          'distance_from_previous': item['distance_from_previous'],
          'estimated_walk_time': item['estimated_walk_time'],
          'is_custom': item['is_custom'] ?? false,
        };
      }).toList();

      // Save to Firestore (update if editing, create new if not)
      if (widget.isEditMode && widget.editDocId != null) {
        // Update existing document
        await FirebaseFirestore.instance
            .collection('saved_itineraries')
            .doc(widget.editDocId)
            .update({
          'items': itineraryData,
          'categories': widget.selectedCategories,
          'updated_at': FieldValue.serverTimestamp(),
        });
        print('DEBUG: Itinerary updated with ID: ${widget.editDocId}');
      } else {
        // Create new document
        final docRef = await FirebaseFirestore.instance
            .collection('saved_itineraries')
            .add({
          'user_id': user.uid,
          'created_at': FieldValue.serverTimestamp(),
          'location': fullAddress ?? 'Unknown location',
          'neighborhood': neighborhood ?? 'Local area',
          'items': itineraryData,
          'categories': widget.selectedCategories,
        });
        print('DEBUG: Itinerary saved with ID: ${docRef.id}');
      }

      if (!mounted) return;

      setState(() {
        hasUnsavedChanges = false;
      });

      ShadToaster.of(context).show(
        const ShadToast(
          title: Text('Success!'),
          description: Text('Your itinerary has been saved'),
        ),
      );
    } catch (e) {
      print('ERROR saving itinerary: $e');
      if (!mounted) return;

      ShadToaster.of(context).show(
        ShadToast.destructive(
          title: const Text('Save failed'),
          description: Text('Unable to save itinerary: ${e.toString()}'),
        ),
      );
    }
  }

  Future<void> _submitToPublic() async {
    if (itinerary.isEmpty) {
      if (!mounted) return;
      ShadToaster.of(context).show(
        const ShadToast.destructive(
          title: Text('Nothing to submit'),
          description: Text('Generate an itinerary first'),
        ),
      );
      return;
    }

    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      ShadToaster.of(context).show(
        const ShadToast.destructive(
          title: Text('Authentication required'),
          description: Text('Please sign in to submit itineraries'),
        ),
      );
      return;
    }

    // Navigate to submit screen
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => SubmitItineraryScreen(
          itinerary: itinerary,
          location: fullAddress ?? 'Unknown location',
          neighborhood: neighborhood ?? 'Local area',
          latitude: currentLocation?.latitude ?? 0.0,
          longitude: currentLocation?.longitude ?? 0.0,
          categories: widget.selectedCategories,
        ),
      ),
    );

    if (result == true && mounted) {
      // Itinerary was successfully submitted
      ShadToaster.of(context).show(
        const ShadToast(
          title: Text('Success!'),
          description: Text('Your itinerary has been submitted for approval'),
        ),
      );
    }
  }

  Future<void> _initializeScoutMode() async {
    setState(() {
      loadingProgress = 0.1;
      loadingMessage = 'Setting up your session...';
    });

    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    try {
      firebaseSessionId = await firebaseService.createSession(
          userId: user.uid, startAddress: fullAddress ?? "Unknown Start");
    } catch (e) {
      print("Error creating Firebase session: $e");
    }

    try {
      djangoSessionId = await ApiService().createSessionDjango(user.uid);
    } catch (e) {
      print("Error creating session in Django: $e");
    }

    setState(() {
      loadingProgress = 0.2;
      loadingMessage = 'Getting your location...';
    });

    // NEW: Use custom location if provided, otherwise get current location
    if (widget.customLocation != null) {
      currentLocation = loc.LocationData.fromMap({
        'latitude': widget.customLocation!['lat'],
        'longitude': widget.customLocation!['lon'],
      });
      fullAddress = widget.customLocation!['name'];
      setState(() {
        loadingProgress = 0.3;
        loadingMessage = 'Using ${widget.customLocation!['name']}...';
      });
    } else {
      // Get current location.
      currentLocation = await loc.Location().getLocation();
      if (currentLocation == null) {
        setState(() {
          isLoading = false;
        });
        return;
      }

      setState(() {
        loadingProgress = 0.3;
        loadingMessage = 'Finding your address...';
      });

      // Fetch placemark for full address.
      try {
        List<Placemark> placemarks = await placemarkFromCoordinates(
          currentLocation!.latitude!,
          currentLocation!.longitude!,
        );
        if (placemarks.isNotEmpty) {
          final place = placemarks.first;
          fullAddress =
              "${place.street}, ${place.locality}, ${place.administrativeArea}, ${place.country}";
        } else {
          fullAddress = "Address not available";
        }
      } catch (e) {
        fullAddress = "Address not available";
      }
    }

    setState(() {
      loadingProgress = 0.4;
      loadingMessage = 'Discovering nearby places...';
    });
    // Fetch nearby places with larger radius for itinerary generation
    try {
      print(
          "DEBUG: Current location: ${currentLocation!.latitude}, ${currentLocation!.longitude}");
      print("DEBUG: Selected categories: ${widget.selectedCategories}");

      // Determine additional keywords based on selected categories
      final List<String> additionalKeywords = [];
      if (widget.selectedCategories.contains('museums')) {
        additionalKeywords.addAll(['museum', 'art_gallery']);
      }
      if (widget.selectedCategories.contains('parks')) {
        additionalKeywords.add('park');
      }
      if (widget.selectedCategories.contains('shopping')) {
        additionalKeywords.addAll(['shopping_mall', 'store']);
      }
      if (widget.selectedCategories.contains('bars')) {
        additionalKeywords.addAll(['bar', 'night_club']);
      }

      // NEW: Use custom radius if provided, otherwise default to 2km
      final radius = widget.explorationRadius?.toInt() ?? 2000;

      // Using Google Maps scraping (tries scraping first, falls back to OSM if needed)
      final places = await apiService.fetchNearbyPlacesUnified(
        currentLocation!.latitude!,
        currentLocation!.longitude!,
        radius: radius, // Use custom or default radius
        additionalKeywords: additionalKeywords,
        useGoogleMapsScraping: true, // Use Google Maps scraping
      );
      print("DEBUG: Fetched ${places.length} places from API");

      // Store original places for swap suggestions
      setState(() {
        _originalPlaces = List.from(places);
      });

      setState(() {
        loadingProgress = 0.6;
        loadingMessage = 'Found ${places.length} amazing places!';
      });

      if (places.isEmpty) {
        print("WARNING: No places found. This could be due to:");
        print("  1. Invalid Google API key");
        print("  2. Location not having any establishments nearby");
        print("  3. API quota exceeded");

        // Show error message to user
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                  'No places found nearby. Please try a different location or check your internet connection.'),
              duration: Duration(seconds: 5),
            ),
          );
        }
        setState(() {
          isLoading = false;
        });
        return;
      }

      setState(() {
        loadingProgress = 0.7;
        loadingMessage = 'Creating your perfect day plan...';
      });

      // Generate day itinerary
      await _generateDayItinerary(places);

      setState(() {
        loadingProgress = 0.9;
        loadingMessage = 'Saving your preferences...';
      });

      final updatedPlaces = places.map((place) {
        place['uid'] = user.uid;
        return place;
      }).toList();
      if (firebaseSessionId != null) {
        await firebaseService.saveEstablishments(
            firebaseSessionId!, updatedPlaces);
      }

      setState(() {
        loadingProgress = 1.0;
        loadingMessage = 'All set! Enjoy your day!';
      });
    } catch (e) {
      print("Error fetching nearby places or generating itinerary: $e");
    }
    setState(() {
      isLoading = false;
    });
  }

  Future<void> _generateDayItinerary(List<dynamic> places) async {
    try {
      // Store original places for swap suggestions (before shuffling)
      setState(() {
        _originalPlaces = List.from(places);
      });

      // Shuffle places before sending to backend for more variety
      places.shuffle();

      // Debug: Check place structure
      if (places.isNotEmpty) {
        final firstPlace = places[0];
        print("DEBUG: Sample place structure:");
        print("  - place_id: ${firstPlace['place_id']}");
        print("  - name: ${firstPlace['name']}");
        print("  - geometry: ${firstPlace['geometry']}");
        print("  - types: ${firstPlace['types']}");
        print("  - formatted_address: ${firstPlace['formatted_address']}");
      }

      print(
          "DEBUG: Sending ${places.length} places to backend for itinerary generation");

      final result = await apiService.generateDayItinerary(
        lat: currentLocation!.latitude!,
        lon: currentLocation!.longitude!,
        selectedCategories: widget.selectedCategories,
        places: places,
        maxDistanceKm: 1.0, // 1 km max distance between places
        vegetarianFilter: false, // Default to false for existing flows
      );

      setState(() {
        itinerary = result['itinerary'] as List<dynamic>? ?? [];
        neighborhood = result['neighborhood'] as String?;
        // Mark as unsaved since this is a newly generated itinerary
        hasUnsavedChanges = true;

        // Automatically add all itinerary places to map and show preview
        _mapPlaces = List.from(itinerary);
        _showMapPreview = itinerary.isNotEmpty;
      });

      print("DEBUG: Generated itinerary with ${itinerary.length} items");

      // Fit map to show all places after map is ready
      // The onMapReady callback will handle this automatically

      // Itinerary generated successfully (no notification shown)

      if (itinerary.isEmpty && mounted) {
        ShadToaster.of(context).show(
          const ShadToast.destructive(
            title: Text('Could not create itinerary'),
            description: Text(
              'Not enough places found to create a full day plan. Try increasing the radius or selecting a more urban area.',
            ),
          ),
        );
      }
    } catch (e) {
      print("Error generating itinerary: $e");
      setState(() {
        itinerary = [];
      });

      if (mounted) {
        ShadToaster.of(context).show(
          ShadToast.destructive(
            title: const Text('Generation failed'),
            description: Text('Error: ${e.toString()}'),
          ),
        );
      }
    }
  }

  /// Calculate heading from previous location to current location.
  void _updateHeading(loc.LocationData newLocation) {
    if (previousLocation != null &&
        previousLocation!.latitude != null &&
        previousLocation!.longitude != null &&
        newLocation.latitude != null &&
        newLocation.longitude != null) {
      // Calculate bearing between previous and current location
      currentHeading = ApiService.calculateBearing(
        previousLocation!.latitude!,
        previousLocation!.longitude!,
        newLocation.latitude!,
        newLocation.longitude!,
      );
      print('DEBUG: Calculated heading: $currentHeading degrees');
    }
    previousLocation = newLocation;
  }

  /// Update Next Best Action recommendation.
  Future<void> _updateNextBestAction() async {
    if (currentLocation == null ||
        currentLocation!.latitude == null ||
        currentLocation!.longitude == null) {
      return;
    }

    try {
      final result = await apiService.getNextBestAction(
        latitude: currentLocation!.latitude!,
        longitude: currentLocation!.longitude!,
        heading: currentHeading,
        timestamp: DateTime.now(),
      );

      if (result != null && mounted) {
        setState(() {
          nextBestAction = result;
        });
        print('DEBUG: NBA updated: ${result['context']}, next_stop: ${result['next_stop']?['name']}');
      }
    } catch (e) {
      print('ERROR: Failed to update NBA: $e');
    }
  }

  Future<void> _updateLocationWithoutMap() async {
    final newLocation = await loc.Location().getLocation();
    
    // Update heading before updating current location
    _updateHeading(newLocation);
    
    setState(() {
      currentLocation = newLocation;
      isLoading = true;
    });
    try {
      List<Placemark> placemarks = await placemarkFromCoordinates(
        newLocation.latitude!,
        newLocation.longitude!,
      );
      if (placemarks.isNotEmpty) {
        final place = placemarks.first;
        fullAddress =
            "${place.street}, ${place.locality}, ${place.administrativeArea}, ${place.country}";
      } else {
        fullAddress = "Address not available";
      }
    } catch (e) {
      fullAddress = "Address not available";
    }
    try {
      // Determine additional keywords based on selected categories
      final List<String> additionalKeywords = [];
      if (widget.selectedCategories.contains('museums')) {
        additionalKeywords.addAll(['museum', 'art_gallery']);
      }
      if (widget.selectedCategories.contains('parks')) {
        additionalKeywords.add('park');
      }
      if (widget.selectedCategories.contains('shopping')) {
        additionalKeywords.addAll(['shopping_mall', 'store']);
      }
      if (widget.selectedCategories.contains('bars')) {
        additionalKeywords.addAll(['bar', 'night_club']);
      }

      final places = await apiService.fetchNearbyPlacesUnified(
        newLocation.latitude!,
        newLocation.longitude!,
        radius: 2000, // 2km radius
        additionalKeywords: additionalKeywords,
        useGoogleMapsScraping: true, // Use Google Maps scraping
      );
      // Regenerate itinerary with new location
      await _generateDayItinerary(places);
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        final updatedPlaces = places.map((place) {
          place['uid'] = user.uid;
          return place;
        }).toList();
        if (firebaseSessionId != null) {
          await firebaseService.saveEstablishments(
              firebaseSessionId!, updatedPlaces);
        }
      }
    } catch (e) {
      print("Error fetching nearby places or regenerating itinerary: $e");
    }
    setState(() {
      isLoading = false;
    });
  }

  // Open maps with place name and address (using OpenStreetMap)
  Future<void> _openMaps(String name, String address) async {
    final query = Uri.encodeComponent('$name, $address');
    // Use OpenStreetMap or generic geo link
    final url = 'https://www.openstreetmap.org/search?query=$query';

    try {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      print('Error opening maps: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open maps for $name')),
      );
    }
  }

  Widget _buildItineraryItem(
      BuildContext context, Map<String, dynamic> item, int index) {
    final slotName = item['slot_name'] as String;
    final startTime = item['start_time'] as String;
    final placeName = item['place_name'] as String;
    final address = item['address'] as String;
    final distanceKm = item['distance_from_previous'] as double?;
    final walkTime = item['estimated_walk_time'] as int?;
    final latitude = item['latitude'] as double?;
    final longitude = item['longitude'] as double?;
    final types = (item['types'] as List<dynamic>? ?? [])
        .map((t) => t.toString())
        .toList();

    // Slot display names and icons (minimal emoji-free)
    final Map<String, Map<String, dynamic>> slotInfo = {
      'morning': {'name': 'Morning', 'icon': Icons.wb_sunny_outlined},
      'mid_day': {'name': 'Midday', 'icon': Icons.restaurant_outlined},
      'afternoon': {'name': 'Afternoon', 'icon': Icons.museum_outlined},
      'evening': {'name': 'Evening', 'icon': Icons.nightlife_outlined},
    };

    final slotDisplay =
        slotInfo[slotName] ?? {'name': slotName, 'icon': Icons.place_outlined};

    return Padding(
      padding: EdgeInsets.only(
        bottom: AppSpacing.md,
        left: AppSpacing.md,
        right: AppSpacing.md,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline indicator
          Column(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.primary, width: 2),
                ),
                child: Icon(
                  slotDisplay['icon'] as IconData,
                  color: AppColors.primary,
                  size: 22,
                ),
              ),
              if (index < itinerary.length - 1)
                Container(
                  width: 2,
                  height: 60,
                  margin: EdgeInsets.symmetric(vertical: AppSpacing.xs),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        AppColors.primary.withOpacity(0.3),
                        AppColors.border,
                      ],
                    ),
                  ),
                ),
            ],
          ),
          SizedBox(width: AppSpacing.md),
          // Content card
          Expanded(
            child: InkWell(
              onTap: () {
                // Find the full place data from original places or use item data
                final placeId = item['place_id']?.toString();
                Map<String, dynamic>? fullPlaceData;

                // Try to find in original places first
                if (placeId != null && _originalPlaces.isNotEmpty) {
                  try {
                    final foundPlace = _originalPlaces.firstWhere(
                      (p) => p['place_id']?.toString() == placeId,
                    );
                    // Create a deep copy
                    fullPlaceData = Map<String, dynamic>.from(foundPlace);
                  } catch (e) {
                    print('DEBUG: Place not found in originalPlaces: $e');
                    fullPlaceData = null;
                  }
                }

                // If not found, construct from item data
                if (fullPlaceData == null) {
                  fullPlaceData = {
                    'name': item['place_name'],
                    'place_id': item['place_id'],
                    'street_address': '',
                    'city': '',
                    'zip': '',
                    'state': '',
                    'country_code': '',
                    'full_address': item['address'],
                    'formatted_address': item['address'],
                    'vicinity': item['address'],
                    'website': null,
                    'avg_rating': null,
                    'rating': null,
                    'total_reviews': null,
                    'user_ratings_total': null,
                    'tags': item['types'] ?? [],
                    'types': item['types'] ?? [],
                    'phone': null,
                    'formatted_phone_number': null,
                    'hours': null,
                    'opening_hours': null,
                    'price_level': null,
                    'photos': item['photos'] ?? [],
                    'lat': item['latitude'],
                    'long': item['longitude'],
                    'geometry': {
                      'location': {
                        'lat': item['latitude'],
                        'lng': item['longitude'],
                      },
                    },
                  };
                }

                // Debug: Print photo info

                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) =>
                        PlaceDetailScreen(place: fullPlaceData!),
                  ),
                );
              },
              child: ShadCard(
                backgroundColor: AppColors.surfaceElevated,
                padding: EdgeInsets.zero,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: EdgeInsets.all(AppSpacing.md),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Time and slot header
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              Container(
                                padding: EdgeInsets.symmetric(
                                  horizontal: AppSpacing.sm,
                                  vertical: AppSpacing.xs,
                                ),
                                decoration: BoxDecoration(
                                  color: AppColors.primary.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(
                                      AppBorderRadius.small),
                                ),
                                child: Text(
                                  slotDisplay['name'] as String,
                                  style: TextStyle(
                                    fontSize: AppTypography.labelMedium,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.primary,
                                    letterSpacing: 0.5,
                                  ),
                                ),
                              ),
                              Text(
                                startTime,
                                style: TextStyle(
                                  fontSize: AppTypography.titleSmall,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ],
                          ),
                          SizedBox(height: AppSpacing.sm),
                          // Place name
                          Text(
                            placeName,
                            style: TextStyle(
                              fontSize: AppTypography.titleLarge,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                              height: 1.3,
                            ),
                          ),
                          SizedBox(height: AppSpacing.xs),
                          // Establishment type badges
                          if (types.isNotEmpty)
                            Wrap(
                              spacing: AppSpacing.xs,
                              runSpacing: AppSpacing.xs,
                              children: types
                                  .where((type) => ![
                                        'point_of_interest',
                                        'establishment',
                                        'food'
                                      ].contains(type.toLowerCase()))
                                  .take(2)
                                  .map((type) {
                                final formattedType =
                                    _formatEstablishmentType(type);
                                final icon = _getTypeIcon(type);

                                return Container(
                                  padding: EdgeInsets.symmetric(
                                    horizontal: AppSpacing.sm,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: AppColors.accent.withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(
                                        AppBorderRadius.small),
                                    border: Border.all(
                                      color: AppColors.accent.withOpacity(0.3),
                                      width: 1,
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(icon,
                                          size: 12, color: AppColors.accent),
                                      SizedBox(width: 4),
                                      Text(
                                        formattedType,
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w600,
                                          color: AppColors.accent,
                                          letterSpacing: 0.3,
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }).toList(),
                            ),
                          SizedBox(height: AppSpacing.sm),
                          // Address
                          Row(
                            children: [
                              Icon(
                                Icons.location_on_outlined,
                                size: 14,
                                color: AppColors.textSecondary,
                              ),
                              SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  address,
                                  style: TextStyle(
                                    fontSize: AppTypography.bodySmall,
                                    color: AppColors.textSecondary,
                                    height: 1.4,
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          // Distance and walk time (if not first item)
                          if (distanceKm != null && distanceKm > 0) ...[
                            SizedBox(height: AppSpacing.sm),
                            Container(
                              padding: EdgeInsets.symmetric(
                                horizontal: AppSpacing.sm,
                                vertical: AppSpacing.xs,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.surface,
                                borderRadius: BorderRadius.circular(
                                    AppBorderRadius.small),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.directions_walk_outlined,
                                    size: 14,
                                    color: AppColors.primary,
                                  ),
                                  SizedBox(width: 4),
                                  Text(
                                    '${formatDistance(distanceKm)} • ${formatWalkTime(walkTime ?? 0)}',
                                    style: TextStyle(
                                      fontSize: AppTypography.bodySmall,
                                      fontWeight: FontWeight.w500,
                                      color: AppColors.textPrimary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          // Curated Reason / Highlight
                          if (item['curated_reason'] != null && 
                              (item['curated_reason'] as String).isNotEmpty) ...[
                            SizedBox(height: AppSpacing.md),
                            Container(
                              padding: EdgeInsets.all(AppSpacing.md),
                              decoration: BoxDecoration(
                                color: AppColors.surface,
                                borderRadius: BorderRadius.circular(AppBorderRadius.small),
                                border: Border.all(
                                  color: AppColors.accent.withOpacity(0.1),
                                  width: 1,
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Icon(Icons.auto_awesome, 
                                          size: 14, color: AppColors.accent),
                                      SizedBox(width: AppSpacing.xs),
                                      Text(
                                        'WHY THIS SPOT',
                                        style: TextStyle(
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                          color: AppColors.accent,
                                          letterSpacing: 1.0,
                                        ),
                                      ),
                                    ],
                                  ),
                                  SizedBox(height: AppSpacing.xs),
                                  Text(
                                    item['curated_reason'],
                                    style: TextStyle(
                                      fontSize: AppTypography.bodySmall,
                                      color: AppColors.textPrimary,
                                      height: 1.4,
                                      fontStyle: FontStyle.italic,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          SizedBox(height: AppSpacing.md),
                          // Action buttons
                          Row(
                            children: [
                              Expanded(
                                child: ShadButton(
                                  size: ShadButtonSize.sm,
                                  backgroundColor: AppColors.primary,
                                  onPressed:
                                      latitude != null && longitude != null
                                          ? () => _openMaps(placeName, address)
                                          : null,
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.map_outlined,
                                          size: 16, color: Colors.white),
                                      SizedBox(width: AppSpacing.xs),
                                      const Text(
                                        'Directions',
                                        style: TextStyle(
                                            color: Colors.white, fontSize: 13),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              SizedBox(width: AppSpacing.xs),
                              ShadButton(
                                size: ShadButtonSize.sm,
                                backgroundColor: _isPlaceInMap(item)
                                    ? AppColors.success.withOpacity(0.2)
                                    : AppColors.accent.withOpacity(0.15),
                                onPressed: latitude != null && longitude != null
                                    ? () => _addPlaceToMap(item)
                                    : null,
                                child: Icon(
                                    _isPlaceInMap(item)
                                        ? Icons.check_circle
                                        : Icons.add_location_alt_outlined,
                                    size: 18,
                                    color: _isPlaceInMap(item)
                                        ? AppColors.success
                                        : AppColors.accent),
                              ),
                              SizedBox(width: AppSpacing.xs),
                              ShadButton(
                                size: ShadButtonSize.sm,
                                backgroundColor:
                                    AppColors.accent.withOpacity(0.15),
                                onPressed: () =>
                                    _showSwapPlaceDialog(index, item),
                                child: Icon(Icons.swap_horiz,
                                    size: 18, color: AppColors.accent),
                              ),
                              SizedBox(width: AppSpacing.xs),
                              ShadButton(
                                size: ShadButtonSize.sm,
                                backgroundColor:
                                    AppColors.error.withOpacity(0.1),
                                onPressed: () => _removeItineraryItem(index),
                                child: Icon(Icons.delete_outline,
                                    size: 18, color: AppColors.error),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Helper to format establishment type
  String _formatEstablishmentType(String type) {
    return type
        .split('_')
        .map((word) =>
            word.isEmpty ? '' : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  // Helper to get icon for establishment type
  IconData _getTypeIcon(String type) {
    final typeLower = type.toLowerCase();
    if (typeLower.contains('restaurant')) return Icons.restaurant;
    if (typeLower.contains('cafe') || typeLower.contains('coffee'))
      return Icons.local_cafe;
    if (typeLower.contains('bar') || typeLower.contains('night_club'))
      return Icons.local_bar;
    if (typeLower.contains('bakery')) return Icons.bakery_dining;
    if (typeLower.contains('museum')) return Icons.museum;
    if (typeLower.contains('park')) return Icons.park;
    if (typeLower.contains('shopping') || typeLower.contains('store'))
      return Icons.shopping_bag;
    if (typeLower.contains('library')) return Icons.local_library;
    if (typeLower.contains('art')) return Icons.palette;
    return Icons.place;
  }

  // Check if place is already in map
  bool _isPlaceInMap(Map<String, dynamic> item) {
    final placeId = item['place_id']?.toString();
    if (placeId == null) return false;
    return _mapPlaces.any((place) => place['place_id']?.toString() == placeId);
  }

  // Add place to map
  void _addPlaceToMap(Map<String, dynamic> item) {
    if (_isPlaceInMap(item)) {
      // Remove if already added
      final placeId = item['place_id']?.toString();
      setState(() {
        _mapPlaces
            .removeWhere((place) => place['place_id']?.toString() == placeId);
        if (_mapPlaces.isEmpty) {
          _showMapPreview = false;
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${item['place_name']} removed from map'),
          duration: const Duration(seconds: 1),
        ),
      );
    } else {
      // Add to map
      setState(() {
        _mapPlaces.add(item);
        _showMapPreview = true;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${item['place_name']} added to map'),
          duration: const Duration(seconds: 1),
        ),
      );
      // Fit camera to show all markers after map is ready
      // Will be handled by onMapReady callback or retry mechanism
    }
  }

  // Fit map camera to show all places
  void _fitMapToPlaces() {
    if (_mapPlaces.isEmpty) return;

    // Only proceed if map is ready
    if (!_isMapReady) {
      // Schedule to try again after a delay
      Future.delayed(const Duration(milliseconds: 300), () {
        if (_isMapReady && mounted) {
          _fitMapToPlaces();
        }
      });
      return;
    }

    final validPlaces = _mapPlaces.where((place) {
      final lat = _getLat(place);
      final lon = _getLon(place);
      return lat != null && lon != null;
    }).toList();

    if (validPlaces.isEmpty) return;

    try {
      if (validPlaces.length == 1) {
        // Single place - just center on it
        final lat = _getLat(validPlaces[0])!;
        final lon = _getLon(validPlaces[0])!;
        _itineraryMapController.move(LatLng(lat, lon), 15.0);
      } else {
        // Multiple places - calculate bounds and fit camera
        double minLat = double.infinity;
        double maxLat = -double.infinity;
        double minLon = double.infinity;
        double maxLon = -double.infinity;

        for (var place in validPlaces) {
          final lat = _getLat(place)!;
          final lon = _getLon(place)!;
          if (lat < minLat) minLat = lat;
          if (lat > maxLat) maxLat = lat;
          if (lon < minLon) minLon = lon;
          if (lon > maxLon) maxLon = lon;
        }

        final bounds = LatLngBounds(
          LatLng(minLat, minLon),
          LatLng(maxLat, maxLon),
        );

        _itineraryMapController.fitCamera(
          CameraFit.bounds(
            bounds: bounds,
            padding: const EdgeInsets.all(50),
          ),
        );
      }
    } catch (e) {
      print('Error fitting map camera: $e');
      // Map might not be ready yet, will retry on next call
    }
  }

  // Open full-screen map
  void _openFullScreenMap() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ItineraryMapScreen(places: _mapPlaces),
      ),
    );
  }

  // Build map preview widget
  Widget _buildMapPreview() {
    if (!_showMapPreview || _mapPlaces.isEmpty) {
      return const SizedBox.shrink();
    }

    final validPlaces = _mapPlaces.where((place) {
      final lat = _getLat(place);
      final lon = _getLon(place);
      return lat != null && lon != null;
    }).toList();

    if (validPlaces.isEmpty) {
      return const SizedBox.shrink();
    }

    // Get polyline points
    final polylinePoints = <LatLng>[];
    for (var place in validPlaces) {
      final lat = _getLat(place)!;
      final lon = _getLon(place)!;
      polylinePoints.add(LatLng(lat, lon));
    }

    // Build markers
    final markers = <Marker>[];
    for (int i = 0; i < validPlaces.length; i++) {
      final place = validPlaces[i];
      final lat = _getLat(place)!;
      final lon = _getLon(place)!;

      final isStart = i == 0;
      final isEnd = i == validPlaces.length - 1;

      markers.add(
        Marker(
          point: LatLng(lat, lon),
          width: isStart || isEnd ? 50 : 35,
          height: isStart || isEnd ? 50 : 35,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: isStart || isEnd ? 40 : 30,
                height: isStart || isEnd ? 40 : 30,
                decoration: BoxDecoration(
                  color: isStart
                      ? AppColors.success
                      : isEnd
                          ? AppColors.error
                          : AppColors.primary,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white,
                    width: 2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.2),
                      blurRadius: 4,
                      offset: const Offset(0, 1),
                    ),
                  ],
                ),
                child: Icon(
                  isStart
                      ? Icons.play_arrow
                      : isEnd
                          ? Icons.flag
                          : Icons.location_on,
                  color: Colors.white,
                  size: isStart || isEnd ? 22 : 18,
                ),
              ),
              if (isStart || isEnd)
                Positioned(
                  bottom: -3,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 1,
                    ),
                    decoration: BoxDecoration(
                      color: isStart ? AppColors.success : AppColors.error,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.white, width: 1),
                    ),
                    child: Text(
                      isStart ? 'S' : 'E',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 8,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
    }

    // Default center
    final defaultCenter = validPlaces.isNotEmpty
        ? LatLng(
            _getLat(validPlaces[0])!,
            _getLon(validPlaces[0])!,
          )
        : const LatLng(40.7128, -74.0060);

    return Container(
      margin: EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: ShadCard(
        backgroundColor: AppColors.surfaceElevated,
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with toggle and expand button
            Container(
              padding: EdgeInsets.all(AppSpacing.md),
              child: Row(
                children: [
                  Icon(
                    Icons.map_outlined,
                    color: AppColors.primary,
                    size: 20,
                  ),
                  SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      'Map View (${validPlaces.length} places)',
                      style: TextStyle(
                        fontSize: AppTypography.titleSmall,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: Icon(
                      Icons.close,
                      size: 18,
                      color: AppColors.textSecondary,
                    ),
                    onPressed: () {
                      setState(() {
                        _showMapPreview = false;
                      });
                    },
                    tooltip: 'Hide map',
                  ),
                  SizedBox(width: AppSpacing.xs),
                  IconButton(
                    icon: Icon(
                      Icons.fullscreen,
                      size: 18,
                      color: AppColors.primary,
                    ),
                    onPressed: _openFullScreenMap,
                    tooltip: 'Full screen',
                  ),
                ],
              ),
            ),
            // Map
            SizedBox(
              height: 220,
              child: FlutterMap(
                mapController: _itineraryMapController,
                options: MapOptions(
                  initialCenter: defaultCenter,
                  initialZoom: 13.0,
                  minZoom: 5.0,
                  maxZoom: 18.0,
                  onMapReady: () {
                    setState(() {
                      _isMapReady = true;
                    });
                    // Fit camera after map is ready
                    Future.delayed(const Duration(milliseconds: 100), () {
                      _fitMapToPlaces();
                    });
                  },
                ),
                children: [
                  TileLayer(
                    urlTemplate:
                        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.example.restaurant_tracker',
                    maxZoom: 19,
                  ),
                  if (polylinePoints.length > 1)
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: polylinePoints,
                          strokeWidth: 3.0,
                          color: AppColors.primary,
                        ),
                      ],
                    ),
                  MarkerLayer(markers: markers),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "Your Day Plan",
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: AppTypography.titleLarge,
            fontWeight: FontWeight.w600,
          ),
        ),
        actions: [
          if (itinerary.isNotEmpty) ...[
            IconButton(
              icon: const Icon(Icons.public),
              onPressed: _submitToPublic,
              tooltip: 'Submit to Public Feed',
            ),
            IconButton(
              icon: Icon(
                hasUnsavedChanges ? Icons.bookmark_outline : Icons.bookmark,
                color: hasUnsavedChanges
                    ? AppColors.textSecondary
                    : AppColors.primary,
              ),
              onPressed: hasUnsavedChanges ? _saveItinerary : null,
              tooltip: hasUnsavedChanges ? 'Save Itinerary' : 'Saved',
            ),
          ],
          IconButton(
            icon: Icon(Icons.close, color: AppColors.textPrimary),
            onPressed: _stopScoutMode,
            tooltip: 'Exit',
          ),
        ],
      ),
      floatingActionButton: itinerary.isNotEmpty
          ? Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (hasUnsavedChanges)
                  FloatingActionButton.extended(
                    onPressed: _saveItinerary,
                    backgroundColor: AppColors.success,
                    icon: const Icon(Icons.save, color: Colors.white),
                    label: const Text(
                      'Save Changes',
                      style: TextStyle(color: Colors.white),
                    ),
                    heroTag: 'save',
                  ),
                if (hasUnsavedChanges) SizedBox(height: AppSpacing.sm),
                FloatingActionButton(
                  onPressed: _showAddPlaceDialog,
                  backgroundColor: AppColors.primary,
                  child: const Icon(Icons.add, color: Colors.white),
                  heroTag: 'add',
                ),
              ],
            )
          : null,
      body: isLoading
          ? Center(
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.xl),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Animated loading spinner with pulse effect
                    CircularProgressIndicator(
                      valueColor:
                          AlwaysStoppedAnimation<Color>(AppColors.primary),
                    )
                        .animate(onPlay: (controller) => controller.repeat())
                        .scaleXY(begin: 0.8, end: 1.2, duration: 600.ms)
                        .then()
                        .scaleXY(begin: 1.2, end: 0.8, duration: 600.ms),

                    SizedBox(height: AppSpacing.xl),

                    // Animated title with fade and slide
                    Text(
                      'Creating your perfect day...',
                      style: TextStyle(
                        fontSize: AppTypography.titleMedium,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    )
                        .animate()
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: -0.2, end: 0, curve: Curves.easeOut),

                    SizedBox(height: AppSpacing.sm),

                    // Animated loading message with shimmer
                    Text(
                      loadingMessage,
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: AppTypography.bodyMedium,
                      ),
                      textAlign: TextAlign.center,
                    ).animate().fadeIn(duration: 400.ms, delay: 100.ms).shimmer(
                          duration: 1500.ms,
                          delay: 400.ms,
                          color: AppColors.primary.withOpacity(0.3),
                        ),

                    SizedBox(height: AppSpacing.xl),

                    // Animated progress bar with slide effect
                    ConstrainedBox(
                      constraints: BoxConstraints(
                        maxWidth: MediaQuery.sizeOf(context).width * 0.6,
                      ),
                      child: Column(
                        children: [
                          ShadProgress(value: loadingProgress)
                              .animate()
                              .fadeIn(duration: 400.ms, delay: 200.ms)
                              .scaleX(
                                begin: 0,
                                end: 1,
                                duration: 500.ms,
                                delay: 200.ms,
                                curve: Curves.easeOut,
                              ),
                          SizedBox(height: AppSpacing.sm),
                          Text(
                            '${(loadingProgress * 100).toInt()}%',
                            style: TextStyle(
                              fontSize: AppTypography.bodySmall,
                              color: AppColors.textSecondary,
                              fontWeight: FontWeight.w500,
                            ),
                          )
                              .animate()
                              .fadeIn(duration: 400.ms, delay: 300.ms)
                              .slideY(
                                  begin: 0.5, end: 0, curve: Curves.easeOut),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            )
          : Column(
              children: [
                // Map preview
                if (_showMapPreview && _mapPlaces.isNotEmpty) ...[
                  SizedBox(height: AppSpacing.sm),
                  _buildMapPreview(),
                ],
                // Next Best Action (Discovery Radar)
                if (nextBestAction != null) ...[
                  SizedBox(height: AppSpacing.sm),
                  _buildNBACard(),
                ],
                SizedBox(height: AppSpacing.sm),
                // Day Itinerary Timeline
                Expanded(
                  child: itinerary.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                padding: EdgeInsets.all(AppSpacing.xl),
                                decoration: BoxDecoration(
                                  color: AppColors.surface,
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  Icons.calendar_today_outlined,
                                  size: 48,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              SizedBox(height: AppSpacing.lg),
                              Text(
                                'No itinerary yet',
                                style: TextStyle(
                                  fontSize: AppTypography.titleMedium,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              SizedBox(height: AppSpacing.sm),
                              Text(
                                'Generate an itinerary to get started',
                                style: TextStyle(
                                  fontSize: AppTypography.bodyMedium,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          controller: _itineraryScrollController,
                          padding: EdgeInsets.all(AppSpacing.md),
                          itemCount: itinerary.length,
                          itemBuilder: (context, index) {
                            // Animate each itinerary item with staggered entrance
                            return _buildItineraryItem(
                                    context, itinerary[index], index)
                                .animate()
                                .fadeIn(
                                  duration: 500.ms,
                                  delay: (80 * index).ms,
                                  curve: Curves.easeOut,
                                )
                                .slideX(
                                  begin: -0.1,
                                  end: 0,
                                  duration: 500.ms,
                                  delay: (80 * index).ms,
                                  curve: Curves.easeOutQuad,
                                )
                                .scale(
                                  begin: const Offset(0.95, 0.95),
                                  end: const Offset(1.0, 1.0),
                                  duration: 500.ms,
                                  delay: (80 * index).ms,
                                  curve: Curves.easeOut,
                                );
                          },
                        ),
                ),
              ],
            ),
    );
  }

  // Build Next Best Action (Discovery Radar) card
  Widget _buildNBACard() {
    if (nextBestAction == null) return const SizedBox.shrink();

    final contextLabel = nextBestAction!['context'] ?? 'Nearby';
    final summary = nextBestAction!['summary'] ?? 'Searching for icons...';
    final confidence = ((nextBestAction!['confidence'] ?? 0.0) is int
        ? (nextBestAction!['confidence'] as int).toDouble()
        : (nextBestAction!['confidence'] ?? 0.0)) as double;
    final itineraryStops = nextBestAction!['itinerary'] as List<dynamic>? ?? [];
    final backup = nextBestAction!['backup_option'] as Map<String, dynamic>?;

    return Container(
      margin: EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: ShadCard(
        backgroundColor: AppColors.surface,
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status bar
            Container(
              padding: EdgeInsets.symmetric(
                  horizontal: AppSpacing.md, vertical: AppSpacing.sm),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.05),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(AppBorderRadius.medium),
                  topRight: Radius.circular(AppBorderRadius.medium),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: AppColors.success,
                      shape: BoxShape.circle,
                    ),
                  ).animate(onPlay: (c) => c.repeat()).scale(
                        begin: const Offset(0.8, 0.8),
                        end: const Offset(1.2, 1.2),
                        duration: 800.ms,
                        curve: Curves.easeInOut,
                      ),
                  SizedBox(width: AppSpacing.sm),
                  Text(
                    'DISCOVERY RADAR • ${contextLabel.toUpperCase()}',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                      letterSpacing: 1.2,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '${(confidence * 100).toInt()}% match',
                    style: TextStyle(
                      fontSize: 10,
                      color: AppColors.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            // Summary and Highlights
            Padding(
              padding: EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    summary,
                    style: TextStyle(
                      fontSize: AppTypography.bodyMedium,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary,
                      height: 1.5,
                    ),
                  ),
                  if (itineraryStops.isNotEmpty) ...[
                    SizedBox(height: AppSpacing.md),
                    // Next Stops List
                    ...itineraryStops.map((stop) {
                      final name = stop['name'] ?? 'Unknown';
                      final dist = stop['distance_m'] ?? 0;
                      final arrival = stop['estimated_arrival'] ?? '';
                      final reason =
                          stop['curated_reason'] ?? stop['reason'] ?? '';
                      final vibe = stop['vibe'] ?? '';

                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 32,
                              height: 32,
                              decoration: BoxDecoration(
                                color: AppColors.primary,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Center(
                                child: Text(
                                  stop['step']?.toString() ?? '1',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ),
                            SizedBox(width: AppSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          name,
                                          style: TextStyle(
                                            fontSize: AppTypography.titleSmall,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.textPrimary,
                                          ),
                                        ),
                                      ),
                                      Text(
                                        arrival,
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: AppColors.primary,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (vibe.isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 2),
                                      child: Text(
                                        vibe,
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: AppColors.accent,
                                          fontWeight: FontWeight.w600,
                                          letterSpacing: 0.5,
                                        ),
                                      ),
                                    ),
                                  SizedBox(height: 2),
                                  Text(
                                    '${dist}m • $reason',
                                    style: TextStyle(
                                      fontSize: AppTypography.bodySmall,
                                      color: AppColors.textSecondary,
                                      height: 1.3,
                                    ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ],
                  // Plan B / Backup
                  if (backup != null) ...[
                    const Divider(height: 24),
                    Row(
                      children: [
                        Icon(Icons.info_outline,
                            size: 14, color: AppColors.textSecondary),
                        SizedBox(width: AppSpacing.xs),
                        Text(
                          'PLAN B:',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: Text(
                            '${backup['name']}: ${backup['reason']}',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textSecondary,
                              fontStyle: FontStyle.italic,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            // Actions
            Padding(
              padding: EdgeInsets.only(
                  left: AppSpacing.md,
                  right: AppSpacing.md,
                  bottom: AppSpacing.md),
              child: Row(
                children: [
                  Expanded(
                    child: ShadButton(
                      size: ShadButtonSize.sm,
                      backgroundColor: AppColors.primary,
                      onPressed: () {
                        if (itineraryStops.isNotEmpty) {
                          _openMaps(itineraryStops[0]['name'], '');
                        }
                      },
                      child: const Text('Go Now',
                          style: TextStyle(color: Colors.white, fontSize: 13)),
                    ),
                  ),
                  SizedBox(width: AppSpacing.sm),
                  ShadButton.outline(
                    size: ShadButtonSize.sm,
                    onPressed: () {
                      setState(() {
                        nextBestAction = null;
                      });
                    },
                    child: const Text('Dismiss', style: TextStyle(fontSize: 13)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Dialog to search and add places to itinerary
class _AddPlaceDialog extends StatefulWidget {
  final loc.LocationData? currentLocation;
  final Function(Map<String, dynamic>) onPlaceSelected;
  final String? title;
  final String? infoText;
  final IconData? icon;

  const _AddPlaceDialog({
    required this.currentLocation,
    required this.onPlaceSelected,
    this.title,
    this.infoText,
    this.icon,
  });

  @override
  State<_AddPlaceDialog> createState() => _AddPlaceDialogState();
}

class _AddPlaceDialogState extends State<_AddPlaceDialog> {
  final TextEditingController _searchController = TextEditingController();
  final ApiService _apiService = ApiService();
  bool _isLoading = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _handlePlaceSelected(Map<String, dynamic> place) async {
    final placeId = place['place_id'] as String?;
    if (placeId == null) return;

    setState(() => _isLoading = true);

    try {
      // Use the place data from autocomplete (we're using OSM/Nominatim now)
      final geometry = place['geometry'] as Map<String, dynamic>?;
      final location = geometry?['location'] as Map<String, dynamic>?;

      if (location != null) {
        final formattedPlace = {
          'place_id': placeId,
          'name': place['description'] as String? ?? 'Unknown Place',
          'vicinity':
              place['structured_formatting']?['secondary_text'] as String? ??
                  '',
          'geometry': geometry,
          'types': [],
          'photos': [],
        };

        if (!mounted) return;
        widget.onPlaceSelected(formattedPlace);
        Navigator.pop(context);
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not fetch place details'),
            duration: Duration(milliseconds: 2500),
          ),
        );
      }
      setState(() => _isLoading = false);
    } catch (e) {
      print('Error fetching place details: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error loading place: $e'),
          duration: Duration(milliseconds: 2500),
        ),
      );
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        constraints: const BoxConstraints(maxHeight: 600, maxWidth: 500),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Container(
              padding: EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.surface,
                border: Border(
                  bottom: BorderSide(color: AppColors.border, width: 1),
                ),
              ),
              child: Row(
                children: [
                  Icon(widget.icon ?? Icons.add_location,
                      color: AppColors.primary),
                  SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      widget.title ?? 'Add Place to Itinerary',
                      style: TextStyle(
                        fontSize: AppTypography.titleMedium,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: Icon(Icons.close, color: AppColors.textPrimary),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),

            // Google Places Search bar
            Padding(
                padding: EdgeInsets.all(AppSpacing.md),
                child: _isLoading
                    ? Center(
                        child: Padding(
                          padding: EdgeInsets.all(AppSpacing.lg),
                          child: CircularProgressIndicator(
                            valueColor: AlwaysStoppedAnimation<Color>(
                                AppColors.primary),
                          ),
                        ),
                      )
                    : location_autocomplete.LocationAutocompleteTextField(
                        controller: _searchController,
                        hintText: 'Search for a place...',
                        inputDecoration: InputDecoration(
                          hintText: 'Search for a place...',
                          hintStyle: TextStyle(
                            color: AppColors.textSecondary,
                          ),
                          prefixIcon: Icon(
                            Icons.search,
                            color: AppColors.primary,
                          ),
                          filled: true,
                          fillColor: AppColors.surface,
                          border: OutlineInputBorder(
                            borderRadius:
                                BorderRadius.circular(AppBorderRadius.medium),
                            borderSide: BorderSide(color: AppColors.border),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius:
                                BorderRadius.circular(AppBorderRadius.medium),
                            borderSide: BorderSide(color: AppColors.border),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius:
                                BorderRadius.circular(AppBorderRadius.medium),
                            borderSide:
                                BorderSide(color: AppColors.primary, width: 2),
                          ),
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: AppSpacing.md,
                            vertical: AppSpacing.sm,
                          ),
                        ),
                        onPlaceSelected: (place) {
                          _handlePlaceSelected(place);
                        },
                      )),

            // Info text
            Padding(
              padding: EdgeInsets.symmetric(horizontal: AppSpacing.md),
              child: Text(
                widget.infoText ??
                    'Search for any place and tap to add it to your itinerary',
                style: TextStyle(
                  fontSize: AppTypography.bodySmall,
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
            ),

            SizedBox(height: AppSpacing.md),
          ],
        ),
      ),
    );
  }
}

/// Dialog to show swap place suggestions
class _SwapPlaceSuggestionsDialog extends StatelessWidget {
  final String oldPlaceName;
  final List<Map<String, dynamic>> suggestions;
  final Function(Map<String, dynamic>) onPlaceSelected;

  const _SwapPlaceSuggestionsDialog({
    required this.oldPlaceName,
    required this.suggestions,
    required this.onPlaceSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        constraints: const BoxConstraints(maxHeight: 600, maxWidth: 500),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Container(
              padding: EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.surface,
                border: Border(
                  bottom: BorderSide(color: AppColors.border, width: 1),
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.swap_horiz, color: AppColors.primary),
                  SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      'Swap $oldPlaceName',
                      style: TextStyle(
                        fontSize: AppTypography.titleMedium,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: Icon(Icons.close, color: AppColors.textPrimary),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),
            // Suggestions list
            Flexible(
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: suggestions.length,
                padding: EdgeInsets.all(AppSpacing.sm),
                itemBuilder: (context, index) {
                  final place = suggestions[index];
                  final placeName =
                      place['name'] ?? place['description'] ?? 'Unknown';
                  final address = place['formatted_address'] ??
                      place['vicinity'] ??
                      place['structured_formatting']?['secondary_text'] ??
                      '';
                  final photos = place['photos'] as List<dynamic>? ?? [];
                  final photoUrl = photos.isNotEmpty
                      ? (photos[0]['url'] as String? ??
                          (photos[0]['photo_reference'] != null
                              ? 'https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${photos[0]['photo_reference']}&key=YOUR_API_KEY'
                              : null))
                      : null;

                  return InkWell(
                    onTap: () {
                      onPlaceSelected(place);
                      Navigator.pop(context);
                    },
                    child: Container(
                      margin: EdgeInsets.only(bottom: AppSpacing.sm),
                      padding: EdgeInsets.all(AppSpacing.sm),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceElevated,
                        borderRadius:
                            BorderRadius.circular(AppBorderRadius.medium),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Row(
                        children: [
                          // Photo
                          if (photoUrl != null)
                            ClipRRect(
                              borderRadius:
                                  BorderRadius.circular(AppBorderRadius.small),
                              child: Image.network(
                                photoUrl,
                                width: 60,
                                height: 60,
                                fit: BoxFit.cover,
                                errorBuilder: (context, error, stackTrace) {
                                  return Container(
                                    width: 60,
                                    height: 60,
                                    color: AppColors.surface,
                                    child: Icon(Icons.place,
                                        color: AppColors.textSecondary),
                                  );
                                },
                              ),
                            )
                          else
                            Container(
                              width: 60,
                              height: 60,
                              decoration: BoxDecoration(
                                color: AppColors.surface,
                                borderRadius: BorderRadius.circular(
                                    AppBorderRadius.small),
                              ),
                              child: Icon(Icons.place,
                                  color: AppColors.textSecondary),
                            ),
                          SizedBox(width: AppSpacing.sm),
                          // Place info
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  placeName,
                                  style: TextStyle(
                                    fontSize: AppTypography.titleSmall,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.textPrimary,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                if (address.isNotEmpty) ...[
                                  SizedBox(height: 4),
                                  Text(
                                    address,
                                    style: TextStyle(
                                      fontSize: AppTypography.bodySmall,
                                      color: AppColors.textSecondary,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right,
                              color: AppColors.textSecondary),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            // Info text
            Padding(
              padding: EdgeInsets.all(AppSpacing.md),
              child: Text(
                'Tap a place to swap',
                style: TextStyle(
                  fontSize: AppTypography.bodySmall,
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// RadarAnimation widget displays a rotating radar sweep.
class RadarAnimation extends StatefulWidget {
  final AnimationController controller;
  const RadarAnimation({super.key, required this.controller});

  @override
  State<RadarAnimation> createState() => _RadarAnimationState();
}

class _RadarAnimationState extends State<RadarAnimation> {
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, child) {
        return CustomPaint(
          painter: RadarPainter(angle: widget.controller.value * 360),
          size: const Size(200, 200),
        );
      },
    );
  }
}

class RadarPainter extends CustomPainter {
  final double angle; // in degrees

  RadarPainter({required this.angle});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // Draw a faint primary color circle.
    final circlePaint = Paint()
      ..color = AppColors.primary.withOpacity(0.1)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, radius, circlePaint);

    // Draw an outer border.
    final borderPaint = Paint()
      ..color = AppColors.primary
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawCircle(center, radius, borderPaint);

    // Draw the rotating radar sweep arc.
    final sweepAngle = 30 * (3.14159265 / 180); // 30 degrees in radians.
    final startAngle = (angle - 15) * (3.14159265 / 180); // Center the sweep.
    final sweepPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          AppColors.primary.withOpacity(0.5),
          AppColors.primary.withOpacity(0.0)
        ],
        stops: const [0.0, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..style = PaintingStyle.fill;

    canvas.drawArc(Rect.fromCircle(center: center, radius: radius), startAngle,
        sweepAngle, true, sweepPaint);
  }

  @override
  bool shouldRepaint(covariant RadarPainter oldDelegate) {
    return oldDelegate.angle != angle;
  }
}
