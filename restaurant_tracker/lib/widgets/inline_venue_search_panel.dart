import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:async';
import 'dart:convert';
import '../api_service.dart';

// Primary green color used throughout the app
const Color _primaryGreen = Color(0xFF2D5016);

Future<http.Response> makeAuthenticatedRequest({
  required String url,
  String method = 'GET',
  Map<String, String>? headers,
  String? body,
}) async {
  final User? currentUser = FirebaseAuth.instance.currentUser;
  if (currentUser == null) {
    throw Exception('User not logged in');
  }

  final String? idToken = await currentUser.getIdToken();
  if (idToken == null) {
    throw Exception('Failed to get ID token');
  }

  final requestHeaders = {
    'Authorization': 'Bearer $idToken',
    'Content-Type': 'application/json',
    ...?headers,
  };

  switch (method.toUpperCase()) {
    case 'GET':
      return await http.get(Uri.parse(url), headers: requestHeaders);
    case 'POST':
      return await http.post(
        Uri.parse(url),
        headers: requestHeaders,
        body: body,
      );
    case 'DELETE':
      return await http.delete(Uri.parse(url), headers: requestHeaders);
    default:
      throw Exception('Unsupported HTTP method: $method');
  }
}

enum SearchSource { venue, osm }

class VenueSearchResult {
  final String? id;
  final SearchSource source;
  final String name;
  final String address;
  final double? latitude;
  final double? longitude;
  final String? city;
  final String? state;
  final String? zipCode;
  final double? rating;
  final int? totalReviews;
  final String? priceRange;
  final List<String> categories;
  final double? distanceMeters;
  final bool isSaved;
  final String? osmType;
  final int? osmId;

  VenueSearchResult({
    this.id,
    required this.source,
    required this.name,
    required this.address,
    this.latitude,
    this.longitude,
    this.city,
    this.state,
    this.zipCode,
    this.rating,
    this.totalReviews,
    this.priceRange,
    required this.categories,
    this.distanceMeters,
    this.isSaved = false,
    this.osmType,
    this.osmId,
  });

  factory VenueSearchResult.fromJson(Map<String, dynamic> json) {
    // Handle different field name variations
    final sourceStr = json['source']?.toString() ?? 'google';
    final source = sourceStr == 'google' ||
            sourceStr == 'yelp' ||
            sourceStr == 'tripadvisor' ||
            sourceStr == 'foursquare'
        ? SearchSource.venue
        : SearchSource.osm;

    // Handle address field variations
    final address =
        json['address']?.toString() ?? json['street_address']?.toString() ?? '';

    // Handle categories - could be array or comma-separated string
    List<String> categories = [];
    if (json['categories'] != null) {
      if (json['categories'] is List) {
        categories = List<String>.from(json['categories']);
      } else if (json['categories'] is String) {
        categories = (json['categories'] as String)
            .split(',')
            .map((e) => e.trim())
            .toList();
      }
    }

    // Calculate distance if we have lat/lon and a reference point
    double? distanceMeters = json['distance_meters']?.toDouble();

    return VenueSearchResult(
      id: json['id']?.toString() ?? json['place_id']?.toString(),
      source: source,
      name: json['name']?.toString() ?? 'Unnamed Location',
      address: address,
      latitude: json['latitude']?.toDouble() ?? json['lat']?.toDouble(),
      longitude: json['longitude']?.toDouble() ??
          json['lng']?.toDouble() ??
          json['lon']?.toDouble(),
      city: json['city']?.toString(),
      state: json['state']?.toString(),
      zipCode: json['zip_code']?.toString() ?? json['zip']?.toString(),
      rating: json['rating']?.toDouble(),
      totalReviews:
          json['total_reviews'] as int? ?? json['user_ratings_total'] as int?,
      priceRange: json['price_range']?.toString(),
      categories: categories,
      distanceMeters: distanceMeters,
      isSaved: json['is_saved'] ?? false,
      osmType: json['osm_type']?.toString(),
      osmId: json['osm_id'] as int?,
    );
  }
}

class InlineVenueSearchPanel extends StatefulWidget {
  final String? itineraryId;
  final int? insertPosition;
  final double? currentLatitude;
  final double? currentLongitude;
  final Function(Map<String, dynamic>)? onStopCreated;
  final Function()? onCancel;

  const InlineVenueSearchPanel({
    super.key,
    this.itineraryId,
    this.insertPosition,
    this.currentLatitude,
    this.currentLongitude,
    this.onStopCreated,
    this.onCancel,
  });

  @override
  State<InlineVenueSearchPanel> createState() => _InlineVenueSearchPanelState();
}

class _InlineVenueSearchPanelState extends State<InlineVenueSearchPanel> {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  Timer? _debounceTimer;
  List<VenueSearchResult> _venueResults = [];
  List<VenueSearchResult> _osmResults = [];
  bool _isSearching = false;
  String? _selectedVenueId;
  VenueSearchResult? _selectedVenue;
  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _searchFocusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    if (_debounceTimer?.isActive ?? false) _debounceTimer!.cancel();

