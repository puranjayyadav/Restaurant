import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;
import '../theme/plandit_design_system.dart';
import '../api_service.dart';

class VenueSearchScreen extends StatefulWidget {
  final String? initialQuery;
  const VenueSearchScreen({super.key, this.initialQuery});

  @override
  State<VenueSearchScreen> createState() => _VenueSearchScreenState();
}

class _VenueSearchScreenState extends State<VenueSearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final Set<String> _lovedPlaceIds = {};
  
  List<Map<String, dynamic>> _results = [];
  bool _isLoading = false;
  bool _hasSearched = false;
  String? _errorMessage;
  Timer? _debounceTimer;

  // Suggested searches for empty state
  final List<String> _suggestedSearches = [
    'Coffee shops',
    'Italian restaurants',
    'Rooftop bars',
    'Sushi',
    'Brunch spots',
    'Pizza',
  ];

  @override
  void initState() {
    super.initState();
    _fetchLovedPlaces();
    
    if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
      _searchController.text = widget.initialQuery!;
      // Use a post frame callback to ensure the UI is ready before searching
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _performSearch(widget.initialQuery!);
      });
    } else {
      // Auto-focus search bar when screen opens only if no initial query
      WidgetsBinding.instance.addPostFrameCallback((_) {
        FocusScope.of(context).requestFocus(FocusNode());
      });
    }
  }

  Future<void> _fetchLovedPlaces() async {
    try {
      final firebaseUser = FirebaseAuth.instance.currentUser;
      if (firebaseUser == null) return;

      final supabase = Supabase.instance.client;
      final response = await supabase
          .from('loved_places')
          .select('place_id')
          .eq('user_id', firebaseUser.uid);

      if (mounted) {
        final lovedIds = (response as List)
            .map((item) => item['place_id'] as String)
            .toSet();
        setState(() {
          _lovedPlaceIds.addAll(lovedIds);
        });
      }
    } catch (e) {
      debugPrint('Error fetching loved places: $e');
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _debounceTimer?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    // Cancel previous timer
    _debounceTimer?.cancel();

    if (query.trim().isEmpty) {
      setState(() {
        _results = [];
        _hasSearched = false;
        _errorMessage = null;
        _isLoading = false;
      });
      return;
    }

    // Set loading state immediately
    setState(() {
      _isLoading = true;
      _hasSearched = true;
    });

    // Start new timer for 500ms debounce
    _debounceTimer = Timer(const Duration(milliseconds: 500), () {
      _performSearch(query);
    });
  }

  Future<void> _performSearch(String query) async {
    if (query.trim().isEmpty) {
      setState(() {
        _results = [];
        _hasSearched = false;
        _errorMessage = null;
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final results = await _searchVenues(query);
      if (mounted) {
        setState(() {
          _results = results;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to search. Please try again.';
          _isLoading = false;
          _results = [];
        });
      }
    }
  }

  Future<List<Map<String, dynamic>>> _searchVenues(String query) async {
    try {
      final searchTerm = query.trim();
      if (searchTerm.isEmpty) return [];

      final baseUrl = ApiService.baseUrl;
      final url = Uri.parse('$baseUrl/api/search-venues/?q=${Uri.encodeComponent(searchTerm)}');
      
      debugPrint('DEBUG: Calling search API: $url');
      
      final response = await http.get(url).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        final List<dynamic> venues = data['venues'] ?? [];
        return List<Map<String, dynamic>>.from(venues);
      } else {
        debugPrint('Backend search failed: ${response.statusCode}');
        debugPrint('Response body: ${response.body}');
        return [];
      }
    } catch (e) {
      debugPrint('Error in _searchVenues: $e');
      return [];
    }
  }

  Future<void> _toggleLovePlace(String placeId, Map<String, dynamic> venue) async {
    final firebaseUser = FirebaseAuth.instance.currentUser;
    if (firebaseUser == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please sign in to save places')),
        );
      }
      return;
    }

    final isCurrentlyLoved = _lovedPlaceIds.contains(placeId);

    setState(() {
      if (isCurrentlyLoved) {
        _lovedPlaceIds.remove(placeId);
      } else {
        _lovedPlaceIds.add(placeId);
      }
    });

    try {
      final supabase = Supabase.instance.client;
      if (isCurrentlyLoved) {
        await supabase.from('loved_places').delete().match({
          'user_id': firebaseUser.uid,
          'place_id': placeId
        });
      } else {
        await supabase.from('loved_places').insert({
          'user_id': firebaseUser.uid,
          'place_id': placeId,
          'name': venue['name'] ?? 'Unknown',
          'rating': venue['rating']?.toString() ?? '0',
          'lat': venue['latitude']?.toString() ?? '0',
          'lng': venue['longitude']?.toString() ?? '0',
        });
      }
    } catch (e) {
      setState(() {
        if (isCurrentlyLoved) {
          _lovedPlaceIds.add(placeId);
        } else {
          _lovedPlaceIds.remove(placeId);
        }
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PlanditColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Search Header
            _buildSearchHeader(),

            // Search Results / States
            Expanded(
              child: _buildBody(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PlanditColors.background,
        border: Border(
          bottom: BorderSide(
            color: PlanditColors.border.withOpacity(0.3),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Back Button
          IconButton(
            icon: const Icon(Icons.arrow_back, color: PlanditColors.foreground),
            onPressed: () => Navigator.pop(context),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          const SizedBox(width: 12),

          // Search Input
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: PlanditColors.glass,
                borderRadius: BorderRadius.circular(100),
                border: Border.all(color: PlanditColors.glassBorder),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.search,
                    color: PlanditColors.mutedForeground,
                    size: 20,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      autofocus: true,
                      decoration: const InputDecoration(
                        hintText: 'Search venues, restaurants, cafes...',
                        hintStyle: TextStyle(
                          color: PlanditColors.mutedForeground,
                          fontSize: 14,
                        ),
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: EdgeInsets.zero,
                      ),
                      style: const TextStyle(
                        color: PlanditColors.foreground,
                        fontSize: 14,
                      ),
                      onChanged: _onSearchChanged,
                      onSubmitted: _performSearch,
                    ),
                  ),
                  if (_searchController.text.isNotEmpty)
                    IconButton(
                      icon: const Icon(Icons.clear, size: 18),
                      color: PlanditColors.mutedForeground,
                      onPressed: () {
                        _searchController.clear();
                        setState(() {
                          _results = [];
                          _hasSearched = false;
                          _isLoading = false;
                        });
                      },
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Search Button
          Container(
            decoration: BoxDecoration(
              color: PlanditColors.primary,
              borderRadius: BorderRadius.circular(100),
            ),
            child: IconButton(
              icon: const Icon(Icons.search, color: PlanditColors.primaryForeground),
              onPressed: () {
                if (_searchController.text.isNotEmpty) {
                  _performSearch(_searchController.text);
                }
              },
              padding: const EdgeInsets.all(12),
              constraints: const BoxConstraints(),
              tooltip: 'Search',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return _buildLoadingState();
    }

    if (_errorMessage != null) {
      return _buildErrorState();
    }

    if (!_hasSearched) {
      return _buildEmptyState();
    }

    if (_results.isEmpty) {
      return _buildNoResultsState();
    }

    return _buildResultsList();
  }

  Widget _buildEmptyState() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Discover Amazing Venues',
            style: GoogleFonts.playfairDisplay(
              fontSize: 24,
              fontWeight: FontWeight.w400,
              color: PlanditColors.foreground,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Search for restaurants, cafes, bars, and more',
            style: TextStyle(
              fontSize: 14,
              color: PlanditColors.mutedForeground,
            ),
          ),
          const SizedBox(height: 32),
          Text(
            'TRY SEARCHING FOR:',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: PlanditColors.mutedForeground.withOpacity(0.7),
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _suggestedSearches.map((suggestion) {
              return GestureDetector(
                onTap: () {
                  _searchController.text = suggestion;
                  _onSearchChanged(suggestion);
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: PlanditColors.secondary,
                    borderRadius: BorderRadius.circular(100),
                    border: Border.all(color: PlanditColors.border.withOpacity(0.3)),
                  ),
                  child: Text(
                    suggestion,
                    style: const TextStyle(
                      fontSize: 13,
                      color: PlanditColors.foreground,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: CircularProgressIndicator(
        color: PlanditColors.accent,
        strokeWidth: 2,
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: PlanditColors.mutedForeground,
            ),
            const SizedBox(height: 16),
            Text(
              _errorMessage ?? 'Something went wrong',
              style: const TextStyle(
                fontSize: 16,
                color: PlanditColors.foreground,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => _performSearch(_searchController.text),
              style: ElevatedButton.styleFrom(
                backgroundColor: PlanditColors.primary,
                foregroundColor: PlanditColors.primaryForeground,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(100),
                ),
              ),
              child: const Text('Try Again'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNoResultsState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.search_off,
              size: 64,
              color: PlanditColors.mutedForeground,
            ),
            const SizedBox(height: 16),
            const Text(
              'No venues found',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: PlanditColors.foreground,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Try a different search or explore our suggestions',
              style: TextStyle(
                fontSize: 14,
                color: PlanditColors.mutedForeground,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultsList() {
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: _results.length,
      separatorBuilder: (context, index) => const SizedBox(height: 16),
      itemBuilder: (context, index) {
        final venue = _results[index];
        return _buildVenueCard(venue);
      },
    );
  }

  Widget _buildVenueCard(Map<String, dynamic> venue) {
    final name = venue['name'] ?? 'Unknown Venue';
    final address = venue['address'] ?? '';
    final city = venue['city'] ?? '';
    final state = venue['state'] ?? '';
    final rating = venue['rating'] != null ? (venue['rating'] as num).toDouble() : null;
    final reviewCount = venue['review_count'] ?? 0;
    final placeId = venue['place_id'] ?? '';
    final categories = venue['categories'] ?? '';

    // Extract photo URL from photos JSONB
    String? imageUrl;
    try {
      final photos = venue['photos'];
      if (photos != null) {
        if (photos is List && photos.isNotEmpty) {
          final firstPhoto = photos[0];
          if (firstPhoto is Map && firstPhoto['url'] != null) {
            imageUrl = firstPhoto['url'].toString();
          } else if (firstPhoto is String) {
            imageUrl = firstPhoto;
          }
        } else if (photos is Map && photos['url'] != null) {
          imageUrl = photos['url'].toString();
        }
      }
    } catch (e) {
      debugPrint('Error parsing venue photos: $e');
    }

    final locationText = [city, state].where((s) => s.isNotEmpty).join(', ');
    final isLoved = _lovedPlaceIds.contains(placeId);

    return GestureDetector(
      onTap: () {
        // TODO: Navigate to venue detail screen
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Venue: $name')),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: PlanditColors.card,
          borderRadius: BorderRadius.circular(8),
          boxShadow: PlanditColors.shadowSoft,
        ),
        clipBehavior: Clip.antiAlias,
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title and Rating/Love Row
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      name,
                      style: GoogleFonts.playfairDisplay(
                        fontSize: 22,
                        fontWeight: FontWeight.w500,
                        color: PlanditColors.primaryText,
                        height: 1.2,
                      ).copyWith(
                        fontFamilyFallback: [
                          'Apple Color Emoji',
                          'Segoe UI Emoji',
                          'Noto Color Emoji',
                        ],
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      GestureDetector(
                        onTap: () => _toggleLovePlace(placeId, venue),
                        child: Icon(
                          isLoved ? Icons.favorite : Icons.favorite_border,
                          color: isLoved ? Colors.red : PlanditColors.primaryText,
                          size: 22,
                        ),
                      ),
                      if (rating != null) ...[
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Icon(
                              Icons.star,
                              size: 14,
                              color: Colors.amber,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              rating.toStringAsFixed(1),
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: PlanditColors.primaryText,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Categories / Location Fallback
              if (categories.isNotEmpty)
                Text(
                  categories,
                  style: const TextStyle(
                    fontSize: 13,
                    color: PlanditColors.accentGold,
                    fontStyle: FontStyle.italic,
                    fontWeight: FontWeight.w500,
                    fontFamilyFallback: [
                      'Apple Color Emoji',
                      'Segoe UI Emoji',
                      'Noto Color Emoji',
                    ],
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                )
              else if (locationText.isNotEmpty)
                Text(
                  locationText,
                  style: const TextStyle(
                    fontSize: 13,
                    color: PlanditColors.accentGold,
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              const SizedBox(height: 12),
              // Location detail
              if (address.isNotEmpty)
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 14,
                      color: PlanditColors.mutedForeground,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        address,
                        style: const TextStyle(
                          fontSize: 13,
                          color: PlanditColors.mutedForeground,
                          height: 1.4,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: 16),
              // Metadata and Action
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Review Count
                  if (reviewCount > 0)
                    _buildMetaBadge('$reviewCount REVIEWS'),
                  const Spacer(),
                  // Gold Action Link
                  Row(
                    children: [
                      Text(
                        'VIEW DETAILS',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: PlanditColors.primaryText,
                          letterSpacing: 1.1,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Icon(
                        Icons.arrow_forward,
                        size: 12,
                        color: PlanditColors.primaryText,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetaBadge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: PlanditColors.secondary.withOpacity(0.5),
        borderRadius: BorderRadius.circular(2),
      ),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: PlanditColors.secondaryForeground,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
