import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:math';
import 'dart:async';

class ApiService {
  final String googleApiKey = 'AIzaSyCqeTKWDSpdukY0rG3_0jipiGY1W5UU_28';

  Future<Map<String, dynamic>?> fetchPlaceDetails(String placeId) async {
    try {
      final url = Uri.parse(
          'https://maps.googleapis.com/maps/api/place/details/json?place_id=$placeId&fields=geometry&key=$googleApiKey');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['status'] == 'OK') {
          return data['result'] as Map<String, dynamic>;
        }
      }
      return null;
    } catch (e) {
      print('Error fetching place details: $e');
      return null;
    }
  }

  /// Fetch address suggestions from OpenStreetMap (via Photon API).
  Future<List<Map<String, dynamic>>> getAddressSuggestions(String query) async {
    if (query.isEmpty || query.length < 2) return [];

    final url = Uri.parse(
        'https://photon.komoot.io/api/?q=${Uri.encodeComponent(query)}&limit=15'); // Increase limit to allow for filtering

    try {
      final response = await http.get(url, headers: {
        'User-Agent': 'Plandit/1.0',
        'Accept': 'application/json',
      });

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        final List<Map<String, dynamic>> suggestions = [];

        final features = data['features'] as List? ?? [];
        for (var feature in features) {
          final props = feature['properties'] as Map? ?? {};

          // Filter for US only
          final cCode = props['countrycode']?.toString().toUpperCase();
          final cName = props['country']?.toString().toLowerCase();

          if (cCode != 'US' && cName != 'united states' && cName != 'usa') {
            continue;
          }

          final geometry = feature['geometry'] as Map? ?? {};
          final coords = geometry['coordinates'] as List? ?? [0.0, 0.0];

          final name = props['name'];
          final city = props['city'];
          final state = props['state'];
          final countryVal = props['country'];

          // Build a clean display string
          final parts = <String>[];
          if (name != null) parts.add(name.toString());
          if (city != null && city != name) parts.add(city.toString());
          if (state != null) parts.add(state.toString());
          if (countryVal != null) parts.add(countryVal.toString());

          final displayString = parts.join(", ");
          if (displayString.isNotEmpty) {
            suggestions.add({
              'display': displayString,
              'lat': coords.length > 1 ? (coords[1] as num).toDouble() : 0.0,
              'lng': coords.length > 0 ? (coords[0] as num).toDouble() : 0.0,
            });
          }
        }
        // Deduplicate
        final seen = <String>{};
        return suggestions.where((s) => seen.add(s['display'])).toList();
      }
    } catch (e) {
      print("ERROR: Failed to fetch OSM address suggestions for '$query': $e");
    }

    return [];
  }

  // Supabase REST (for cloneable adventures)
  static const String supabaseUrl =
      'https://diytyziczzosylmyrfxo.supabase.co/rest/v1';
  // Set a publishable/anon key via --dart-define=SUPABASE_ANON_KEY=...
  // Fallback for development (DO NOT use in production - set via --dart-define instead)
  static String get supabaseAnonKey {
    final envKey =
        const String.fromEnvironment('SUPABASE_ANON_KEY', defaultValue: '');
    if (envKey.isNotEmpty) {
      return envKey;
    }
    // Development fallback - remove this in production builds
    // For production, always use: flutter run --dart-define=SUPABASE_ANON_KEY=your_key_here
    const devFallback =
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpeXR5emljenpvc3lsbXlyZnhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4NjYzOTMsImV4cCI6MjA4MDQ0MjM5M30.2Wet_5E82ippon8oDCvCV8X1g0POrO6uwUq9B5jgSr4';
    // Use fallback in development (when env key is not set)
    // In production, always set SUPABASE_ANON_KEY via --dart-define
    return devFallback;
  }

  // Backend URL - Automatically switches between local and production
  /// Fetch detailed itinerary information with rich venue data
  Future<Map<String, dynamic>?> fetchItineraryDetails(
      List<String> placeIds) async {
    if (placeIds.isEmpty) return null;

    try {
      final Uri url = Uri.parse('$baseUrl/api/api/itinerary-details/');
      print('DEBUG: Full URL: $url');
      print('DEBUG: Fetching itinerary details for ${placeIds.length} places');
      print('DEBUG: Place IDs: $placeIds');

      final requestBody = json.encode({'place_ids': placeIds});
      print('DEBUG: Request body: $requestBody');

      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: requestBody,
          )
          .timeout(const Duration(seconds: 30));

      print('DEBUG: Response status code: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        print('DEBUG: Successfully fetched itinerary details');
        print('DEBUG: Response data: $data');
        return data as Map<String, dynamic>;
      } else {
        print('ERROR: Itinerary details fetch failed: ${response.statusCode}');
        print('ERROR: Response body: ${response.body}');
        return null;
      }
    } catch (e, stackTrace) {
      print('ERROR: Exception fetching itinerary details: $e');
      print('ERROR: Stack trace: $stackTrace');
      return null;
    }
  }

  static String get baseUrl {
    // Set to true for local development, false for Railway production
    const bool useLocal = true;

    if (useLocal) {
      // For physical Android devices: Use your computer's local IP address
      // Find your IP with: ipconfig | findstr /i "IPv4"
      // Make sure both phone and computer are on the same WiFi network
      if (!kIsWeb && Platform.isAndroid) {
        // Replace with your actual local IP address (e.g., 192.168.1.163)
        // Update this if your IP changes!
        return 'http://192.168.1.163:8000';
      }
      // iOS simulator, desktop, and web can use localhost
      // For physical iOS devices, also use the local IP address
      if (!kIsWeb && Platform.isIOS) {
        return 'http://192.168.1.163:8000';
      }
      return 'http://localhost:8000';
    }

    // Production Railway deployment
    return 'https://restaurant-production-3aa0.up.railway.app';
  }

  /// Fetch cloneable adventures from Supabase (public table).
  Future<List<Map<String, dynamic>>> getCloneableAdventures(
      {int limit = 20}) async {
    try {
      print('DEBUG: getCloneableAdventures called with limit=$limit');
      print('DEBUG: supabaseUrl=$supabaseUrl');
      print(
          'DEBUG: supabaseAnonKey is ${supabaseAnonKey.isEmpty ? "EMPTY" : "SET (${supabaseAnonKey.length} chars)"}');

      if (supabaseAnonKey.isEmpty) {
        print(
            'ERROR: SUPABASE_ANON_KEY not set. Pass --dart-define=SUPABASE_ANON_KEY=... when running the app');
        return []; // Return empty list instead of throwing
      }

      final uri = Uri.parse(
          '$supabaseUrl/cloneable_adventures?select=source_id,title,new_title,subtitle,tags,header_image_url,score,stops,original_url&order=score.desc&limit=$limit');

      print('DEBUG: Requesting URL: $uri');

      // Create HTTP client with timeout
      final client = http.Client();
      try {
        final resp = await client.get(uri, headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'application/json',
          'Prefer': 'return=representation',
        }).timeout(
          const Duration(seconds: 30),
          onTimeout: () {
            print('ERROR: Request timed out after 30 seconds');
            throw TimeoutException(
                'Supabase request timed out after 30 seconds');
          },
        );

        print('DEBUG: Response status: ${resp.statusCode}');
        print('DEBUG: Response headers: ${resp.headers}');
        print('DEBUG: Response body length: ${resp.body.length}');

        if (resp.statusCode != 200) {
          print(
              'ERROR: Failed to fetch cloneable adventures (HTTP ${resp.statusCode})');
          print('ERROR: Response body: ${resp.body}');
          return []; // Return empty list instead of throwing
        }

        final data = json.decode(utf8.decode(resp.bodyBytes));
        print('DEBUG: Decoded data type: ${data.runtimeType}');

        if (data is List) {
          print('DEBUG: Found ${data.length} cloneable adventures');
          final result = data.map<Map<String, dynamic>>((e) {
            final m = Map<String, dynamic>.from(e as Map);
            // Normalize tags to List<String>
            final tags = m['tags'];
            if (tags is List) {
              m['tags'] = tags.map((x) => x.toString()).toList();
            }
            return m;
          }).toList();
          print('DEBUG: Returning ${result.length} normalized adventures');
          return result;
        }
        print('WARNING: Response is not a List, type: ${data.runtimeType}');
        return [];
      } finally {
        client.close();
      }
    } on TimeoutException catch (e) {
      print('ERROR: Timeout fetching cloneable adventures: $e');
      return [];
    } on SocketException catch (e) {
      print('ERROR: Network error fetching cloneable adventures: $e');
      print('ERROR: Check your internet connection and Supabase URL');
      return [];
    } on FormatException catch (e) {
      print('ERROR: JSON parsing error: $e');
      return [];
    } catch (e, stackTrace) {
      print('ERROR: Exception fetching cloneable adventures: $e');
      print('ERROR: Type: ${e.runtimeType}');
      print('ERROR: Stack trace: $stackTrace');
      return [];
    }
  }

  /// Fetch Instagram-worthy places from lemon8_articles guide table
  /// Get Instagram-worthy places near a location
  /// Filters for cafes, restaurants, and shops - excludes generic types like parks
  Future<List<Map<String, dynamic>>> getInstagramWorthyPlaces({
    double? lat,
    double? lng,
    int radiusMeters = 3000,
    int limit = 2,
    String? city,
  }) async {
    try {
      if (supabaseAnonKey.isEmpty) {
        print('DEBUG: Supabase key is empty, cannot fetch Instagram spots');
        return [];
      }

      // Convert radius to km for distance calculation
      final radiusKm = radiusMeters / 1000.0;

      // Query lemon8_articles table for Instagram-worthy spots
      final uri = Uri.parse(
          '$supabaseUrl/lemon8_articles?select=*&limit=50'); // Get more to filter

      print('DEBUG: Fetching Instagram spots from: $uri');
      if (lat != null && lng != null) {
        print('DEBUG: Center: ($lat, $lng), Radius: ${radiusKm}km');
      }

      final resp = await http.get(uri, headers: {
        'apikey': supabaseAnonKey,
        'Authorization': 'Bearer $supabaseAnonKey',
        'Content-Type': 'application/json',
      }).timeout(const Duration(seconds: 15));

      if (resp.statusCode != 200) {
        print('ERROR: Failed to fetch Instagram spots: ${resp.statusCode}');
        print('ERROR: Response body: ${resp.body}');
        return [];
      }

      final data = json.decode(utf8.decode(resp.bodyBytes));
      if (data is! List) {
        print('ERROR: Response is not a list, got: ${data.runtimeType}');
        return [];
      }

      print('DEBUG: Fetched ${data.length} total lemon8_articles');

      final results = <Map<String, dynamic>>[];
      int skippedNoData = 0;
      int skippedNoCoords = 0;
      int skippedDistance = 0;
      int skippedCategory = 0;

      // Filter and process results - lemon8_articles has nested structure
      for (var article in data) {
        if (article is! Map) continue;

        // Get itinerary data and coordinate arrays
        final itineraryData = article['itinerary_data'];
        final stopsLat = article['stops_lat'] as List<dynamic>?;
        final stopsLng = article['stops_lng'] as List<dynamic>?;

        if (itineraryData == null || stopsLat == null || stopsLng == null) {
          skippedNoData++;
          continue;
        }

        // Parse stops from itinerary_data
        List<dynamic> stops = [];
        if (itineraryData is Map) {
          stops = itineraryData['stops'] as List<dynamic>? ?? [];
        } else if (itineraryData is List) {
          stops = itineraryData;
        }

        if (stops.isEmpty) {
          skippedNoData++;
          continue;
        }

        // Process each stop with its coordinates
        for (int i = 0;
            i < stops.length && i < stopsLat.length && i < stopsLng.length;
            i++) {
          final stop = stops[i];
          if (stop is! Map) continue;

          final placeLat = _safeDouble(stopsLat[i], 0.0);
          final placeLng = _safeDouble(stopsLng[i], 0.0);

          if (placeLat == 0.0 || placeLng == 0.0) {
            skippedNoCoords++;
            continue;
          }

          // Calculate distance if location provided
          double distance = 0.0;
          if (lat != null && lng != null) {
            distance = _calculateDistance(lat, lng, placeLat, placeLng);
            if (distance > radiusKm) {
              skippedDistance++;
              continue;
            }
          }

          // Filter by category - exclude generic types
          final category = (stop['category'] ?? '').toString().toLowerCase();
          final excludedTypes = ['park', 'state', 'city', 'neighborhood'];

          // Skip if it's a generic type
          if (excludedTypes.any((type) => category.contains(type))) {
            skippedCategory++;
            continue;
          }

          // Format as itinerary-compatible item
          results.add({
            'name': stop['place_name'] ?? stop['name'] ?? 'Instagram Spot',
            'lat': placeLat,
            'lng': placeLng,
            'category': stop['category'] ?? 'Cafe',
            'description': stop['notes'] ??
                stop['description'] ??
                'A highly aesthetic, Instagram-worthy discovery.',
            'image_url': stop['image_url'],
            'lemon8_url': article['url'],
            'is_lemon8': true,
            'distance_km': distance,
          });
        }
      }

      print(
          'DEBUG: Filtered results - Total: ${results.length}, Skipped (no data: $skippedNoData, no coords: $skippedNoCoords, distance: $skippedDistance, category: $skippedCategory)');

      // Sort by distance if location provided, otherwise shuffle
      if (lat != null && lng != null) {
        results.sort((a, b) =>
            (a['distance_km'] as double).compareTo(b['distance_km'] as double));
      } else {
        results.shuffle();
      }

      final filtered = results.take(limit).toList();
      print('DEBUG: Returning ${filtered.length} Instagram-worthy places');
      if (filtered.isNotEmpty) {
        print(
            'DEBUG: First place: ${filtered[0]['name']} at ${filtered[0]['distance_km']}km');
      }

      return filtered;
    } catch (e) {
      print('ERROR: Exception in getInstagramWorthyPlaces: $e');
      return [];
    }
  }

  Future<String?> createSessionDjango(String userId) async {
    // Replace with your actual Django backend URL for session creation.
    final Uri url = Uri.parse("$baseUrl/api/create_session/");
    final http.Response response =
        await http.post(url, body: {"userId": userId});
    if (response.statusCode == 200) {
      final Map<String, dynamic> data =
          json.decode(utf8.decode(response.bodyBytes));
      // Assuming your Django endpoint returns a JSON with a 'sessionId' field.
      return data['sessionId'];
    } else {
      throw Exception('Failed to create session in Django');
    }
  }

  /// Fetches user preferences from Firebase to use for recommendation filtering
  Future<List<String>> _fetchUserPreferences(String userId) async {
    try {
      final prefsDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(userId)
          .collection('preferences')
          .doc('taste_profile')
          .get()
          .timeout(const Duration(seconds: 15), onTimeout: () {
        print('WARNING: User preferences query timed out');
        throw TimeoutException('User preferences query timed out');
      });

      if (prefsDoc.exists && prefsDoc.data() != null) {
        final data = prefsDoc.data()!;
        if (data.containsKey('placeIds') && data['placeIds'] is List) {
          return (data['placeIds'] as List)
              .map((item) => item.toString())
              .toList();
        }
      }

      // Fallback - check if we're using the older format where placeIds are stored directly
      final userPrefsDoc = await FirebaseFirestore.instance
          .collection('user_preferences')
          .doc(userId)
          .get()
          .timeout(const Duration(seconds: 15), onTimeout: () {
        print('WARNING: User preferences fallback query timed out');
        throw TimeoutException('User preferences fallback query timed out');
      });

      if (userPrefsDoc.exists && userPrefsDoc.data() != null) {
        final data = userPrefsDoc.data()!;
        if (data.containsKey('placeIds') && data['placeIds'] is List) {
          return (data['placeIds'] as List)
              .map((item) => item.toString())
              .toList();
        }
      }

      return [];
    } on TimeoutException {
      print('Error: User preferences query timed out');
      return [];
    } catch (e) {
      print('Error fetching user preferences: $e');
      return [];
    }
  }

  /// Records a user interaction with a restaurant to improve future recommendations.
  Future<bool> recordInteraction({
    required String establishmentId,
    required String interactionType, // 'VIEW', 'SAVE', 'VISIT', 'RATE'
    int? rating, // 1-5 stars for 'RATE' interactions
    String? tripId, // Optional trip association
  }) async {
    try {
      // *** TEMPORARY: Just log the interaction without sending to backend ***
      print(
          "DEBUG: Recording interaction (local only): $interactionType with establishment $establishmentId");
      if (rating != null) {
        print("DEBUG: Rating: $rating stars");
      }
      if (tripId != null) {
        print("DEBUG: Associated with trip: $tripId");
      }
      return true;

      /* ORIGINAL CODE - UNCOMMENT WHEN BACKEND IS WORKING
      // Get the current user's ID token
      final User? currentUser = FirebaseAuth.instance.currentUser;
      if (currentUser == null) {
        throw Exception('User not logged in');
      }

      final String? idToken = await currentUser.getIdToken();
      if (idToken == null) {
        throw Exception('Failed to get ID token');
      }

      // Build request body
      final Map<String, dynamic> requestBody = {
        'establishment_id': establishmentId,
        'interaction_type': interactionType,
      };

      // Add optional parameters if provided
      if (rating != null) {
        requestBody['rating'] = rating;
      }

      if (tripId != null) {
        requestBody['trip_id'] = tripId;
      }

      // Make the request (updated URL to match backend routes)
      final Uri url = Uri.parse("$baseUrl/api/interaction/");

      final http.Response response = await http.post(
        url,
        headers: {
          'Authorization': 'Bearer $idToken',
          'Content-Type': 'application/json',
        },
        body: json.encode(requestBody),
      );

      return response.statusCode == 200;
      */
    } catch (e) {
      print('Error recording interaction: $e');
      return false;
    }
  }

  /// Fetches restaurants directly from Firestore when the backend API is unavailable.
  /// Uses location data to prioritize nearby restaurants.
  Future<List<dynamic>> fetchRestaurantsFromFirestore(
      {required double lat,
      required double lon,
      double radiusKm = 50.0 // Default to a wider search radius
      }) async {
    try {
      print("DEBUG: Fetching restaurants directly from Firestore");

      // Get current user
      final User? currentUser = FirebaseAuth.instance.currentUser;
      if (currentUser == null) {
        print("DEBUG: User not logged in");
        throw Exception(
            'User not logged in - please sign in to get recommendations');
      }

      // Verify Firebase token to ensure authentication is working
      try {
        final String? idToken = await currentUser.getIdToken();
        if (idToken == null || idToken.isEmpty) {
          throw Exception('Firebase authentication token is invalid');
        }
        print("DEBUG: Firebase authentication verified");
      } catch (authError) {
        print("DEBUG: Firebase authentication error: $authError");
        throw Exception(
            'Authentication error: Please sign out and sign in again');
      }

      // Fetch user preferences to improve recommendations
      final userPreferences = await _fetchUserPreferences(currentUser.uid);
      print(
          "DEBUG: Found ${userPreferences.length} user preferences for Firestore fallback");

      final firestore = FirebaseFirestore.instance;

      // Debug output for Firestore connection
      print("DEBUG: Using Firestore with user UID: ${currentUser.uid}");

      // Query ALL establishments, not just user's, to get more variety
      print("DEBUG: Querying Firestore establishments collection group...");
      // Reduce timeout to 8 seconds to avoid Firestore's 10-second warning
      final results = await firestore
          .collectionGroup('establishments')
          .limit(100) // Get up to 100 establishments for more diversity
          .get()
          .timeout(Duration(seconds: 15), onTimeout: () {
        print("WARNING: Firestore query timed out after 8 seconds");
        throw TimeoutException("Firestore query timed out after 8 seconds");
      });

      print(
          "DEBUG: Firestore query returned ${results.docs.length} establishments");

      if (results.docs.isEmpty) {
        print("DEBUG: No establishments found in Firestore");
        return []; // Return empty list rather than throwing an exception
      }

      // Print all found establishment names to debug
      print("DEBUG: Found establishments:");
      for (var doc in results.docs.take(10)) {
        print(" - ${doc.data()['name'] ?? 'unnamed'} (ID: ${doc.id})");
      }
      if (results.docs.length > 10) {
        print(" - ... and ${results.docs.length - 10} more");
      }

      // Convert query results to list of maps
      final List<Map<String, dynamic>> establishments = results.docs
          .map((doc) => {
                ...doc.data(),
                'id': doc.id,
              })
          .toList();

      // Add some randomization to avoid seeing the same results repeatedly
      establishments.shuffle();

      // Process establishments to match the expected format for the UI
      final List<Map<String, dynamic>> formattedEstablishments =
          establishments.map((est) {
        // Calculate distance from user's location if location data is available
        double? distanceKm;
        if (est['geometry'] != null &&
            est['geometry']['location'] != null &&
            est['geometry']['location']['lat'] != null &&
            est['geometry']['location']['lng'] != null) {
          final double estLat = est['geometry']['location']['lat'];
          final double estLng = est['geometry']['location']['lng'];

          distanceKm = _calculateDistance(lat, lon, estLat, estLng);
        }

        // Check if this establishment is in user preferences
        final bool isPreferred = userPreferences.contains(est['id']);

        // Get categories/types for content-based similarity
        List<String> categories = [];
        if (est['types'] != null && est['types'] is List) {
          categories = (est['types'] as List).map((t) => t.toString()).toList();
        }

        // Convert data format to match API response format
        return {
          'id': est['id'],
          'name': est['name'] ?? 'Unknown Restaurant',
          'address': est['vicinity'] ??
              est['formatted_address'] ??
              'Address not available',
          'price_range': _formatPriceLevel(est['price_level']),
          'dining_style': est['diningStyle'] ?? 'CASUAL',
          'dining_style_display':
              _formatDiningStyle(est['diningStyle'] ?? 'CASUAL'),
          'distance_km': distanceKm,
          'features': _formatFeatures(est['specialFeatures'] ?? []),
          'is_preferred': isPreferred,
          'categories': categories,
          'rating': est['rating'],
          // Add a randomization factor to preference score to increase diversity
          'preference_score': _calculatePreferenceScore(
                isPreferred: isPreferred,
                distanceKm: distanceKm,
                rating: est['rating'] is num
                    ? (est['rating'] as num).toDouble()
                    : null,
                categories: categories,
                userPreferences: userPreferences,
                allEstablishments: establishments,
              ) +
              (Random().nextDouble() * 10), // Add randomization factor
        };
      }).toList();

      // Sort by preference score (combines distance, user preference, and ratings)
      formattedEstablishments.sort((a, b) {
        final scoreA = a['preference_score'] as double;
        final scoreB = b['preference_score'] as double;
        return scoreB.compareTo(scoreA); // Higher score first
      });

      // Ensure more variety by taking more results and spreading preferences
      final int maxResults =
          min(formattedEstablishments.length, 20); // Show up to 20 results
      final filteredEstablishments =
          formattedEstablishments.take(maxResults).toList();

      print(
          "DEBUG: Returning ${filteredEstablishments.length} personalized establishments");

      // Print scores of returned establishments
      print("DEBUG: Recommended establishments:");
      for (var est in filteredEstablishments
          .take(min(filteredEstablishments.length, 5))) {
        print(
            " - ${est['name']} (Score: ${est['preference_score'].toStringAsFixed(2)}, Preferred: ${est['is_preferred']}, Distance: ${est['distance_km']?.toStringAsFixed(2) ?? 'unknown'} km)");
      }

      return filteredEstablishments;
    } catch (e, stackTrace) {
      print("DEBUG: Error fetching from Firestore: $e");
      print(stackTrace);

      // Provide more helpful error messages for common issues
      if (e.toString().contains('network') ||
          e.toString().contains('connection') ||
          e is TimeoutException) {
        throw Exception(
            'Network connectivity issue - check your internet connection');
      } else if (e.toString().contains('permission') ||
          e.toString().contains('denied') ||
          e.toString().contains('unauthorized')) {
        throw Exception(
            'Access denied - you may not have permission to view these restaurants');
      } else if (e.toString().contains('authentication') ||
          e.toString().contains('sign in')) {
        throw Exception(
            'Authentication error - please sign out and sign in again');
      }

      // Return empty list on error
      final errorMessage = e.toString();
      final truncatedMessage =
          errorMessage.substring(0, min(errorMessage.length, 100));
      throw Exception('Could not load restaurants: $truncatedMessage');
    }
  }

  // Calculate a preference score based on multiple factors
  double _calculatePreferenceScore({
    required bool isPreferred,
    double? distanceKm,
    double? rating,
    required List<String> categories,
    required List<String> userPreferences,
    required List<Map<String, dynamic>> allEstablishments,
  }) {
    double score = 0.0;

    // User explicitly prefers this place (highest weight)
    if (isPreferred) {
      score += 100.0;
    }

    // Distance factor (closer is better)
    if (distanceKm != null) {
      // Inverse relationship - closer places get higher scores
      // Max 30 points for distance (diminishes as distance increases)
      score += 30.0 * (1.0 / (1.0 + distanceKm * 0.1));
    }

    // Rating factor (if available)
    if (rating != null) {
      // Up to 20 points for rating (4.5+ gets full points)
      score += (rating / 5.0) * 20.0;
    }

    // Category similarity to user preferences
    if (userPreferences.isNotEmpty) {
      // Find places the user has preferred
      final preferredPlaces = allEstablishments
          .where((est) => userPreferences.contains(est['id']))
          .toList();

      // Extract categories from preferred places
      final List<String> preferredCategories = [];
      for (final place in preferredPlaces) {
        if (place['types'] != null && place['types'] is List) {
          preferredCategories
              .addAll((place['types'] as List).map((t) => t.toString()));
        }
      }

      // Count how many categories match the user's preferred categories
      int matchingCategories = 0;
      for (final category in categories) {
        if (preferredCategories.contains(category)) {
          matchingCategories++;
        }
      }

      // Add up to 50 points based on category similarity
      if (categories.isNotEmpty && preferredCategories.isNotEmpty) {
        final similarityScore = matchingCategories / categories.length;
        score += similarityScore * 50.0;
      }
    }

    return score;
  }

  // Helper method to calculate distance between two points using Haversine formula
  double _calculateDistance(
      double lat1, double lon1, double lat2, double lon2) {
    const double earthRadiusKm = 6371.0;
    final double dLat = _degreesToRadians(lat2 - lat1);
    final double dLon = _degreesToRadians(lon2 - lon1);

    final double a = sin(dLat / 2) * sin(dLat / 2) +
        cos(_degreesToRadians(lat1)) *
            cos(_degreesToRadians(lat2)) *
            sin(dLon / 2) *
            sin(dLon / 2);

    final double c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return earthRadiusKm * c;
  }

  double _degreesToRadians(double degrees) {
    return degrees * (pi / 180.0);
  }

  // Helper method to format price level
  String _formatPriceLevel(dynamic priceLevel) {
    if (priceLevel == null) return '';

    // Convert numeric price level to dollar signs
    if (priceLevel is num) {
      int level = priceLevel.toInt();
      if (level >= 1 && level <= 4) {
        return List.filled(level, '\$').join();
      }
      return '\$' * level; // Fallback
    }
    // If it's already a string of dollar signs
    else if (priceLevel is String) {
      if (priceLevel.contains('\$')) {
        return priceLevel;
      }
      // Try to parse as number if it's a numeric string
      try {
        int level = int.parse(priceLevel);
        return '\$' * level;
      } catch (_) {
        return priceLevel; // Just return the original string
      }
    }

    return '';
  }

  // Helper method to format dining style
  String _formatDiningStyle(dynamic diningStyle) {
    if (diningStyle == null) return '';

    if (diningStyle is String) {
      // Convert SNAKE_CASE to Title Case
      return diningStyle
          .split('_')
          .map((word) => word.isEmpty
              ? ''
              : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
          .join(' ');
    } else if (diningStyle is List) {
      // Format list of dining styles
      return diningStyle
          .map((style) => style is String
              ? style
                  .split('_')
                  .map((word) => word.isEmpty
                      ? ''
                      : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
                  .join(' ')
              : style.toString())
          .join(', ');
    } else {
      // For any other case, convert to string
      return diningStyle.toString();
    }
  }

  // Helper method to format features
  List<Map<String, String>> _formatFeatures(List<dynamic> features) {
    return features.map((feature) {
      final String featureType =
          feature is String ? feature : feature.toString();

      // Format the display name (convert SNAKE_CASE to Title Case)
      final String displayName = featureType
          .split('_')
          .map((word) => word.isEmpty
              ? ''
              : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
          .join(' ');

      return {
        'feature_type': featureType,
        'feature_type_display': displayName,
      };
    }).toList();
  }

  /// Generates a day itinerary from morning to evening
  /// Ensures all places are within maxDistanceKm of each other
  Future<Map<String, dynamic>> generateDayItinerary({
    required double lat,
    required double lon,
    required List<String> selectedCategories,
    required List<dynamic> places,
    double maxDistanceKm = 1.5,
    bool vegetarianFilter = false,
  }) async {
    final User? currentUser = FirebaseAuth.instance.currentUser;
    if (currentUser == null) {
      throw Exception('User not logged in');
    }

    final Uri url = Uri.parse('$baseUrl/api/generate-day-itinerary/');

    final Map<String, dynamic> requestBody = {
      'user_id': currentUser.uid,
      'latitude': lat,
      'longitude': lon,
      'selected_categories': selectedCategories,
      'max_distance_km': maxDistanceKm,
      'places': places,
      'vegetarian_filter': vegetarianFilter,
    };

    final http.Response response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode(requestBody),
    );

    if (response.statusCode == 200) {
      return json.decode(utf8.decode(response.bodyBytes))
          as Map<String, dynamic>;
    } else {
      final errorBody = json.decode(utf8.decode(response.bodyBytes));
      throw Exception(errorBody['error'] ?? 'Failed to generate day itinerary');
    }
  }

  // / Get scraped restaurants with filtering options
  Future<List<Map<String, dynamic>>> getScrapedRestaurants({
    double? lat,
    double? lng,
    double? radiusKm,
    int limit = 50,
  }) async {
    try {
      final queryParams = {
        'limit': limit.toString(),
      };

      if (lat != null && lng != null) {
        queryParams['latitude'] = lat.toString();
        queryParams['longitude'] = lng.toString();
        queryParams['radius_km'] = (radiusKm ?? 5.0).toString();
      }

      final uri = Uri.parse('$baseUrl/api/scraped-restaurants/')
          .replace(queryParameters: queryParams);

      print('DEBUG: Fetching scraped restaurants from: $uri');

      final response = await http.get(uri).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (data is Map && data.containsKey('results')) {
          final results = List<Map<String, dynamic>>.from(data['results']);
          // Normalize Decimal fields that DRF sends as strings to prevent cast errors
          for (var r in results) {
            r['latitude'] = _safeDouble(r['latitude'], 0.0);
            r['longitude'] = _safeDouble(r['longitude'], 0.0);
            r['rating'] = _safeDouble(r['rating'], 0.0);
          }
          return results;
        }
        return [];
      } else {
        print(
            'ERROR: Failed to fetch scraped restaurants: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('ERROR: Exception in getScrapedRestaurants: $e');
      return [];
    }
  }

  /// REST Direct: Fetch ALL active places from Supabase
  Future<List<Map<String, dynamic>>> getSupabaseAllPlaces(
      {int limit = 1000}) async {
    try {
      if (supabaseAnonKey.isEmpty) return [];

      // Query res_backend_scrapedrestaurant for all active places
      final uri = Uri.parse(
          '$supabaseUrl/res_backend_scrapedrestaurant?select=*&is_active=eq.true&limit=$limit');

      print('DEBUG: Fetching ALL active places from Supabase: $uri');

      final resp = await http.get(uri, headers: {
        'apikey': supabaseAnonKey,
        'Authorization': 'Bearer $supabaseAnonKey',
        'Content-Type': 'application/json',
      }).timeout(const Duration(seconds: 20));

      if (resp.statusCode != 200) {
        print('ERROR: Supabase direct fetch failed: ${resp.body}');
        return [];
      }

      final data = json.decode(utf8.decode(resp.bodyBytes));
      if (data is List) {
        final results = List<Map<String, dynamic>>.from(data);
        for (var r in results) {
          r['latitude'] = _safeDouble(r['latitude'], 0.0);
          r['longitude'] = _safeDouble(r['longitude'], 0.0);
          r['rating'] = _safeDouble(r['rating'], 0.0);
        }
        return results;
      }
      return [];
    } catch (e) {
      print('ERROR: Exception in getSupabaseAllPlaces: $e');
      return [];
    }
  }

  // ============================================
  // USER ENGAGEMENT METHODS (SUPABASE)
  // ============================================

  /// Save a place to loved_places
  Future<bool> lovePlace({
    required String userId,
    required String placeId,
    required String name,
    double? rating,
    double? lat,
    double? lng,
  }) async {
    try {
      if (supabaseAnonKey.isEmpty) return false;
      final uri = Uri.parse('$supabaseUrl/loved_places');
      final response = await http.post(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'application/json',
          'Prefer': 'resolution=merge-duplicates',
        },
        body: json.encode({
          'user_id': userId,
          'place_id': placeId,
          'name': name,
          'rating': rating,
          'lat': lat,
          'lng': lng,
        }),
      );
      return response.statusCode == 201 ||
          response.statusCode == 200 ||
          response.statusCode == 204;
    } catch (e) {
      print('ERROR: lovePlace failure: $e');
      return false;
    }
  }

  /// Remove a place from loved_places
  Future<bool> unlovePlace(String userId, String placeId) async {
    try {
      if (supabaseAnonKey.isEmpty) return false;
      final uri = Uri.parse(
          '$supabaseUrl/loved_places?user_id=eq.$userId&place_id=eq.$placeId');
      final response = await http.delete(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
        },
      );
      return response.statusCode == 204 || response.statusCode == 200;
    } catch (e) {
      print('ERROR: unlovePlace failure: $e');
      return false;
    }
  }

  /// Check if a place is loved by the user
  Future<bool> isPlaceLoved(String userId, String placeId) async {
    try {
      if (supabaseAnonKey.isEmpty) return false;
      final uri = Uri.parse(
          '$supabaseUrl/loved_places?user_id=eq.$userId&place_id=eq.$placeId&select=id');
      final response = await http.get(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
        },
      );
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes)) as List;
        return data.isNotEmpty;
      }
      return false;
    } catch (e) {
      print('ERROR: isPlaceLoved failure: $e');
      return false;
    }
  }

  /// Get all loved places for a user
  Future<List<Map<String, dynamic>>> getLovedPlaces(String userId) async {
    try {
      if (supabaseAnonKey.isEmpty) return [];
      final uri = Uri.parse(
          '$supabaseUrl/loved_places?user_id=eq.$userId&order=saved_at.desc');
      final response = await http.get(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
        },
      );
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        return List<Map<String, dynamic>>.from(data);
      }
      return [];
    } catch (e) {
      print('ERROR: getLovedPlaces failure: $e');
      return [];
    }
  }

  /// Save a place to disliked_places
  Future<bool> dislikePlace(String userId, String placeId, String? name) async {
    try {
      if (supabaseAnonKey.isEmpty) return false;
      final uri = Uri.parse('$supabaseUrl/disliked_places');
      final response = await http.post(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'application/json',
          'Prefer': 'resolution=merge-duplicates',
        },
        body: json.encode({
          'user_id': userId,
          'place_id': placeId,
          'name': name,
        }),
      );
      return response.statusCode == 201 ||
          response.statusCode == 204 ||
          response.statusCode == 200;
    } catch (e) {
      print('ERROR: dislikePlace failure: $e');
      return false;
    }
  }

  /// Get list of disliked place IDs
  Future<List<String>> getDislikedPlaceIds(String userId) async {
    try {
      if (supabaseAnonKey.isEmpty) return [];
      final uri = Uri.parse(
          '$supabaseUrl/disliked_places?user_id=eq.$userId&select=place_id');
      final response = await http.get(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
        },
      );
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes)) as List;
        return data.map((e) => e['place_id'].toString()).toList();
      }
      return [];
    } catch (e) {
      print('ERROR: getDislikedPlaceIds failure: $e');
      return [];
    }
  }

  /// Submit a user tip
  Future<bool> submitUserTip(
      String userId, String placeId, String tipText) async {
    try {
      if (supabaseAnonKey.isEmpty) return false;
      final uri = Uri.parse('$supabaseUrl/user_tips');
      final response = await http.post(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'user_id': userId,
          'place_id': placeId,
          'tip_text': tipText,
        }),
      );
      return response.statusCode == 201;
    } catch (e) {
      print('ERROR: submitUserTip failure: $e');
      return false;
    }
  }

  /// Record an uploaded image URL
  Future<bool> recordPlaceImage(
      String userId, String placeId, String imageUrl) async {
    try {
      if (supabaseAnonKey.isEmpty) return false;
      final uri = Uri.parse('$supabaseUrl/place_images');
      final response = await http.post(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'user_id': userId,
          'place_id': placeId,
          'image_url': imageUrl,
        }),
      );
      return response.statusCode == 201;
    } catch (e) {
      print('ERROR: recordPlaceImage failure: $e');
      return false;
    }
  }

  /// Helper to upload file to Supabase Storage via REST
  /// Note: This is a simplified version, requires a public bucket named 'place-images'
  Future<String?> uploadImageToSupabase(String fileName, File imageFile) async {
    try {
      if (supabaseAnonKey.isEmpty) return null;

      // Bucket name: place-images
      final storageUrl = supabaseUrl.replaceAll('/rest/v1', '/storage/v1');
      final uri = Uri.parse('$storageUrl/object/place-images/$fileName');

      final response = await http.post(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'image/jpeg', // Or detect mime type
        },
        body: await imageFile.readAsBytes(),
      );

      if (response.statusCode == 200) {
        // Return the public URL
        // https://diytyziczzosylmyrfxo.supabase.co/storage/v1/object/public/place-images/filename
        return '$storageUrl/object/public/place-images/$fileName';
      }
      print(
          'ERROR: uploadImageToSupabase failure: ${response.statusCode} - ${response.body}');
      return null;
    } catch (e) {
      print('ERROR: uploadImageToSupabase exception: $e');
      return null;
    }
  }

  // ============================================
  // DISCOVERY & PRE-CREATED ITINERARIES METHODS
  // ============================================

  /// Get featured pre-created itineraries for home page
  Future<List<Map<String, dynamic>>> getFeaturedItineraries({
    int limit = 8,
    int maxRetries = 2,
  }) async {
    print(
        'DEBUG: getFeaturedItineraries() called with limit=$limit, maxRetries=$maxRetries');
    print('DEBUG: baseUrl = $baseUrl');

    int retryCount = 0;

    while (retryCount <= maxRetries) {
      try {
        final Uri url =
            Uri.parse('$baseUrl/api/discovery/featured-itineraries/')
                .replace(queryParameters: {
          'limit': limit.toString(),
        });

        print(
            'DEBUG: Fetching featured itineraries from: $url (attempt ${retryCount + 1}/${maxRetries + 1})');
        print('DEBUG: About to make HTTP GET request...');

        // Create HTTP client with longer timeout
        final client = http.Client();
        try {
          final response = await client.get(url).timeout(
            const Duration(seconds: 30),
            onTimeout: () {
              print(
                  'ERROR: Request timeout after 30 seconds - attempt ${retryCount + 1}');
              throw TimeoutException('Request timeout');
            },
          );

          print('DEBUG: Response status: ${response.statusCode}');
          print('DEBUG: Response body length: ${response.body.length}');

          if (response.statusCode == 200) {
            try {
              final data = json.decode(utf8.decode(response.bodyBytes))
                  as Map<String, dynamic>;
              print('DEBUG: Response keys: ${data.keys.toList()}');

              // Validate response structure
              if (!data.containsKey('featured_itineraries')) {
                print('ERROR: Response missing "featured_itineraries" key');
                print('ERROR: Available keys: ${data.keys.toList()}');
                print('ERROR: Full response: ${response.body}');
                return [];
              }

              final featuredItinerariesRaw = data['featured_itineraries'];
              if (featuredItinerariesRaw == null) {
                print('ERROR: featured_itineraries is null');
                return [];
              }

              if (featuredItinerariesRaw is! List) {
                print(
                    'ERROR: featured_itineraries is not a List, type: ${featuredItinerariesRaw.runtimeType}');
                return [];
              }

              final itineraries = <Map<String, dynamic>>[];
              for (var i = 0; i < featuredItinerariesRaw.length; i++) {
                try {
                  final item = featuredItinerariesRaw[i];
                  if (item is! Map<String, dynamic>) {
                    print(
                        'ERROR: Item at index $i is not a Map, type: ${item.runtimeType}');
                    continue;
                  }

                  // Normalize and validate the itinerary data
                  final normalizedItinerary = _normalizeItineraryData(item);
                  if (normalizedItinerary.isNotEmpty) {
                    itineraries.add(normalizedItinerary);
                  } else {
                    print('WARNING: Skipping invalid itinerary at index $i');
                  }
                } catch (e, stackTrace) {
                  print('ERROR: Exception parsing itinerary at index $i: $e');
                  print('ERROR: Stack trace: $stackTrace');
                  print('ERROR: Item data: ${featuredItinerariesRaw[i]}');
                }
              }

              print(
                  'DEBUG: Successfully parsed ${itineraries.length} featured itineraries');

              // Log total count from API response
              if (data.containsKey('total_featured')) {
                print(
                    'DEBUG: API returned total_featured: ${data['total_featured']}');
              }

              // Log first itinerary structure for debugging
              if (itineraries.isNotEmpty) {
                print(
                    'DEBUG: First itinerary keys: ${itineraries[0].keys.toList()}');
                print(
                    'DEBUG: First itinerary title: ${itineraries[0]['title']}');
                print(
                    'DEBUG: First itinerary has sample_image_url: ${itineraries[0].containsKey('sample_image_url')}');
                print(
                    'DEBUG: First itinerary has itinerary_data: ${itineraries[0].containsKey('itinerary_data')}');
              }

              return itineraries;
            } catch (e, stackTrace) {
              print('ERROR: Exception parsing JSON response: $e');
              print('ERROR: Stack trace: $stackTrace');
              print('ERROR: Response body: ${response.body}');
              return [];
            }
          } else {
            print(
                'ERROR: Failed to fetch featured itineraries: ${response.statusCode}');
            print('ERROR: Response body: ${response.body}');
            return [];
          }
        } finally {
          client.close();
        }
      } on TimeoutException catch (e) {
        retryCount++;
        if (retryCount > maxRetries) {
          print(
              'ERROR: Connection timeout after ${maxRetries + 1} attempts - Make sure Django server is running on port 8000');
          print('ERROR: Base URL was: $baseUrl');
          return [];
        }
        print('DEBUG: Retrying after timeout... (${retryCount}/${maxRetries})');
        await Future.delayed(
            Duration(seconds: 2 * retryCount)); // Exponential backoff
      } on SocketException catch (e) {
        retryCount++;
        if (retryCount > maxRetries) {
          print('ERROR: Socket exception - Server may not be running: $e');
          print('ERROR: Base URL was: $baseUrl');
          return [];
        }
        print(
            'DEBUG: Retrying after socket error... (${retryCount}/${maxRetries})');
        await Future.delayed(Duration(seconds: 2 * retryCount));
      } catch (e) {
        print('ERROR: Exception fetching featured itineraries: $e');
        print('ERROR: Base URL was: $baseUrl');
        return [];
      }
    }

    return [];
  }

  /// Normalize and validate itinerary data from API response
  Map<String, dynamic> _normalizeItineraryData(Map<String, dynamic> rawData) {
    try {
      final normalized = <String, dynamic>{};

      // Required fields with defaults
      normalized['id'] = _safeInt(rawData['id'], 0);
      normalized['title'] =
          rawData['title']?.toString().trim() ?? 'Untitled Itinerary';
      normalized['description'] =
          rawData['description']?.toString().trim() ?? '';

      // Optional fields with safe defaults
      final subtitle = rawData['subtitle']?.toString().trim();
      if (subtitle != null && subtitle.isNotEmpty) {
        normalized['subtitle'] = subtitle;
      } else {
        // Build subtitle from neighborhood and cuisine
        final neighborhood = rawData['neighborhood']?.toString().trim() ?? '';
        final cuisine = rawData['cuisine']?.toString().trim() ?? '';
        if (neighborhood.isNotEmpty && cuisine.isNotEmpty) {
          normalized['subtitle'] = '$neighborhood • $cuisine';
        } else {
          normalized['subtitle'] =
              neighborhood.isNotEmpty ? neighborhood : cuisine;
        }
      }

      normalized['cuisine'] = rawData['cuisine']?.toString().trim() ?? '';
      normalized['price_range'] =
          rawData['price_range']?.toString().trim() ?? '';
      normalized['neighborhood'] =
          rawData['neighborhood']?.toString().trim() ?? '';

      // Sample image URL - clean and validate
      final sampleImageUrl =
          rawData['sample_image_url']?.toString().trim() ?? '';
      if (sampleImageUrl.isNotEmpty &&
          sampleImageUrl != 'null' &&
          sampleImageUrl != 'None' &&
          (sampleImageUrl.startsWith('http://') ||
              sampleImageUrl.startsWith('https://'))) {
        normalized['sample_image_url'] = sampleImageUrl;
      } else {
        normalized['sample_image_url'] = '';
      }

      // Numeric fields with type conversion
      normalized['restaurant_count'] = _safeInt(rawData['restaurant_count'], 0);
      normalized['enriched_count'] = _safeInt(rawData['enriched_count'], 0);
      normalized['enrichment_percentage'] =
          _safeDouble(rawData['enrichment_percentage'], 0.0);
      normalized['latitude'] = _safeDouble(rawData['latitude'], 0.0);
      normalized['longitude'] = _safeDouble(rawData['longitude'], 0.0);
      normalized['radius_km'] = _safeDouble(rawData['radius_km'], 0.0);
      normalized['min_rating'] = _safeDouble(rawData['min_rating'], 0.0);

      // Boolean fields
      normalized['is_featured'] = rawData['is_featured'] == true;

      // Tags - ensure it's a List of strings
      if (rawData['tags'] != null) {
        if (rawData['tags'] is List) {
          normalized['tags'] = (rawData['tags'] as List)
              .map((e) => e?.toString().trim() ?? '')
              .where((e) => e.isNotEmpty)
              .toList();
        } else if (rawData['tags'] is String) {
          // Handle case where tags might be a comma-separated string
          final tagString = rawData['tags'].toString().trim();
          normalized['tags'] = tagString.isNotEmpty
              ? tagString
                  .split(',')
                  .map((e) => e.trim())
                  .where((e) => e.isNotEmpty)
                  .toList()
              : [];
        } else {
          normalized['tags'] = [];
        }
      } else {
        normalized['tags'] = [];
      }

      // Itinerary data - normalize and validate structure
      if (rawData['itinerary_data'] != null &&
          rawData['itinerary_data'] is Map) {
        final itineraryData = rawData['itinerary_data'] as Map<String, dynamic>;
        final normalizedItineraryData = <String, dynamic>{};

        // Ensure itinerary is a list
        if (itineraryData['itinerary'] != null &&
            itineraryData['itinerary'] is List) {
          final itineraryItems = (itineraryData['itinerary'] as List)
              .map((item) => _normalizeItineraryItem(item))
              .where((item) => item.isNotEmpty)
              .toList();
          normalizedItineraryData['itinerary'] = itineraryItems;
        } else {
          normalizedItineraryData['itinerary'] = [];
        }

        // Preserve enrichment_stats if present
        if (itineraryData['enrichment_stats'] != null &&
            itineraryData['enrichment_stats'] is Map) {
          normalizedItineraryData['enrichment_stats'] =
              itineraryData['enrichment_stats'] as Map<String, dynamic>;
        }

        // Preserve route_stats if present
        if (itineraryData['route_stats'] != null &&
            itineraryData['route_stats'] is Map) {
          normalizedItineraryData['route_stats'] =
              itineraryData['route_stats'] as Map<String, dynamic>;
        }

        normalized['itinerary_data'] = normalizedItineraryData;
      } else {
        normalized['itinerary_data'] = <String, dynamic>{'itinerary': []};
      }

      // Timestamps
      normalized['created_at'] = rawData['created_at']?.toString().trim() ?? '';
      normalized['last_updated'] = rawData['last_updated']?.toString().trim() ??
          rawData['created_at']?.toString().trim() ??
          '';

      return normalized;
    } catch (e, stackTrace) {
      print('ERROR: Exception in _normalizeItineraryData: $e');
      print('ERROR: Stack trace: $stackTrace');
      print('ERROR: Raw data keys: ${rawData.keys.toList()}');
      return <String, dynamic>{};
    }
  }

  /// Normalize a single itinerary item (restaurant) from itinerary_data.itinerary
  Map<String, dynamic> _normalizeItineraryItem(dynamic item) {
    try {
      if (item == null || item is! Map) {
        return <String, dynamic>{};
      }

      final normalized = <String, dynamic>{};
      final itemMap = item as Map<String, dynamic>;

      // Basic fields
      normalized['place_id'] =
          (itemMap['place_id'] ?? itemMap['placeId'])?.toString();
      normalized['place_name'] =
          (itemMap['place_name'] ?? itemMap['name'])?.toString().trim() ?? '';
      normalized['address'] = itemMap['address']?.toString().trim() ?? '';

      // Handle coordinates (direct or nested)
      if (itemMap['coordinates'] != null && itemMap['coordinates'] is Map) {
        final coords = itemMap['coordinates'] as Map;
        normalized['latitude'] = _safeDouble(coords['lat'], null);
        normalized['longitude'] = _safeDouble(coords['lng'], null);
      } else {
        normalized['latitude'] = _safeDouble(itemMap['latitude'], null);
        normalized['longitude'] = _safeDouble(itemMap['longitude'], null);
      }

      normalized['rating'] = _safeDouble(itemMap['rating'], 0.0);
      normalized['price_range'] =
          itemMap['price_range']?.toString().trim() ?? '';
      normalized['time_slot'] = itemMap['time_slot']?.toString().trim() ?? '';
      normalized['is_enriched'] = itemMap['is_enriched'] == true;

      // Normalize postgres_data
      if (itemMap['postgres_data'] != null && itemMap['postgres_data'] is Map) {
        final postgresData = itemMap['postgres_data'] as Map<String, dynamic>;
        final normalizedPostgres = <String, dynamic>{};

        // Photos - ensure it's a list of valid URLs
        if (postgresData['photos'] != null) {
          if (postgresData['photos'] is List) {
            final photos = (postgresData['photos'] as List)
                .map((photo) {
                  if (photo is String) {
                    final url = photo.trim();
                    if (url.isNotEmpty &&
                        url != 'null' &&
                        url != 'None' &&
                        (url.startsWith('http://') ||
                            url.startsWith('https://'))) {
                      return url;
                    }
                  } else if (photo is Map) {
                    // Handle photo object with 'url' field
                    final url = photo['url']?.toString().trim() ?? '';
                    if (url.isNotEmpty &&
                        (url.startsWith('http://') ||
                            url.startsWith('https://'))) {
                      return url;
                    }
                  }
                  return null;
                })
                .where((url) => url != null)
                .toList();
            normalizedPostgres['photos'] = photos;
          } else {
            normalizedPostgres['photos'] = [];
          }
        } else {
          normalizedPostgres['photos'] = [];
        }

        // Other postgres_data fields
        normalizedPostgres['menu_items'] = postgresData['menu_items'] is List
            ? postgresData['menu_items']
            : [];
        normalizedPostgres['reviews'] =
            postgresData['reviews'] is List ? postgresData['reviews'] : [];
        normalizedPostgres['tags'] =
            postgresData['tags'] is List ? postgresData['tags'] : [];
        normalizedPostgres['features'] =
            postgresData['features'] is List ? postgresData['features'] : [];
        normalizedPostgres['about'] =
            postgresData['about']?.toString().trim() ?? '';
        normalizedPostgres['price_range'] =
            postgresData['price_range']?.toString().trim() ?? '';
        normalizedPostgres['hours'] = postgresData['hours'] is Map
            ? postgresData['hours']
            : <String, dynamic>{};
        normalizedPostgres['categories'] = postgresData['categories'] is List
            ? postgresData['categories']
            : [];
        normalizedPostgres['phone'] =
            postgresData['phone']?.toString().trim() ?? '';
        normalizedPostgres['website'] =
            postgresData['website']?.toString().trim() ?? '';

        normalized['postgres_data'] = normalizedPostgres;
      } else {
        normalized['postgres_data'] = <String, dynamic>{'photos': []};
      }

      // Preserve enrichment_metadata if present
      if (itemMap['enrichment_metadata'] != null &&
          itemMap['enrichment_metadata'] is Map) {
        normalized['enrichment_metadata'] =
            itemMap['enrichment_metadata'] as Map<String, dynamic>;
      }

      return normalized;
    } catch (e, stackTrace) {
      print('ERROR: Exception in _normalizeItineraryItem: $e');
      print('ERROR: Stack trace: $stackTrace');
      return <String, dynamic>{};
    }
  }

  /// Safely convert value to int
  int _safeInt(dynamic value, int defaultValue) {
    if (value == null) return defaultValue;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) {
      final parsed = int.tryParse(value);
      return parsed ?? defaultValue;
    }
    return defaultValue;
  }

  /// Safely convert value to double
  double _safeDouble(dynamic value, double? defaultValue) {
    if (value == null) return defaultValue ?? 0.0;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) {
      final trimmed = value.trim();
      if (trimmed.isEmpty) return defaultValue ?? 0.0;
      final parsed = double.tryParse(trimmed);
      return parsed ?? defaultValue ?? 0.0;
    }
    return defaultValue ?? 0.0;
  }

  /// Get pre-created itineraries with optional filters
  Future<List<Map<String, dynamic>>> getPreCreatedItineraries({
    String? cuisine,
    String? priceRange,
    double? minRating,
    List<String>? tags,
    double? latitude,
    double? longitude,
    double? radiusKm,
    int limit = 20,
  }) async {
    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
      };

      if (cuisine != null && cuisine.isNotEmpty) {
        queryParams['cuisine'] = cuisine;
      }
      if (priceRange != null && priceRange.isNotEmpty) {
        queryParams['price_range'] = priceRange;
      }
      if (minRating != null && minRating > 0) {
        queryParams['min_rating'] = minRating.toString();
      }
      if (tags != null && tags.isNotEmpty) {
        queryParams['tags'] = tags.join(',');
      }
      if (latitude != null && longitude != null) {
        queryParams['latitude'] = latitude.toString();
        queryParams['longitude'] = longitude.toString();
      }
      if (radiusKm != null) {
        queryParams['radius_km'] = radiusKm.toString();
      }

      final Uri url =
          Uri.parse('$baseUrl/api/discovery/pre-created-itineraries/')
              .replace(queryParameters: queryParams);

      final response = await http.get(url);

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return (data['itineraries'] as List)
            .map((item) => item as Map<String, dynamic>)
            .toList();
      } else {
        print(
            'ERROR: Failed to fetch pre-created itineraries: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('ERROR: Exception fetching pre-created itineraries: $e');
      return [];
    }
  }

  /// Generate and enrich itinerary with Postgres data
  Future<Map<String, dynamic>> generateAndEnrichItinerary({
    required double latitude,
    required double longitude,
    required double radiusKm,
    required List<dynamic> places,
    String? cuisine,
    String? priceRange,
    double? minRating,
    List<String>? tags,
  }) async {
    try {
      final Uri url =
          Uri.parse('$baseUrl/api/discovery/generate-and-enrich-itinerary/');

      final Map<String, dynamic> requestBody = {
        'latitude': latitude,
        'longitude': longitude,
        'radius_km': radiusKm,
        'places': places,
      };

      if (cuisine != null && cuisine.isNotEmpty) {
        requestBody['cuisine'] = cuisine;
      }
      if (priceRange != null && priceRange.isNotEmpty) {
        requestBody['price_range'] = priceRange;
      }
      if (minRating != null && minRating > 0) {
        requestBody['min_rating'] = minRating;
      }
      if (tags != null && tags.isNotEmpty) {
        requestBody['tags'] = tags.join(',');
      }

      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        final errorBody = json.decode(response.body);
        throw Exception(
            errorBody['error'] ?? 'Failed to generate enriched itinerary');
      }
    } catch (e) {
      print('ERROR: Exception generating enriched itinerary: $e');
      rethrow;
    }
  }

  // ============================================
  // NOMINATIM GEOCODING METHODS
  // ============================================

  /// Reverse geocoding using Nominatim (replaces Google Geocoding)
  Future<Map<String, dynamic>?> reverseGeocodeNominatim(
    double lat,
    double lon,
  ) async {
    // Add delay to respect rate limit (1 req/sec)
    await Future.delayed(Duration(milliseconds: 1100));

    final Uri url = Uri.https('nominatim.openstreetmap.org', '/reverse', {
      'lat': lat.toString(),
      'lon': lon.toString(),
      'format': 'json',
      'addressdetails': '1',
    });

    try {
      final response = await http.get(
        url,
        headers: {
          'User-Agent': 'RestaurantTracker/1.0', // Required by Nominatim
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final address = data['address'] as Map<String, dynamic>? ?? {};

        // Build formatted address
        final parts = <String>[];
        if (address['road'] != null) parts.add(address['road'] as String);
        if (address['city'] != null) parts.add(address['city'] as String);
        if (address['state'] != null) parts.add(address['state'] as String);
        if (address['country'] != null) parts.add(address['country'] as String);

        return {
          'formatted_address': parts.join(', '),
          'address_components': address,
        };
      }
    } catch (e) {
      print("ERROR: Nominatim reverse geocoding failed: $e");
    }

    return null;
  }

  /// Forward geocoding using Nominatim
  Future<List<Map<String, dynamic>>> geocodeNominatim(String query) async {
    await Future.delayed(Duration(milliseconds: 1100)); // Rate limit

    final Uri url = Uri.https('nominatim.openstreetmap.org', '/search', {
      'q': query,
      'format': 'json',
      'addressdetails': '1',
      'limit': '10',
    });

    try {
      final response = await http.get(
        url,
        headers: {
          'User-Agent': 'RestaurantTracker/1.0',
        },
      );

      if (response.statusCode == 200) {
        final results = json.decode(response.body) as List<dynamic>;

        return results.map((result) {
          return {
            'place_id': result['place_id'].toString(),
            'formatted_address': result['display_name'] as String? ?? '',
            'geometry': {
              'location': {
                'lat': double.parse(result['lat'] as String),
                'lng': double.parse(result['lon'] as String),
              },
            },
          };
        }).toList();
      }
    } catch (e) {
      print("ERROR: Nominatim geocoding failed: $e");
    }

    return [];
  }

  // ============================================
  // GOOGLE MAPS SCRAPING METHODS
  // ============================================

  /// Helper function to calculate string similarity (simple Levenshtein-based)
  double _calculateStringSimilarity(String s1, String s2) {
    if (s1 == s2) return 1.0;
    if (s1.isEmpty || s2.isEmpty) return 0.0;

    // Simple similarity: count matching characters in order
    int matches = 0;
    int minLen = s1.length < s2.length ? s1.length : s2.length;
    int maxLen = s1.length > s2.length ? s1.length : s2.length;

    for (int i = 0; i < minLen; i++) {
      if (s1[i] == s2[i]) matches++;
    }

    return matches / maxLen;
  }

  /// Safe array access helper (replaces JavaScript eval lookup)
  dynamic _safeLookup(dynamic data, List<int> indexes) {
    try {
      dynamic result = data;
      for (final index in indexes) {
        if (result is List && index < result.length) {
          result = result[index];
        } else if (result is Map && result.containsKey(index)) {
          result = result[index];
        } else {
          return null;
        }
      }
      return result;
    } catch (e) {
      return null;
    }
  }

  /// Prepares Google Maps response data for parsing
  List<dynamic> _prepareGoogleMapsData(String input) {
    try {
      String cleaned = input;

      // Remove /*""*/ at the end if present (6 characters)
      if (cleaned.length >= 6 && cleaned.endsWith('/*""*/')) {
        cleaned = cleaned.substring(0, cleaned.length - 6);
      }

      // Handle format: {"c":0,"d":")]}'\n[...]}
      // First parse the outer JSON object
      dynamic outerJson;
      try {
        outerJson = json.decode(cleaned);
      } catch (e) {
        print("ERROR: Failed to parse outer JSON: $e");
        return [];
      }

      // Check if it's the {"c":0,"d":"...} format
      if (outerJson is Map && outerJson.containsKey('d')) {
        final d = outerJson['d'];

        // If "d" is a string, parse it
        if (d is String) {
          String dCleaned = d;

          // Remove )]}' prefix if present
          if (dCleaned.startsWith(")]}'")) {
            dCleaned = dCleaned.substring(4);
          }

          // Remove newlines
          dCleaned = dCleaned.replaceAll('\n', '').trim();

          try {
            final dParsed = json.decode(dCleaned);

            // Now extract places from the parsed data
            if (dParsed is List && dParsed.isNotEmpty) {
              final first = dParsed[0];
              if (first is List && first.length > 1) {
                final second = first[1];
                if (second is List) {
                  return second
                      .map((array) {
                        if (array is List && array.length > 14) {
                          return array[14];
                        }
                        return null;
                      })
                      .where((item) => item != null)
                      .toList();
                }
              }
            }
          } catch (e) {
            print("ERROR: Failed to parse 'd' string: $e");
            return [];
          }
        }
        // If "d" is already a List or Map, use it directly
        else if (d is List && d.isNotEmpty) {
          final first = d[0];
          if (first is List && first.length > 1) {
            final second = first[1];
            if (second is List) {
              return second
                  .map((array) {
                    if (array is List && array.length > 14) {
                      return array[14];
                    }
                    return null;
                  })
                  .where((item) => item != null)
                  .toList();
            }
          }
        }
      }

      // Fallback: Try direct array format [["query", [[...]]]]
      String testCleaned = cleaned;
      if (testCleaned.contains(")]}'")) {
        final index = testCleaned.indexOf(")]}'");
        testCleaned = testCleaned.substring(index + 4);
      }
      testCleaned = testCleaned.replaceAll('\n', '').trim();

      if (testCleaned.length >= 6 && testCleaned.endsWith('/*""*/')) {
        testCleaned = testCleaned.substring(0, testCleaned.length - 6);
      }

      try {
        final jsonData = json.decode(testCleaned);
        if (jsonData is List && jsonData.isNotEmpty) {
          final first = jsonData[0];
          if (first is List && first.length > 1) {
            final second = first[1];
            if (second is List) {
              return second
                  .map((array) {
                    if (array is List && array.length > 14) {
                      return array[14];
                    }
                    return null;
                  })
                  .where((item) => item != null)
                  .toList();
            }
          }
        }
      } catch (e) {
        print("ERROR: Failed fallback parsing: $e");
      }

      return [];
    } catch (e) {
      print("ERROR: Failed to prepare Google Maps data: $e");
      final preview = input.length > 300 ? input.substring(0, 300) : input;
      print("DEBUG: Response preview: $preview");
      return [];
    }
  }

  /// Extracts latitude and longitude from place data
  Map<String, double> _getLatLong(dynamic place) {
    // Based on test output: coordinates are at index 208: [[null, null, lat, lng]]
    // Safely convert to double - values might be int or double
    double? lat;
    double? long;

    // Primary location: index 208[0][2] for lat, 208[0][3] for lng
    final latValue = _safeLookup(place, [208, 0, 2]);
    if (latValue != null) {
      if (latValue is num) {
        lat = latValue.toDouble();
      } else if (latValue is String) {
        lat = double.tryParse(latValue);
      }
    }

    final longValue = _safeLookup(place, [208, 0, 3]);
    if (longValue != null) {
      if (longValue is num) {
        long = longValue.toDouble();
      } else if (longValue is String) {
        long = double.tryParse(longValue);
      }
    }

    // Fallback 1: try index 9 (sometimes coordinates are here)
    if (lat == null || long == null) {
      if (place is List && place.length > 9 && place[9] is List) {
        final altCoords = place[9] as List;
        if (altCoords.length > 2) {
          final altLat = altCoords[2];
          final altLng = altCoords.length > 3 ? altCoords[3] : null;
          if (altLat is num && lat == null) {
            lat = altLat.toDouble();
          }
          if (altLng is num && long == null) {
            long = altLng.toDouble();
          }
        }
      }
    }

    // Fallback 2: try alternative location structure
    if (lat == null) {
      final altLatValue = _safeLookup(place, [37, 0, 0, 8, 0, 2]);
      if (altLatValue != null) {
        if (altLatValue is num) {
          lat = altLatValue.toDouble();
        } else if (altLatValue is String) {
          lat = double.tryParse(altLatValue);
        }
      }
    }
    if (long == null) {
      final altLongValue = _safeLookup(place, [37, 0, 0, 8, 0, 1]);
      if (altLongValue != null) {
        if (altLongValue is num) {
          long = altLongValue.toDouble();
        } else if (altLongValue is String) {
          long = double.tryParse(altLongValue);
        }
      }
    }

    // Fallback 3: Search through indices for coordinate-like values
    if (lat == null || long == null) {
      if (place is List) {
        // Look for patterns like [null, null, lat, lng] in various indices
        for (int i = 0; i < place.length && i < 250; i++) {
          final item = place[i];
          if (item is List && item.isNotEmpty) {
            // Check if it's a coordinate array [null, null, lat, lng]
            if (item.length >= 4 && item[0] == null && item[1] == null) {
              final potentialLat = item[2];
              final potentialLng = item[3];
              if (potentialLat is num && potentialLng is num) {
                if (lat == null) lat = potentialLat.toDouble();
                if (long == null) long = potentialLng.toDouble();
                break; // Found coordinates, stop searching
              }
            }
            // Check nested arrays
            if (item.length > 0 && item[0] is List) {
              final nested = item[0] as List;
              if (nested.length >= 4 &&
                  nested[0] == null &&
                  nested[1] == null) {
                final potentialLat = nested[2];
                final potentialLng = nested[3];
                if (potentialLat is num && potentialLng is num) {
                  if (lat == null) lat = potentialLat.toDouble();
                  if (long == null) long = potentialLng.toDouble();
                  break;
                }
              }
            }
          }
        }
      }
    }

    return {
      'lat': lat ?? 0.0,
      'long': long ?? 0.0,
    };
  }

  /// Extracts opening hours from place data
  List<Map<String, dynamic>> _getHours(dynamic place) {
    final hoursArray = _safeLookup(place, [203, 0]);
    if (hoursArray == null || hoursArray is! List) {
      return [];
    }

    return hoursArray
        .map((d) {
          if (d is! List || d.isEmpty) return null;

          final day = d[0];
          // Safely convert to string - values might be int or String
          final hoursValue = _safeLookup(d, [3, 0, 0]);
          final hours = hoursValue?.toString();

          final open24HourValue = _safeLookup(d, [3, 0, 1, 0, 0]);
          final open24Hour = open24HourValue?.toString();

          final close24HourValue = _safeLookup(d, [3, 0, 1, 1, 0]);
          final close24Hour = close24HourValue?.toString();

          return {
            'day': day,
            'hours': hours,
            'open24Hour': open24Hour,
            'close24Hour': close24Hour,
          };
        })
        .where((item) => item != null)
        .cast<Map<String, dynamic>>()
        .toList();
  }

  /// Builds results from prepared Google Maps data
  Future<List<Map<String, dynamic>>> _buildGoogleMapsResults(
      List<dynamic> preparedData) async {
    final results = <Map<String, dynamic>>[];

    for (final place in preparedData) {
      if (place == null) continue;
      if (place is! List) continue;

      // Extract fields based on actual Google Maps response structure
      // Place ID is at index 78 (not index 0 - that's a search session ID)
      // Fallback to index 0 if 78 doesn't exist
      String placeId = '';
      if (place.length > 78 && place[78] != null) {
        placeId = place[78].toString();
      } else if (place.length > 0 && place[0] != null) {
        // Fallback to index 0 if 78 doesn't exist
        placeId = place[0].toString();
      }

      // Debug: Log first few place_ids to check for duplicates
      if (results.length < 3) {
        print(
            "DEBUG: Place ${results.length + 1} - place_id: $placeId, name: ${place.length > 11 ? place[11] : 'N/A'}");
      }

      // Address (index 2) - can be a List or String
      String streetAddress = '';
      String city = '';
      String fullAddressStr = '';
      if (place.length > 2) {
        final addressData = place[2];
        if (addressData is List && addressData.isNotEmpty) {
          streetAddress = addressData[0]?.toString() ?? '';
          if (addressData.length > 1) {
            city = addressData[1]?.toString() ?? '';
          }
          fullAddressStr = addressData
              .map((e) => e?.toString() ?? '')
              .where((s) => s.isNotEmpty)
              .join(', ');
        } else if (addressData is String) {
          fullAddressStr = addressData;
          streetAddress = addressData;
        } else if (addressData != null) {
          // Fallback: convert to string
          fullAddressStr = addressData.toString();
          streetAddress = fullAddressStr;
        }
      }

      // Rating and reviews (index 4 is a List: [null, null, price, ..., rating, reviews])
      double? rating;
      int? totalReviews;
      String? priceLevel;
      if (place.length > 4 && place[4] is List) {
        final ratingData = place[4] as List;
        if (ratingData.length > 7) {
          rating = (ratingData[7] as num?)?.toDouble();
        }
        if (ratingData.length > 8) {
          totalReviews = (ratingData[8] as num?)?.toInt();
        }
        if (ratingData.length > 2) {
          priceLevel = ratingData[2]?.toString();
        }
      }

      // Website (index 7 is a List: [url, domain, ...])
      String website = '';
      if (place.length > 7 && place[7] is List) {
        final websiteData = place[7] as List;
        if (websiteData.isNotEmpty) {
          website = websiteData[0]?.toString() ?? '';
        }
      }

      // Name (index 11) - can be String or other types
      String name = 'Unknown';
      if (place.length > 11 && place[11] != null) {
        name = place[11].toString();
      }

      // Types/Categories (index 13)
      List<String> types = [];
      if (place.length > 13 && place[13] is List) {
        types = (place[13] as List<dynamic>)
            .map((t) => t?.toString() ?? '')
            .where((t) => t.isNotEmpty)
            .cast<String>()
            .toList();
      }

      // Coordinates (index 208: [[null, null, lat, lng]])
      final coords = _getLatLong(place);

      // Phone (index 178 is a List: [phone, ...])
      String? phone;
      if (place.length > 178 && place[178] is List) {
        final phoneData = place[178] as List;
        if (phoneData.isNotEmpty) {
          final phoneValue = phoneData[0];
          if (phoneValue is List && phoneValue.isNotEmpty) {
            // Sometimes phone is nested: [[phone_number, ...]]
            phone = phoneValue[0]?.toString();
          } else {
            phone = phoneValue?.toString();
          }
        }
      }

      // Hours
      final hours = _getHours(place);

      // Extract social media links (Instagram, TikTok)
      String? instagramUrl;
      String? tiktokUrl;

      // Helper function to recursively search for social media URLs
      void searchForSocialLinks(dynamic data, int depth) {
        if (depth > 5) return; // Limit depth

        if (data is String) {
          final url = data.trim().toLowerCase();
          // Check for Instagram links
          if (url.contains('instagram.com') &&
              !url.contains('facebook.com/instagram') &&
              instagramUrl == null) {
            // Extract clean Instagram URL
            final pattern =
                RegExp(r'https?://(?:www\.)?instagram\.com/[^\s"<>]+');
            final match = pattern.firstMatch(data);
            if (match != null) {
              instagramUrl = match.group(0);
            }
          }
          // Check for TikTok links
          if (url.contains('tiktok.com') && tiktokUrl == null) {
            // Extract clean TikTok URL
            final pattern = RegExp(
                r'https?://(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/[^\s"<>]+');
            final match = pattern.firstMatch(data);
            if (match != null) {
              tiktokUrl = match.group(0);
            }
          }
        } else if (data is List) {
          for (final item in data) {
            if (instagramUrl != null && tiktokUrl != null) break;
            searchForSocialLinks(item, depth + 1);
          }
        } else if (data is Map) {
          for (final value in data.values) {
            if (instagramUrl != null && tiktokUrl != null) break;
            searchForSocialLinks(value, depth + 1);
          }
        }
      }

      // Search through known indices where URLs might be stored
      // Website is at index 7, social links might be nearby or in other URL fields
      final urlIndices = [
        6,
        7,
        8,
        9,
        10,
        20,
        21,
        22,
        23,
        24,
        25,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40
      ];
      for (final idx in urlIndices) {
        if (idx < place.length && place[idx] != null) {
          searchForSocialLinks(place[idx], 0);
          if (instagramUrl != null && tiktokUrl != null) break;
        }
      }

      // If not found in known indices, do a broader search
      if (instagramUrl == null || tiktokUrl == null) {
        for (int idx = 0; idx < place.length && idx < 250; idx++) {
          if (place[idx] != null) {
            searchForSocialLinks(place[idx], 0);
            if (instagramUrl != null && tiktokUrl != null) break;
          }
        }
      }

      // Also check the website field - sometimes social links are in the main website field
      if (website.isNotEmpty) {
        final websiteLower = website.toLowerCase();
        if (websiteLower.contains('instagram.com') && instagramUrl == null) {
          final pattern =
              RegExp(r'https?://(?:www\.)?instagram\.com/[^\s"<>]+');
          final match = pattern.firstMatch(website);
          if (match != null) {
            instagramUrl = match.group(0);
          }
        }
        if (websiteLower.contains('tiktok.com') && tiktokUrl == null) {
          final pattern =
              RegExp(r'https?://(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/[^\s"<>]+');
          final match = pattern.firstMatch(website);
          if (match != null) {
            tiktokUrl = match.group(0);
          }
        }
      }

      // Build full address if we have components
      if (fullAddressStr.isEmpty && streetAddress.isNotEmpty) {
        fullAddressStr =
            [streetAddress, city].where((s) => s.isNotEmpty).join(', ');
      }
      if (fullAddressStr.isEmpty) {
        fullAddressStr = name; // Fallback to name
      }

      final result = {
        'street_address': streetAddress,
        'city': city,
        'zip': '', // Not directly available in this structure
        'state': '', // Not directly available in this structure
        'country_code': '', // Not directly available in this structure
        'full_address': fullAddressStr,
        'website': website,
        'avg_rating': rating,
        'total_reviews': totalReviews,
        'name': name,
        'tags': types,
        'notes': null, // Can be extracted from other fields if needed
        'place_id': placeId,
        'phone': phone,
        'lat': coords['lat']!,
        'long': coords['long']!,
        'hours': hours,
        'price_level': priceLevel,
        'instagram_url': instagramUrl,
        'tiktok_url': tiktokUrl,
      };

      results.add(result);
    }

    return results;
  }

  /// Fetches places from Google Maps using scraping method
  /// This is an alternative to the official API that doesn't require API keys
  Future<List<Map<String, dynamic>>> _getGoogleMapsScrapedData(
    String query,
    double lat,
    double lon, {
    double zoom = 13499.795714815926,
    int count = 200,
    int start = 0,
    int retries = 0,
  }) async {
    try {
      // Build the complex Google Maps search URL
      final encodedQuery = Uri.encodeComponent(query);
      final url =
          'https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&pb=!4m12!1m3!1d$zoom!2d$lon!3d$lat!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!7i$count!8i$start!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!65m5!3m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q=$encodedQuery&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1';

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'User-Agent':
              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.114 Safari/537.36',
          'Accept': '*/*',
          'Accept-Language': 'en-US,en;q=0.9',
          'Referer': 'https://www.google.com/',
          'Referrer-Policy': 'origin',
        },
      );

      if (response.statusCode == 200) {
        final html = response.body;
        // Remove /*""*/ at the end
        final data = html.length >= 6 && html.endsWith('/*""*/')
            ? html.substring(0, html.length - 6)
            : html;
        final preparedData = _prepareGoogleMapsData(data);
        final results = await _buildGoogleMapsResults(preparedData);
        return results;
      } else {
        print("ERROR: Google Maps scraping returned ${response.statusCode}");
        if (retries < 3) {
          await Future.delayed(Duration(seconds: 2));
          return _getGoogleMapsScrapedData(query, lat, lon,
              zoom: zoom, count: count, start: start, retries: retries + 1);
        }
        return [];
      }
    } catch (e) {
      print("ERROR: Exception in Google Maps scraping: $e");
      if (retries < 3) {
        await Future.delayed(Duration(seconds: 2));
        return _getGoogleMapsScrapedData(query, lat, lon,
            zoom: zoom, count: count, start: start, retries: retries + 1);
      }
      return [];
    }
  }

  /// Transforms Google Maps scraped data to match Google Places format
  Map<String, dynamic> _transformGoogleMapsScrapedToGoogleFormat(
      Map<String, dynamic> place) {
    // Safely extract tags
    List<dynamic> tags = [];
    if (place['tags'] is List) {
      tags = place['tags'] as List;
    }
    final types = tags.map((tag) => tag.toString()).toList();

    // Safely extract coordinates
    double lat = 0.0;
    if (place['lat'] != null) {
      if (place['lat'] is num) {
        lat = (place['lat'] as num).toDouble();
      } else {
        lat = double.tryParse(place['lat'].toString()) ?? 0.0;
      }
    }

    double lng = 0.0;
    if (place['long'] != null) {
      if (place['long'] is num) {
        lng = (place['long'] as num).toDouble();
      } else {
        lng = double.tryParse(place['long'].toString()) ?? 0.0;
      }
    }

    // Safely extract rating
    double? rating;
    if (place['avg_rating'] != null) {
      if (place['avg_rating'] is num) {
        rating = (place['avg_rating'] as num).toDouble();
      } else {
        rating = double.tryParse(place['avg_rating'].toString());
      }
    }

    // Safely extract total reviews
    int? totalReviews;
    if (place['total_reviews'] != null) {
      if (place['total_reviews'] is num) {
        totalReviews = (place['total_reviews'] as num).toInt();
      } else {
        totalReviews = int.tryParse(place['total_reviews'].toString());
      }
    }

    return {
      'place_id': place['place_id']?.toString() ?? '',
      'name': place['name']?.toString() ?? 'Unknown',
      'formatted_address': place['full_address']?.toString() ?? '',
      'vicinity': place['full_address']?.toString() ?? '',
      'geometry': {
        'location': {
          'lat': lat,
          'lng': lng,
        },
      },
      'rating': rating,
      'user_ratings_total': totalReviews,
      'types': types,
      'website': place['website']?.toString(),
      'formatted_phone_number': place['phone']?.toString(),
      'opening_hours': (place['hours'] is List) ? place['hours'] : [],
      'instagram_url': place['instagram_url']?.toString(),
      'tiktok_url': place['tiktok_url']?.toString(),
      'google_maps_scraped': true, // Flag to indicate this is scraped data
    };
  }

  /// Fetches nearby places using Google Maps scraping (no API key required)
  /// This is an alternative to the official API
  /// Makes PARALLEL scraping calls for each keyword group to get more results
  Future<List<dynamic>> fetchNearbyPlacesGoogleMapsScraped(
    double lat,
    double lon, {
    int radius = 500,
    List<String>? additionalKeywords,
  }) async {
    print(
        "DEBUG: Fetching places from Google Maps (scraped): $lat, $lon, radius: $radius");

    // Build keyword groups - each group will be searched separately in parallel
    final List<List<String>> keywordGroups = [
      ['restaurant', 'cafe', 'dessert'], // Base group
    ];

    // Add additional keyword groups based on categories
    if (additionalKeywords != null && additionalKeywords.isNotEmpty) {
      // Group related keywords together for better results
      final List<String> museumsParks = [];
      final List<String> shopping = [];
      final List<String> bars = [];

      for (final keyword in additionalKeywords) {
        if (keyword.contains('museum') ||
            keyword.contains('art_gallery') ||
            keyword.contains('park')) {
          museumsParks.add(keyword);
        } else if (keyword.contains('shopping') || keyword.contains('store')) {
          shopping.add(keyword);
        } else if (keyword.contains('bar') || keyword.contains('night_club')) {
          bars.add(keyword);
        } else {
          // Add other keywords to base group
          keywordGroups[0].add(keyword);
        }
      }

      if (museumsParks.isNotEmpty) {
        keywordGroups.add(museumsParks);
      }
      if (shopping.isNotEmpty) {
        keywordGroups.add(shopping);
      }
      if (bars.isNotEmpty) {
        keywordGroups.add(bars);
      }
    }

    print(
        "DEBUG: Using ${keywordGroups.length} keyword groups in PARALLEL: ${keywordGroups.map((g) => g.join(' ')).toList()}");

    // Calculate zoom level based on radius (approximate)
    // Larger radius = smaller zoom number
    double zoom = 13499.795714815926; // Default zoom
    if (radius <= 500) {
      zoom = 2000;
    } else if (radius <= 1000) {
      zoom = 4000;
    } else if (radius <= 2000) {
      zoom = 10000;
    } else if (radius <= 5000) {
      zoom = 35000;
    } else {
      zoom = 70000;
    }

    try {
      // Make PARALLEL scraping calls for each keyword group
      final List<Future<List<Map<String, dynamic>>>> scrapingFutures =
          keywordGroups.map((keywordGroup) async {
        try {
          final query = keywordGroup.join(' ');
          print("DEBUG: Scraping with query: $query");

          final scrapedResults = await _getGoogleMapsScrapedData(
            query,
            lat,
            lon,
            zoom: zoom,
            count: 200,
            start: 0,
          );

          print(
              "DEBUG: Query '$query' returned ${scrapedResults.length} places");
          return scrapedResults;
        } catch (e) {
          print(
              "ERROR: Exception while scraping for ${keywordGroup.join(' ')}: $e");
          return <Map<String, dynamic>>[];
        }
      }).toList();

      // Wait for all scraping calls to complete in parallel
      print(
          "DEBUG: Waiting for all ${scrapingFutures.length} parallel scraping calls to complete...");
      final List<List<Map<String, dynamic>>> allScrapedResults =
          await Future.wait(scrapingFutures);

      // Flatten all results into a single list
      final List<Map<String, dynamic>> scrapedResults =
          allScrapedResults.expand((list) => list).toList();

      print(
          "DEBUG: Google Maps scraping returned ${scrapedResults.length} total places (before deduplication)");

      // Transform to Google Places format
      final transformedPlaces = scrapedResults.map((place) {
        return _transformGoogleMapsScrapedToGoogleFormat(place);
      }).toList();

      print("DEBUG: Transformed ${transformedPlaces.length} places");

      // Deduplicate by place_id
      final Map<String, dynamic> uniqueResults = {};
      int validPlaces = 0;
      int invalidPlaces = 0;
      int missingPlaceId = 0;
      int invalidCoords = 0;

      for (final place in transformedPlaces) {
        final placeId = place['place_id']?.toString();
        if (placeId != null && placeId.isNotEmpty) {
          // Validate that place has required fields
          final geometry = place['geometry'];
          final location = geometry?['location'];
          final lat = location?['lat'];
          final lng = location?['lng'];

          if (lat != null && lng != null && lat != 0.0 && lng != 0.0) {
            // Check if place_id already exists - if so, use coordinates+name as unique key
            if (uniqueResults.containsKey(placeId)) {
              // Duplicate place_id detected - use coordinates+name as fallback key
              final coordKey =
                  '${lat.toStringAsFixed(6)},${lng.toStringAsFixed(6)}';
              final name = place['name']?.toString() ?? '';
              final uniqueKey = '$placeId-$coordKey-$name';
              uniqueResults[uniqueKey] = place;
              validPlaces++;
            } else {
              uniqueResults[placeId] = place;
              validPlaces++;
            }
          } else {
            invalidPlaces++;
            invalidCoords++;
            // Only print first few invalid places to avoid spam
            if (invalidCoords <= 3) {
              print(
                  "DEBUG: Skipping place ${place['name']} - invalid coordinates: lat=$lat, lng=$lng");
            }
          }
        } else {
          invalidPlaces++;
          missingPlaceId++;
          // Only print first few missing place_ids to avoid spam
          if (missingPlaceId <= 3) {
            print("DEBUG: Skipping place ${place['name']} - missing place_id");
          }
        }
      }

      print(
          "DEBUG: Valid places: $validPlaces, Invalid places: $invalidPlaces (missing place_id: $missingPlaceId, invalid coords: $invalidCoords)");

      // Debug: Check for duplicate place_ids
      if (validPlaces > uniqueResults.length) {
        print(
            "WARNING: Found ${validPlaces - uniqueResults.length} places with duplicate place_ids!");
        // Show sample of place_ids to debug
        final samplePlaceIds = transformedPlaces
            .take(5)
            .map((p) => p['place_id']?.toString())
            .toList();
        print("DEBUG: Sample place_ids: $samplePlaceIds");
      }

      print("DEBUG: Returning ${uniqueResults.length} unique valid places");

      if (validPlaces < 5) {
        print(
            "WARNING: Very few valid places found. Coordinate extraction may need improvement.");
      }

      return uniqueResults.values.toList();
    } catch (e) {
      print("ERROR: Exception fetching Google Maps scraped places: $e");
      return [];
    }
  }

  /// Unified method: Uses Google Maps scraping only
  Future<List<dynamic>> fetchNearbyPlacesUnified(
    double lat,
    double lon, {
    int radius = 500,
    List<String>? additionalKeywords,
    bool fetchDetailedPhotos = false,
    bool useGoogleMapsScraping = true, // Always true now
  }) async {
    print("DEBUG: Using Google Maps scraping...");
    return fetchNearbyPlacesGoogleMapsScraped(
      lat,
      lon,
      radius: radius,
      additionalKeywords: additionalKeywords,
    );
  }

  // ============================================================================
  // Public Itinerary Sharing API Methods
  // ============================================================================

  Future<Map<String, dynamic>> createItinerarySkeleton({
    required String destination,
    required DateTime startDate,
    required DateTime endDate,
    required String groupSize,
    required List<String> vibes,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/itineraries/create-skeleton/');

      final Map<String, dynamic> requestBody = {
        'destination': destination,
        'start_date':
            startDate.toIso8601String().substring(0, 10), // YYYY-MM-DD
        'end_date': endDate.toIso8601String().substring(0, 10), // YYYY-MM-DD
        'group_size': groupSize,
        'vibes': vibes,
      };

      print('DEBUG: Calling createItinerarySkeleton endpoint: $url');
      print('DEBUG: Request body: $requestBody');

      // Don't send auth - backend allows anonymous access
      final response = await http
          .post(
        url,
        headers: {
          'Content-Type': 'application/json',
        },
        body: json.encode(requestBody),
      )
          .timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw TimeoutException(
              'Create itinerary skeleton request timed out after 30 seconds');
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final result = json.decode(response.body) as Map<String, dynamic>;
        print('DEBUG: Create itinerary skeleton response: $result');
        return result;
      } else {
        print(
            'ERROR: Failed to create itinerary skeleton: ${response.statusCode}');
        print('Response: ${response.body}');
        final errorBody = json.decode(response.body);
        throw Exception(
            errorBody['error'] ?? 'Failed to create itinerary skeleton');
      }
    } catch (e) {
      print('ERROR: Exception creating itinerary skeleton: $e');
      rethrow;
    }
  }

  /// Save a complete itinerary to Supabase
  Future<void> saveItinerary(Map<String, dynamic> itineraryData) async {
    try {
      if (supabaseAnonKey.isEmpty) {
        throw Exception('Supabase key not configured');
      }

      final uri = Uri.parse('$supabaseUrl/itineraries');

      final resp = await http.post(
        uri,
        headers: {
          'apikey': supabaseAnonKey,
          'Authorization': 'Bearer $supabaseAnonKey',
          'Content-Type': 'application/json',
          'Prefer': 'return=minimal',
        },
        body: json.encode(itineraryData),
      );

      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        print('DEBUG: Itinerary saved successfully');
        return;
      } else {
        throw Exception(
            'Failed to save itinerary: ${resp.statusCode} - ${resp.body}');
      }
    } catch (e) {
      print('ERROR: Exception saving itinerary: $e');
      rethrow;
    }
  }

  /// Submit an itinerary to the public feed
  Future<Map<String, dynamic>?> submitPublicItinerary({
    required String userId,
    required String userName,
    String? userPhotoUrl,
    required String title,
    required String description,
    required String location,
    required double latitude,
    required double longitude,
    required String neighborhood,
    required List<String> categories,
    required List<dynamic> items,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/submit-itinerary/');

      // Prepare request body
      final requestBody = {
        'user_id': userId,
        'user_name': userName,
        'user_photo_url': userPhotoUrl,
        'title': title,
        'description': description,
        'location': location,
        'latitude': latitude,
        'longitude': longitude,
        'neighborhood': neighborhood,
        'categories': categories,
        'items': items,
      };

      print('DEBUG: Submitting itinerary with ${items.length} items');
      print(
          'DEBUG: Request body size: ${json.encode(requestBody).length} bytes');

      final response = await http
          .post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
        },
        body: json.encode(requestBody),
      )
          .timeout(
        const Duration(seconds: 60),
        onTimeout: () {
          throw Exception('Request timeout after 60 seconds');
        },
      );

      if (response.statusCode == 201) {
        return json.decode(response.body);
      } else {
        print('ERROR: Failed to submit itinerary: ${response.statusCode}');
        print('Response: ${response.body}');
        try {
          final errorData = json.decode(utf8.decode(response.bodyBytes));
          throw Exception(errorData['error'] ?? 'Failed to submit itinerary');
        } catch (_) {
          throw Exception('Failed to submit itinerary: ${response.statusCode}');
        }
      }
    } catch (e) {
      print('ERROR: Exception submitting itinerary: $e');
      rethrow;
    }
  }

  /// Save an itinerary to the user's saved_lists
  Future<Map<String, dynamic>?> saveItineraryToUserList({
    required String userId,
    required String title,
    String? subtitle,
    String? description,
    required Map<String, dynamic> itineraryData,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/save-itinerary/');

      final requestBody = {
        'user_id': userId,
        'title': title,
        'subtitle': subtitle ?? '',
        'description': description ?? '',
        'itinerary_data': itineraryData,
      };

      final response = await http
          .post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      )
          .timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw Exception('Request timeout after 30 seconds');
        },
      );

      if (response.statusCode == 201) {
        return json.decode(utf8.decode(response.bodyBytes));
      } else {
        print('ERROR: Failed to save itinerary: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception saving itinerary: $e');
      return null;
    }
  }

  /// Get all saved itineraries for a user
  Future<List<Map<String, dynamic>>> getSavedItineraries(String userId) async {
    try {
      final url = Uri.parse('$baseUrl/api/saved-itineraries/?user_id=$userId');

      final response = await http.get(url).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw Exception('Request timeout after 30 seconds');
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        final List<dynamic> itineraries = data['itineraries'] ?? [];
        return List<Map<String, dynamic>>.from(itineraries);
      } else {
        print('ERROR: Failed to get saved itineraries: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('ERROR: Exception getting saved itineraries: $e');
      return [];
    }
  }

  /// Get public itineraries with optional filtering
  Future<Map<String, dynamic>?> getPublicItineraries({
    String? location,
    List<String>? categories,
    String sort = 'recent', // 'likes' or 'recent'
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, String>{
        'sort': sort,
        'limit': limit.toString(),
        'offset': offset.toString(),
      };
      if (location != null && location.isNotEmpty) {
        queryParams['location'] = location;
      }
      if (categories != null && categories.isNotEmpty) {
        queryParams['categories'] = categories.join(',');
      }

      final url = Uri.parse('$baseUrl/api/public-itineraries/')
          .replace(queryParameters: queryParams);
      final response = await http.get(url);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print(
            'ERROR: Failed to fetch public itineraries: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception fetching public itineraries: $e');
      return null;
    }
  }

  /// Toggle like on a public itinerary
  Future<Map<String, dynamic>?> likePublicItinerary({
    required String itineraryId,
    required String userId,
  }) async {
    try {
      final url =
          Uri.parse('$baseUrl/api/public-itineraries/$itineraryId/like/');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('ERROR: Failed to like itinerary: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception liking itinerary: $e');
      return null;
    }
  }

  /// Check if user has liked an itinerary
  Future<bool> hasLikedItinerary({
    required String itineraryId,
    required String userId,
  }) async {
    try {
      final likesRef = FirebaseFirestore.instance
          .collection('public_itineraries')
          .doc(itineraryId)
          .collection('likes')
          .doc(userId);
      final doc = await likesRef.get().timeout(const Duration(seconds: 15),
          onTimeout: () {
        print('WARNING: Like status query timed out');
        throw TimeoutException('Like status query timed out');
      });
      return doc.exists;
    } on TimeoutException {
      print('ERROR: Like status query timed out');
      return false;
    } catch (e) {
      print('ERROR: Exception checking like status: $e');
      return false;
    }
  }

  /// Add a public itinerary to user's schedule
  Future<Map<String, dynamic>?> addPublicItineraryToSchedule({
    required String itineraryId,
    required String userId,
  }) async {
    try {
      final url = Uri.parse(
          '$baseUrl/api/public-itineraries/$itineraryId/add-to-schedule/');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print(
            'ERROR: Failed to add itinerary to schedule: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception adding itinerary to schedule: $e');
      return null;
    }
  }

  /// Share a public itinerary (increments share count)
  Future<Map<String, dynamic>?> sharePublicItinerary({
    required String itineraryId,
  }) async {
    try {
      final url =
          Uri.parse('$baseUrl/api/public-itineraries/$itineraryId/share/');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('ERROR: Failed to share itinerary: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception sharing itinerary: $e');
      return null;
    }
  }

  /// Update a user's own public itinerary
  Future<Map<String, dynamic>?> updatePublicItinerary({
    required String itineraryId,
    required String userId,
    String? title,
    String? description,
    List<dynamic>? items,
    List<String>? categories,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/public-itineraries/$itineraryId/');
      final body = <String, dynamic>{'user_id': userId};
      if (title != null) body['title'] = title;
      if (description != null) body['description'] = description;
      if (items != null) body['items'] = items;
      if (categories != null) body['categories'] = categories;

      final response = await http.put(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('ERROR: Failed to update itinerary: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception updating itinerary: $e');
      return null;
    }
  }

  /// Delete a user's own public itinerary
  Future<bool> deletePublicItinerary({
    required String itineraryId,
    required String userId,
  }) async {
    try {
      final url =
          Uri.parse('$baseUrl/api/public-itineraries/$itineraryId/delete/');
      final response = await http.delete(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        print('ERROR: Failed to delete itinerary: ${response.statusCode}');
        print('Response: ${response.body}');
        return false;
      }
    } catch (e) {
      print('ERROR: Exception deleting itinerary: $e');
      return false;
    }
  }

  /// Get user statistics
  Future<Map<String, dynamic>?> getUserStats({
    required String userId,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/user-stats/$userId/');
      final response = await http.get(url);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('ERROR: Failed to fetch user stats: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception fetching user stats: $e');
      return null;
    }
  }

  /// Get Next Best Action (NBA) recommendation for real-time suggestions.
  /// Returns only the next 2 steps instead of full itinerary.
  Future<Map<String, dynamic>?> getNextBestAction({
    required double latitude,
    required double longitude,
    double? heading, // degrees (0-360, North=0)
    DateTime? timestamp,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/api/next-best-action/');

      final requestBody = {
        'latitude': latitude,
        'longitude': longitude,
        if (heading != null) 'heading': heading,
        if (timestamp != null) 'timestamp': timestamp.toIso8601String(),
      };

      print('DEBUG: Calling NBA endpoint: $url');
      print('DEBUG: Request body: $requestBody');

      final response = await http
          .post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
        },
        body: json.encode(requestBody),
      )
          .timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw TimeoutException('NBA request timed out after 30 seconds');
        },
      );

      if (response.statusCode == 200) {
        final result = json.decode(response.body);
        print(
            'DEBUG: NBA response: ${result['context']}, cache_hit: ${result['cache_hit']}, response_time_ms: ${result['response_time_ms']}');
        return result;
      } else {
        print('ERROR: Failed to get NBA: ${response.statusCode}');
        print('Response: ${response.body}');
        return null;
      }
    } catch (e) {
      print('ERROR: Exception getting NBA: $e');
      return null;
    }
  }

  /// Calculate bearing (heading) from two coordinates.
  /// Returns bearing in degrees (0-360, where 0 = North, 90 = East).
  static double calculateBearing(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    final lat1Rad = lat1 * pi / 180;
    final lat2Rad = lat2 * pi / 180;
    final deltaLon = (lon2 - lon1) * pi / 180;

    final y = sin(deltaLon) * cos(lat2Rad);
    final x = cos(lat1Rad) * sin(lat2Rad) -
        sin(lat1Rad) * cos(lat2Rad) * cos(deltaLon);

    final bearing = atan2(y, x);
    final bearingDegrees = bearing * 180 / pi;

    // Normalize to 0-360
    return (bearingDegrees + 360) % 360;
  }

  // ============================================
  // PLANDIT REAL-TIME ITINERARY GENERATION
  // ============================================

  /// Parse natural language query using LLM
  Future<Map<String, dynamic>> parseQuery(
    String query, {
    Map<String, double>? userLocation,
  }) async {
    try {
      final Uri url = Uri.parse('$baseUrl/api/parse-query/');

      final Map<String, dynamic> requestBody = {
        'query': query,
      };

      if (userLocation != null) {
        requestBody['user_location'] = {
          'lat': userLocation['lat'],
          'lng': userLocation['lng'],
        };
      }

      print('DEBUG: Parsing query: "$query"');

      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: json.encode(requestBody),
          )
          .timeout(
            const Duration(seconds: 15),
            onTimeout: () => throw TimeoutException('Query parsing timeout'),
          );

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes))
            as Map<String, dynamic>;
        print('DEBUG: Query parsed successfully');
        return data;
      } else {
        final errorBody = json.decode(utf8.decode(response.bodyBytes));
        throw Exception(errorBody['error'] ?? 'Failed to parse query');
      }
    } catch (e) {
      print('ERROR: Exception parsing query: $e');
      rethrow;
    }
  }

  /// Generate itinerary with structured parameters
  /// Unified itinerary generation
  Future<Map<String, dynamic>> generateItinerary({
    double? startLat,
    double? startLong,
    String? selectedVibe,
    String? socialContext,
    String? query,
    Map<String, double>? userLocation,
    int radiusMeters = 3000,
    String? localTimeStart,
    List<String>? excludePlaceIds,
    List<String>? cuisinePreferences,
  }) async {
    try {
      final Uri url = Uri.parse('$baseUrl/api/generate-itinerary/');

      // Get user ID from Firebase Auth if available
      String? userId;
      try {
        final firebaseAuth = FirebaseAuth.instance;
        userId = firebaseAuth.currentUser?.uid;
      } catch (e) {
        print('DEBUG: Could not get Firebase user ID: $e');
      }

      final Map<String, dynamic> requestBody = {
        if (startLat != null) 'start_lat': startLat,
        if (startLong != null) 'start_long': startLong,
        if (selectedVibe != null) 'selected_vibe': selectedVibe,
        if (socialContext != null) 'social_context': socialContext,
        if (query != null) 'query': query,
        if (userLocation != null) 'user_location': userLocation,
        'radius_meters': radiusMeters,
        if (localTimeStart != null) 'local_time_start': localTimeStart,
        'exclude_place_ids': excludePlaceIds ?? [],
        'cuisine_preferences': cuisinePreferences ?? [],
        if (userId != null) 'user_id': userId,
      };

      print(
          'DEBUG: Unified Request to /api/generate-itinerary/ with query="$query"');

      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: json.encode(requestBody),
          )
          .timeout(
            const Duration(seconds: 40), // Increased timeout for unified call
            onTimeout: () =>
                throw TimeoutException('Itinerary generation timeout'),
          );

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes))
            as Map<String, dynamic>;
        print('DEBUG: Itinerary generated successfully (Unified)');
        return data;
      } else {
        final errorBody = json.decode(utf8.decode(response.bodyBytes));
        throw Exception(errorBody['error'] ?? 'Failed to generate itinerary');
      }
    } catch (e) {
      print('ERROR: Exception in unified generateItinerary: $e');
      rethrow;
    }
  }

  /// Convenience method: now just calls unified generateItinerary
  Future<Map<String, dynamic>> generateItineraryFromQuery(
    String query, {
    Map<String, double>? userLocation,
    List<String>? excludePlaceIds,
    Map<String, dynamic>? filters,
    double? lat,
    double? lng,
  }) async {
    // Single unified call
    return generateItinerary(
      query: query,
      userLocation: userLocation,
      excludePlaceIds: excludePlaceIds,
      // Pass explicit filters directly, giving precedence to lat/lng
      startLat: lat ?? filters?['latitude'],
      startLong: lng ?? filters?['longitude'],
      selectedVibe: filters?['vibe'],
      socialContext: filters?['socialContext']?.toString().toLowerCase(),
      localTimeStart: filters?['timeOfDay'],
      cuisinePreferences: (filters?['cuisines'] as List?)?.cast<String>(),
    );
  }
}