    _debounceTimer = Timer(const Duration(milliseconds: 300), () {
      if (_searchController.text.trim().length >= 2) {
        _performSearch();
      } else {
        setState(() {
          _venueResults = [];
          _osmResults = [];
          _errorMessage = null;
        });
      }
    });
  }

  Future<void> _performSearch() async {
    if (_isSearching) return;

    setState(() {
      _isSearching = true;
      _errorMessage = null;
    });

    try {
      final query = _searchController.text.trim();
      if (query.isEmpty) {
        setState(() {
          _venueResults = [];
          _osmResults = [];
          _isSearching = false;
        });
        return;
      }

      // Get base URL from ApiService (static getter)
      final baseUrl = ApiService.baseUrl;

      // Use the existing search-venues endpoint (included under /api/ prefix)
      final url = Uri.parse('$baseUrl/api/search-venues/').replace(
        queryParameters: {
          'q': query,
          'limit': '8',
        },
      );

      print('DEBUG: Searching venues at: $url');

      // This endpoint has @permission_classes([]) so it doesn't require authentication
      // Making unauthenticated request to avoid token validation issues
      http.Response response;
      try {
        response = await http.get(
          url,
          headers: {'Content-Type': 'application/json'},
        ).timeout(
          const Duration(seconds: 10),
          onTimeout: () {
            throw Exception(
                'Request timed out. The search is taking too long.');
          },
        );
      } catch (e) {
        if (e.toString().contains('timeout')) {
          throw Exception(
              'Search timed out. Try a shorter or more specific search term.');
        }
        throw Exception('Failed to connect to server: $e');
      }

      print('DEBUG: Response status: ${response.statusCode}');
      print(
          'DEBUG: Response body: ${response.body.length > 200 ? response.body.substring(0, 200) + "..." : response.body}');

      if (response.statusCode == 200) {
        Map<String, dynamic> data;
        try {
          data = json.decode(response.body) as Map<String, dynamic>;
        } catch (e) {
          throw Exception('Invalid JSON response from server');
        }

        // Handle the existing endpoint format (returns 'venues' array)
        final List<dynamic> venuesList = data['venues'] as List? ?? [];
        final List<VenueSearchResult> venues = venuesList
            .map((v) {
              try {
                return VenueSearchResult.fromJson(v as Map<String, dynamic>);
              } catch (e) {
                print('ERROR: Failed to parse venue: $v, error: $e');
                return null;
              }
            })
            .whereType<VenueSearchResult>()
            .toList();

        // For now, OSM results are empty until we add OSM integration
        final List<VenueSearchResult> osmResults = [];

        setState(() {
          _venueResults = venues;
          _osmResults = osmResults;
          if (venues.isEmpty && osmResults.isEmpty) {
            _errorMessage = "No venues found. Try a different search term.";
          }
        });
      } else if (response.statusCode == 500) {
        // Handle database timeout or server errors
        String errorMsg =
            'Search is taking too long. Try a more specific search term.';
        try {
          final errorData = json.decode(response.body) as Map<String, dynamic>;
          final errorStr = errorData['error']?.toString() ?? '';
          if (errorStr.contains('timeout') ||
              errorStr.contains('statement timeout')) {
            errorMsg =
                'Search timed out. Try a shorter or more specific search term.';
          } else {
            errorMsg = 'Server error. Please try again.';
          }
        } catch (e) {
          // Keep default message
        }
        setState(() {
          _errorMessage = errorMsg;
        });
      } else {
        String errorMsg = 'Search temporarily unavailable.';
        try {
          final errorData = json.decode(response.body) as Map<String, dynamic>;
          errorMsg = errorData['error']?.toString() ?? errorMsg;
        } catch (e) {
          errorMsg =
              'Server error (${response.statusCode}): ${response.body.length > 100 ? response.body.substring(0, 100) : response.body}';
        }
        setState(() {
          _errorMessage = errorMsg;
        });
      }
    } catch (e, stackTrace) {
      print('ERROR: Venue search failed: $e');
      print('ERROR: Stack trace: $stackTrace');
      setState(() {
        _errorMessage = "Network error. Check your connection.";
      });
    } finally {
      setState(() {
        _isSearching = false;
      });
    }
  }

  void _selectVenue(VenueSearchResult venue) {
    setState(() {
      if (_selectedVenueId == venue.id && venue.isSaved) {
        _selectedVenueId = null;
        _selectedVenue = null;
      } else {
        _selectedVenueId = venue.id;
        _selectedVenue = venue;
      }
    });
  }

  Future<void> _addStop() async {
    if (_selectedVenue == null) return;

    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    try {
      if (_selectedVenue!.source == SearchSource.osm) {
        await _autosaveOsmVenue();
      } else {
        _createStopFromSelectedVenue();
      }
      // Reset saving state after successful creation
      setState(() {
        _isSaving = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = "Failed to add stop. Please try again.";
        _isSaving = false;
      });
    }
  }

  Future<void> _autosaveOsmVenue() async {
    final osmResult = _osmResults.firstWhere(
      (venue) =>
          venue.id == _selectedVenueId ||
          (venue.osmType == _selectedVenue!.osmType &&
              venue.osmId == _selectedVenue!.osmId),
    );

    final url = Uri.parse('http://localhost:8000/api/venues/autosave-osm');
    final response = await makeAuthenticatedRequest(
      url: url.toString(),
      method: 'POST',
      body: json.encode({
        'osm_data': {
          'osm_type': osmResult.osmType,
          'osm_id': osmResult.osmId,
          'name': osmResult.name,
          'address': osmResult.address,
          'lat': osmResult.latitude,
          'lon': osmResult.longitude,
          'categories': osmResult.categories,
        },
        if (widget.itineraryId != null) 'itinerary_id': widget.itineraryId,
        if (widget.insertPosition != null) 'position': widget.insertPosition,
      }),
      headers: {'Content-Type': 'application/json'},
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      widget.onStopCreated?.call(data['stop'] ?? data);
      widget.onCancel?.call();
    } else {
      throw Exception('Failed to save OSM venue');
    }
  }

  void _createStopFromSelectedVenue() {
    final stopData = {
      'venue_id': _selectedVenue!.id,
      'venue': {
        'id': _selectedVenue!.id,
        'name': _selectedVenue!.name,
        'address': _selectedVenue!.address,
        'latitude': _selectedVenue!.latitude,
        'longitude': _selectedVenue!.longitude,
        'rating': _selectedVenue!.rating,
        'categories': _selectedVenue!.categories,
        'source': _selectedVenue!.source == SearchSource.osm ? 'osm' : 'google',
        'osm_type': _selectedVenue!.osmType,
        'osm_id': _selectedVenue!.osmId,
      },
      'itinerary_id': widget.itineraryId,
      'position': widget.insertPosition,
    };

    widget.onStopCreated?.call(stopData);
    widget.onCancel?.call();
  }

  String _formatDistance(double? meters) {
    if (meters == null) return '';
    if (meters < 1000) {
      return '${meters.round()}m';
    } else {
      return '${(meters / 1000).toStringAsFixed(1)}km';
    }
  }

  Widget _buildVenueListItem(VenueSearchResult venue) {
    final isSelected = _selectedVenueId == venue.id ||
        (_selectedVenue?.osmType == venue.osmType &&
            _selectedVenue?.osmId == venue.osmId);

    return Card(
      elevation: isSelected ? 2 : 1,
      margin: const EdgeInsets.symmetric(vertical: 4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isSelected
            ? const BorderSide(color: _primaryGreen, width: 2)
            : BorderSide(color: Colors.grey[200]!),
      ),
      child: InkWell(
        onTap: () => _selectVenue(venue),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Icon(
                isSelected ? Icons.check_circle : Icons.circle_outlined,
                color: isSelected ? _primaryGreen : Colors.grey[400],
                size: 24,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            venue.name,
                            style: GoogleFonts.inter(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: Colors.black87,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (venue.distanceMeters != null) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: _primaryGreen.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              _formatDistance(venue.distanceMeters),
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: _primaryGreen,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      venue.address,
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (venue.categories.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        venue.categories.join(' • '),
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: Colors.grey[500],
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Search bar
          TextField(
            controller: _searchController,
            focusNode: _searchFocusNode,
            decoration: InputDecoration(
              hintText: 'Search for venues...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _isSearching
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              filled: true,
              fillColor: Colors.white,
            ),
          ),

          // Error message
          if (_errorMessage != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange[50],
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange[200]!),
              ),
              child: Text(
                _errorMessage!,
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: Colors.orange[800],
                ),
              ),
            ),
          ],

          // Results
          if (_venueResults.isNotEmpty || _osmResults.isNotEmpty) ...[
            const SizedBox(height: 16),
            SizedBox(
              height: 300,
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_venueResults.isNotEmpty) ...[
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(
                          'From your venues',
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.black87,
                          ),
                        ),
                      ),
                      ..._venueResults
                          .map((venue) => _buildVenueListItem(venue)),
                      const SizedBox(height: 16),
                    ],
                    if (_osmResults.isNotEmpty) ...[
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(
                          'From OpenStreetMap',
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.black87,
                          ),
                        ),
                      ),
                      ..._osmResults.map((venue) => _buildVenueListItem(venue)),
                    ],
                  ],
                ),
              ),
            ),
          ],

          // Action buttons
          if (_selectedVenue != null) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: widget.onCancel,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      side: BorderSide(color: Colors.grey[400]!),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: Text(
                      'Cancel',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: Colors.black87,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _isSaving ? null : _addStop,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _primaryGreen,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      elevation: 0,
                    ),
                    child: _isSaving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2,
                            ),
                          )
                        : Text(
                            'Add Stop',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                            ),
                          ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
