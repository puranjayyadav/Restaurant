import 'package:flutter/material.dart';
import 'package:location/location.dart' as loc;
import 'package:url_launcher/url_launcher.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'api_service.dart';
import 'dart:math' show min;

class DiscoveryRadarScreen extends StatefulWidget {
  const DiscoveryRadarScreen({super.key});

  @override
  _DiscoveryRadarScreenState createState() => _DiscoveryRadarScreenState();
}

class _DiscoveryRadarScreenState extends State<DiscoveryRadarScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> _recommendations = [];
  bool _isLoading = true;
  String? _error;
  loc.LocationData? _currentLocation;

  @override
  void initState() {
    super.initState();
    _getCurrentLocation();
  }

  Future<void> _getCurrentLocation() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });

      final locationService = loc.Location();

      // Check if location service is enabled
      bool serviceEnabled = await locationService.serviceEnabled();
      if (!serviceEnabled) {
        serviceEnabled = await locationService.requestService();
        if (!serviceEnabled) {
          setState(() {
            _error = 'Location services are disabled';
            _isLoading = false;
          });
          return;
        }
      }

      // Check if permission is granted
      loc.PermissionStatus permissionStatus =
          await locationService.hasPermission();
      if (permissionStatus == loc.PermissionStatus.denied) {
        permissionStatus = await locationService.requestPermission();
        if (permissionStatus != loc.PermissionStatus.granted) {
          setState(() {
            _error = 'Location permission denied';
            _isLoading = false;
          });
          return;
        }
      }

      // Get location
      _currentLocation = await locationService.getLocation();
      await _loadRecommendations();
    } catch (e) {
      setState(() {
        _error = 'Failed to get location: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _loadRecommendations() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });

      if (_currentLocation == null) {
        print("DEBUG: Current location is null, attempting to get it");
        await _getCurrentLocation();
        return;
      }

      print(
          "DEBUG: Fetching recommendations with location: ${_currentLocation!.latitude}, ${_currentLocation!.longitude}");

      List<dynamic> recommendations = [];
      String errorMessage = '';

      // For testing purposes, use mock data directly when we have repeated results issues
      recommendations = _generateDiverseMockRestaurants();
      print(
          "DEBUG: Using diverse mock data with ${recommendations.length} restaurants");

      // Update the state with whatever data we have (might be empty)
      setState(() {
        _recommendations = recommendations;
        _isLoading = false;
        _error = errorMessage.isEmpty ? null : errorMessage;
      });

      // Debug which places are being shown
      if (_recommendations.isNotEmpty) {
        print("DEBUG: Showing these restaurants:");
        for (int i = 0; i < min(_recommendations.length, 10); i++) {
          print(" ${i + 1}. ${_recommendations[i]['name']}");
        }
      } else {
        print("DEBUG: No recommendations to show");
      }
    } catch (e, stackTrace) {
      print("DEBUG: Error loading recommendations: $e");
      print("DEBUG: Stack trace: $stackTrace");
      setState(() {
        _error =
            'Failed to load recommendations: ${e.toString().substring(0, min(100, e.toString().length))}';
        _isLoading = false;
      });
    }
  }

  // Generate diverse mock data for testing
  List<Map<String, dynamic>> _generateDiverseMockRestaurants() {
    final List<Map<String, dynamic>> restaurants = [
      {
        'id': '1',
        'name': 'Taste of Italy',
        'address': '123 Main St, New York, NY',
        'price_range': '\$\$\$',
        'dining_style': 'FINE',
        'dining_style_display': 'Fine Dining',
        'is_preferred': true,
        'distance_km': 1.2,
        'rating': 4.5,
        'preference_score': 85.0,
        'features': [
          {
            'feature_type': 'OUTDOOR',
            'feature_type_display': 'Outdoor Seating'
          },
          {'feature_type': 'VEGAN', 'feature_type_display': 'Vegan-friendly'}
        ]
      },
      {
        'id': '2',
        'name': 'Burger Palace',
        'address': '456 Oak Ave, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': false,
        'distance_km': 0.8,
        'rating': 4.0,
        'preference_score': 75.0,
        'features': [
          {'feature_type': 'TAKEOUT', 'feature_type_display': 'Takeout'},
          {'feature_type': 'FAMILY', 'feature_type_display': 'Family-friendly'}
        ]
      },
      {
        'id': '3',
        'name': 'Sushi Heaven',
        'address': '789 Pine St, New York, NY',
        'price_range': '\$\$\$\$',
        'dining_style': 'FINE',
        'dining_style_display': 'Fine Dining',
        'is_preferred': true,
        'distance_km': 1.5,
        'rating': 4.8,
        'preference_score': 90.0,
        'features': [
          {'feature_type': 'VEGAN', 'feature_type_display': 'Vegan-friendly'},
          {'feature_type': 'HALAL', 'feature_type_display': 'Halal'}
        ]
      },
      {
        'id': '4',
        'name': 'Taco Fiesta',
        'address': '300 Broadway, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': false,
        'distance_km': 2.1,
        'rating': 4.2,
        'preference_score': 70.0,
        'features': [
          {'feature_type': 'TAKEOUT', 'feature_type_display': 'Takeout'},
          {'feature_type': 'SPICY', 'feature_type_display': 'Spicy Food'}
        ]
      },
      {
        'id': '5',
        'name': 'Pho Delight',
        'address': '450 Canal St, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': false,
        'distance_km': 1.7,
        'rating': 4.3,
        'preference_score': 72.0,
        'features': [
          {'feature_type': 'TAKEOUT', 'feature_type_display': 'Takeout'},
          {'feature_type': 'VEGAN', 'feature_type_display': 'Vegan-friendly'}
        ]
      },
      {
        'id': '6',
        'name': 'Indian Spice Kitchen',
        'address': '555 5th Ave, New York, NY',
        'price_range': '\$\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': true,
        'distance_km': 3.0,
        'rating': 4.6,
        'preference_score': 88.0,
        'features': [
          {'feature_type': 'SPICY', 'feature_type_display': 'Spicy Food'},
          {'feature_type': 'VEGAN', 'feature_type_display': 'Vegan-friendly'}
        ]
      },
      {
        'id': '7',
        'name': 'Mama\'s Pizza',
        'address': '123 Mulberry St, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': false,
        'distance_km': 0.5,
        'rating': 4.4,
        'preference_score': 78.0,
        'features': [
          {'feature_type': 'TAKEOUT', 'feature_type_display': 'Takeout'},
          {'feature_type': 'FAMILY', 'feature_type_display': 'Family-friendly'}
        ]
      },
      {
        'id': '8',
        'name': 'Coffee & Books',
        'address': '555 Broadway, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CAFE',
        'dining_style_display': 'Cafe',
        'is_preferred': true,
        'distance_km': 1.9,
        'rating': 4.7,
        'preference_score': 86.0,
        'features': [
          {'feature_type': 'COFFEE', 'feature_type_display': 'Coffee'},
          {'feature_type': 'WIFI', 'feature_type_display': 'Free WiFi'}
        ]
      },
      {
        'id': '9',
        'name': 'Mediterranean Delights',
        'address': '678 9th Ave, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': false,
        'distance_km': 2.5,
        'rating': 4.2,
        'preference_score': 73.0,
        'features': [
          {
            'feature_type': 'HEALTHY',
            'feature_type_display': 'Healthy Options'
          },
          {'feature_type': 'VEGAN', 'feature_type_display': 'Vegan-friendly'}
        ]
      },
      {
        'id': '10',
        'name': 'Steakhouse Prime',
        'address': '890 Park Ave, New York, NY',
        'price_range': '\$\$\$\$',
        'dining_style': 'FINE',
        'dining_style_display': 'Fine Dining',
        'is_preferred': false,
        'distance_km': 3.2,
        'rating': 4.9,
        'preference_score': 82.0,
        'features': [
          {'feature_type': 'UPSCALE', 'feature_type_display': 'Upscale'},
          {'feature_type': 'ALCOHOL', 'feature_type_display': 'Full Bar'}
        ]
      },
      {
        'id': '11',
        'name': 'Ramen House',
        'address': '111 E 31st St, New York, NY',
        'price_range': '\$\$',
        'dining_style': 'CASUAL',
        'dining_style_display': 'Casual Dining',
        'is_preferred': true,
        'distance_km': 1.3,
        'rating': 4.5,
        'preference_score': 84.0,
        'features': [
          {'feature_type': 'TAKEOUT', 'feature_type_display': 'Takeout'},
          {'feature_type': 'LATE', 'feature_type_display': 'Late Night'}
        ]
      },
      {
        'id': '12',
        'name': 'Vegan Paradise',
        'address': '333 W 4th St, New York, NY',
        'price_range': '\$\$\$',
        'dining_style': 'MODERN',
        'dining_style_display': 'Modern',
        'is_preferred': true,
        'distance_km': 2.0,
        'rating': 4.7,
        'preference_score': 89.0,
        'features': [
          {'feature_type': 'VEGAN', 'feature_type_display': 'Vegan-friendly'},
          {'feature_type': 'ORGANIC', 'feature_type_display': 'Organic'}
        ]
      }
    ];

    // Ensure new results order each time
    restaurants.shuffle();

    return restaurants;
  }

  void _openMaps(String name, String address) async {
    final query = Uri.encodeComponent('$name, $address');
    final url = Uri.parse('https://www.openstreetmap.org/search?query=$query');

    try {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open maps for $name')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Discovery Radar'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadRecommendations,
            tooltip: 'Refresh recommendations',
          ),
        ],
      ),
      body: Stack(
        children: [
          _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(_error!,
                              style: const TextStyle(color: Colors.red)),
                          const SizedBox(height: 20),
                          ShadButton(
                            onPressed: _loadRecommendations,
                            child: const Text('Try Again'),
                          ),
                        ],
                      ),
                    )
                  : _recommendations.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Text(
                                  'No personalized recommendations available'),
                              const SizedBox(height: 10),
                              Text('Debug info:',
                                  style:
                                      TextStyle(fontWeight: FontWeight.bold)),
                              Text(
                                  'Location: ${_currentLocation?.latitude ?? "null"}, ${_currentLocation?.longitude ?? "null"}'),
                              Text('API called: ${_isLoading ? "No" : "Yes"}'),
                              Text('Error: ${_error ?? "None"}'),
                              const SizedBox(height: 20),
                              ShadButton(
                                onPressed: _loadRecommendations,
                                child: const Text('Refresh'),
                              ),
                            ],
                          ),
                        )
                      : _buildRecommendationsList(),
          // Debug button overlay
          Positioned(
            bottom: 20,
            right: 20,
            child: FloatingActionButton(
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: Text('Debug Information'),
                    content: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('Recommendations: ${_recommendations.length}'),
                          Text(
                              'First recommendation: ${_recommendations.isNotEmpty ? _recommendations[0]['name'] : "None"}'),
                          Text('Loading: $_isLoading'),
                          Text('Error: ${_error ?? "None"}'),
                          Text(
                              'Location: ${_currentLocation?.latitude}, ${_currentLocation?.longitude}'),
                          const Divider(),
                          if (_recommendations.isNotEmpty) ...[
                            Text('Data sample:',
                                style: TextStyle(fontWeight: FontWeight.bold)),
                            Text(_recommendations[0].toString(),
                                style: TextStyle(fontSize: 12)),
                          ]
                        ],
                      ),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: Text('Close'),
                      ),
                      TextButton(
                        onPressed: () {
                          Navigator.of(context).pop();
                          _loadRecommendations();
                        },
                        child: Text('Refresh Data'),
                      ),
                    ],
                  ),
                );
              },
              backgroundColor: Colors.red,
              child: Icon(Icons.bug_report),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRecommendationsList() {
    return RefreshIndicator(
      onRefresh: _loadRecommendations,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _recommendations.length,
        itemBuilder: (context, index) {
          final recommendation = _recommendations[index];
          return _buildRecommendationCard(recommendation);
        },
      ),
    );
  }

  Widget _buildRecommendationCard(dynamic recommendation) {
    final String name = recommendation['name'] ?? 'Unknown Restaurant';
    final String address = recommendation['address'] ?? 'Address not available';
    final String priceRange = recommendation['price_range'] ?? '';
    final String diningStyle = recommendation['dining_style_display'] ?? '';
    final bool isPreferred = recommendation['is_preferred'] ?? false;
    final double? preferenceScore = recommendation['preference_score'] is num
        ? (recommendation['preference_score'] as num).toDouble()
        : null;
    final double? distanceKm = recommendation['distance_km'] is num
        ? (recommendation['distance_km'] as num).toDouble()
        : null;

    // Get features if available
    List<dynamic> features = [];
    if (recommendation.containsKey('features')) {
      features = recommendation['features'] as List<dynamic>;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: ShadCard(
        child: Stack(
          children: [
          // Recommendation card content
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        name,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Text(
                      priceRange,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        address,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ),
                    if (distanceKm != null)
                      Text(
                        '${distanceKm.toStringAsFixed(1)} km',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                if (diningStyle.isNotEmpty)
                  Text(
                    'Dining Style: $diningStyle',
                    style: const TextStyle(fontSize: 14),
                  ),
                if (features.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  const Text(
                    'Features:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 8,
                    children: features
                        .map((feature) => Chip(
                              label: Text(
                                feature['feature_type_display'] ??
                                    feature['feature_type'] ??
                                    '',
                                style: const TextStyle(fontSize: 12),
                              ),
                              backgroundColor: Colors.blue.shade100,
                            ))
                        .toList(),
                  ),
                ],
                if (preferenceScore != null) ...[
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: preferenceScore /
                        200.0, // Normalize to 0-1 range (max score is ~200)
                    backgroundColor: Colors.grey[200],
                    valueColor: AlwaysStoppedAnimation<Color>(
                      isPreferred ? Colors.pink : Colors.blue,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isPreferred
                        ? 'Matches your taste profile!'
                        : 'Recommended based on your preferences',
                    style: TextStyle(
                      fontSize: 12,
                      color: isPreferred ? Colors.pink : Colors.blue[700],
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () {
                        final String? id = recommendation['id']?.toString();
                        if (id != null) {
                          _apiService.recordInteraction(
                            establishmentId: id,
                            interactionType: 'SAVE',
                          );
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                                content: Text('Restaurant saved to favorites')),
                          );
                        }
                      },
                      icon: const Icon(Icons.favorite),
                      label: const Text('Save'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.pink,
                        foregroundColor: Colors.white,
                      ),
                    ),
                    ShadButton(
                      onPressed: () => _openMaps(name, address),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.map, size: 18),
                          SizedBox(width: 8),
                          Text('View on Map'),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Taste match badge
          if (isPreferred)
            Positioned(
              top: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.pink,
                  borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(8),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.thumb_up, color: Colors.white, size: 12),
                    SizedBox(width: 4),
                    Text(
                      'Taste Match',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
      ),
    );
  }
}
