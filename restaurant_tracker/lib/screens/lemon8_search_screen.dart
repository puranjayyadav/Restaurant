import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import '../../api_service.dart';
import 'package:url_launcher/url_launcher.dart';
import '../widgets/lemon8/lemon8_vibe_pill.dart';
import '../services/lemon8_image_service.dart';
import 'lemon8_detail_screen.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_auth/firebase_auth.dart';

class Lemon8SearchScreen extends StatefulWidget {
  const Lemon8SearchScreen({super.key});

  @override
  State<Lemon8SearchScreen> createState() => _Lemon8SearchScreenState();
}

class _Lemon8SearchScreenState extends State<Lemon8SearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final ApiService _apiService = ApiService();

  List<Map<String, dynamic>> _results = [];
  bool _isLoading = false;
  bool _hasSearched = false;
  String? _errorMessage;
  final Set<String> _lovedPlaceIds = {};
  bool _isVenueSearchMode = false; // false = itineraries, true = venues

  // Suggested searches for empty state
  final List<String> _suggestedSearches = [
    'Romantic date in Soho',
    'Cozy cafes for working',
    'Hidden gems in Brooklyn',
    'Aesthetic matcha spots',
    'Rooftop bars NYC',
    'Quiet bookstores',
  ];

  @override
  void initState() {
    super.initState();
    _fetchLovedPlaces();
    // Auto-focus search bar when screen opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      FocusScope.of(context).requestFocus(FocusNode());
    });
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
    super.dispose();
  }

  Future<void> _performSearch(String query) async {
    if (query.trim().isEmpty) {
      setState(() {
        _results = [];
        _hasSearched = false;
        _errorMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _hasSearched = true;
      _errorMessage = null;
    });

    try {
      List<Map<String, dynamic>> results;
      if (_isVenueSearchMode) {
        results = await _searchVenues(query);
      } else {
        results = await _apiService.searchLemon8Aesthetics(query, k: 10);
      }
      setState(() {
        _results = results;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to search. Please try again.';
        _isLoading = false;
        _results = [];
      });
    }
  }

  Future<List<Map<String, dynamic>>> _searchVenues(String query) async {
    try {
      final supabase = Supabase.instance.client;
      final searchTerm = query.trim();

      if (searchTerm.isEmpty) {
        return [];
      }

      // Search across name, address, and city fields
      final response = await supabase
          .from('venues')
          .select()
          .or('name.ilike.%$searchTerm%,address.ilike.%$searchTerm%,city.ilike.%$searchTerm%')
          .order('rating', ascending: false)
          .limit(20);

      return List<Map<String, dynamic>>.from(response);
    } catch (e) {
      print('ERROR: Exception in _searchVenues: $e');
      throw e;
    }
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
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
      child: Column(
        children: [
          // Search Mode Toggle
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: PlanditColors.glass,
              borderRadius: BorderRadius.circular(100),
              border: Border.all(color: PlanditColors.glassBorder),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildToggleButton('Itineraries', !_isVenueSearchMode),
                _buildToggleButton('Venues', _isVenueSearchMode),
              ],
            ),
          ),
          Row(
            children: [
              // Back Button
              IconButton(
                icon: const Icon(Icons.arrow_back,
                    color: PlanditColors.foreground),
                onPressed: () => Navigator.pop(context),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
              const SizedBox(width: 12),

              // Search Input
              Expanded(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
                            hintText: 'Search vibes, aesthetics, date ideas...',
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
                          onSubmitted: _performSearch,
                          onChanged: (value) {
                            // Debounce search - only search after user stops typing for 500ms
                            Future.delayed(const Duration(milliseconds: 500),
                                () {
                              if (_searchController.text == value) {
                                _performSearch(value);
                              }
                            });
                          },
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
                            });
                          },
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildToggleButton(String label, bool isSelected) {
    return GestureDetector(
      onTap: () {
        setState(() {
          _isVenueSearchMode = label == 'Venues';
          if (_searchController.text.isNotEmpty) {
            _performSearch(_searchController.text);
          }
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? PlanditColors.primary : Colors.transparent,
          borderRadius: BorderRadius.circular(100),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: isSelected
                ? PlanditColors.primaryForeground
                : PlanditColors.foreground,
          ),
        ),
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
            'Discover Aesthetic Spots',
            style: GoogleFonts.playfairDisplay(
              fontSize: 24,
              fontWeight: FontWeight.w400,
              color: PlanditColors.foreground,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Search for vibes, date ideas, and hidden gems curated from Lemon8',
            style: TextStyle(
              fontSize: 14,
              color: PlanditColors.mutedForeground,
            ),
          ),
          const SizedBox(height: 32),
          Text(
            'Try searching for:',
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
                  _performSearch(suggestion);
                },
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: PlanditColors.secondary,
                    borderRadius: BorderRadius.circular(100),
                    border: Border.all(
                        color: PlanditColors.border.withOpacity(0.3)),
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
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: 5,
      separatorBuilder: (context, index) => const SizedBox(height: 16),
      itemBuilder: (context, index) {
        return Container(
          height: 120,
          decoration: BoxDecoration(
            color: PlanditColors.glass,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Center(
            child: CircularProgressIndicator(
              color: PlanditColors.accent,
              strokeWidth: 2,
            ),
          ),
        );
      },
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
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
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
              'No results found',
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
        final result = _results[index];
        if (_isVenueSearchMode) {
          return _buildVenueCard(result);
        } else {
          return _buildResultCard(result);
        }
      },
    );
  }

  Widget _buildResultCard(Map<String, dynamic> result) {
    final title = result['title'] ?? 'Untitled';
    final description = result['description'] ?? '';
    final url = result['url'] ?? '';
    final vibes = List<String>.from(result['contained_vibes'] ?? []);
    final imageUrl = Lemon8ImageService.getItineraryImage(result);

    // Parse metadata from enriched_itinerary_data
    Map<String, dynamic> enrichedData = {};
    final rawEnriched = result['enriched_itinerary_data'];
    if (rawEnriched is Map) {
      enrichedData = Map<String, dynamic>.from(rawEnriched);
    } else if (rawEnriched is String) {
      try {
        enrichedData = json.decode(rawEnriched) as Map<String, dynamic>;
      } catch (e) {
        print('ERROR: Failed to parse enriched_itinerary_data: $e');
      }
    }

    final stops =
        enrichedData['stops'] is List ? (enrichedData['stops'] as List) : [];
    final stopCount = stops.length;
    final priceTier = enrichedData['price'] ?? '\$\$';

    // Generate a unique ID for the itinerary
    final itineraryId =
        'lemon8_itinerary_${title.toLowerCase().replaceAll(' ', '_')}';
    final isLoved = _lovedPlaceIds.contains(itineraryId);

    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => Lemon8DetailScreen(result: result),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 24),
        decoration: BoxDecoration(
          color: PlanditColors.chicCream,
          borderRadius: BorderRadius.circular(2), // Sharp, architectural feel
          boxShadow: PlanditColors.shadowChic,
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Premium Image Header
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Image.network(
                    imageUrl,
                    fit: BoxFit.cover,
                  ),
                ),
                // Gradient Overlay
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          PlanditColors.chicCharcoal.withOpacity(0.4),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),
                // Love Button Overlay
                Positioned(
                  top: 16,
                  right: 16,
                  child: GestureDetector(
                    onTap: () async {
                      final firebaseUser = FirebaseAuth.instance.currentUser;
                      if (firebaseUser == null) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text('Please sign in to save places')),
                        );
                        return;
                      }

                      final isCurrentlyLoved =
                          _lovedPlaceIds.contains(itineraryId);

                      setState(() {
                        if (isCurrentlyLoved) {
                          _lovedPlaceIds.remove(itineraryId);
                        } else {
                          _lovedPlaceIds.add(itineraryId);
                        }
                      });

                      try {
                        final supabase = Supabase.instance.client;
                        if (isCurrentlyLoved) {
                          await supabase.from('loved_places').delete().match({
                            'user_id': firebaseUser.uid,
                            'place_id': itineraryId
                          });
                        } else {
                          // Get coords from first stop if available
                          double lat = 0.0;
                          double lng = 0.0;
                          if (stops.isNotEmpty) {
                            final firstStop = stops[0];
                            if (firstStop is Map) {
                              lat =
                                  (firstStop['lat'] as num?)?.toDouble() ?? 0.0;
                              lng =
                                  (firstStop['lng'] as num?)?.toDouble() ?? 0.0;
                            }
                          }

                          await supabase.from('loved_places').insert({
                            'user_id': firebaseUser.uid,
                            'place_id': itineraryId,
                            'name': title,
                            'rating': '4.8', // Itineraries are premium
                            'lat': lat.toString(),
                            'lng': lng.toString(),
                          });
                        }
                      } catch (e) {
                        setState(() {
                          if (isCurrentlyLoved) {
                            _lovedPlaceIds.add(itineraryId);
                          } else {
                            _lovedPlaceIds.remove(itineraryId);
                          }
                        });
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                                content: Text('Failed to update: $e'),
                                backgroundColor: Colors.red),
                          );
                        }
                      }
                    },
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.9),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Icon(
                        isLoved ? Icons.favorite : Icons.favorite_border,
                        color:
                            isLoved ? Colors.red : PlanditColors.chicCharcoal,
                        size: 20,
                      ),
                    ),
                  ),
                ),
                // Vibe Pills Overlay
                if (vibes.isNotEmpty)
                  Positioned(
                    top: 16,
                    left: 16,
                    right: 16,
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: vibes
                          .take(3)
                          .map((vibe) => Lemon8VibePill(text: vibe))
                          .toList(),
                    ),
                  ),
              ],
            ),

            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title
                  Text(
                    title,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 26,
                      fontWeight: FontWeight.w500,
                      color: PlanditColors.chicCharcoal,
                      height: 1.2,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 12),
                  // Truncated Description
                  if (description.isNotEmpty)
                    Text(
                      description,
                      style: const TextStyle(
                        fontSize: 14,
                        color: PlanditColors.mutedForeground,
                        height: 1.5,
                      ),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                  const SizedBox(height: 20),
                  // Metadata and Action
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Stops and Price
                      Row(
                        children: [
                          _buildMetaBadge('$stopCount STOPS'),
                          const SizedBox(width: 8),
                          _buildMetaBadge('EST. $priceTier'),
                        ],
                      ),
                      // Gold Action Link
                      Row(
                        children: [
                          Text(
                            'VIEW ITINERARY',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: PlanditColors.chicGold,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Icon(
                            Icons.arrow_forward,
                            size: 14,
                            color: PlanditColors.chicGold,
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVenueCard(Map<String, dynamic> venue) {
    final name = venue['name'] ?? 'Unknown Venue';
    final address = venue['address'] ?? '';
    final city = venue['city'] ?? '';
    final state = venue['state'] ?? '';
    final rating =
        venue['rating'] != null ? (venue['rating'] as num).toDouble() : null;
    final reviewCount = venue['review_count'] ?? 0;
    final placeId = venue['place_id'] ?? '';

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
      print('Error parsing venue photos: $e');
    }

    final locationText = [city, state].where((s) => s.isNotEmpty).join(', ');
    final isLoved = _lovedPlaceIds.contains(placeId);

    return GestureDetector(
      onTap: () {
        // TODO: Navigate to venue detail screen when available
        // For now, just show a snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Venue: $name')),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 24),
        decoration: BoxDecoration(
          color: PlanditColors.chicCream,
          borderRadius: BorderRadius.circular(2),
          boxShadow: PlanditColors.shadowChic,
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Premium Image Header
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 16 / 9,
                  child: imageUrl != null && imageUrl.isNotEmpty
                      ? Image.network(
                          imageUrl,
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) {
                            return Container(
                              color: PlanditColors.glass,
                              child: const Center(
                                child: Icon(
                                  Icons.restaurant,
                                  size: 48,
                                  color: PlanditColors.mutedForeground,
                                ),
                              ),
                            );
                          },
                        )
                      : Container(
                          color: PlanditColors.glass,
                          child: const Center(
                            child: Icon(
                              Icons.restaurant,
                              size: 48,
                              color: PlanditColors.mutedForeground,
                            ),
                          ),
                        ),
                ),
                // Gradient Overlay
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          PlanditColors.chicCharcoal.withOpacity(0.4),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),
                // Love Button Overlay
                Positioned(
                  top: 16,
                  right: 16,
                  child: GestureDetector(
                    onTap: () async {
                      final firebaseUser = FirebaseAuth.instance.currentUser;
                      if (firebaseUser == null) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text('Please sign in to save places')),
                        );
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
                            'name': name,
                            'rating': rating?.toString() ?? '0',
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
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                                content: Text('Failed to update: $e'),
                                backgroundColor: Colors.red),
                          );
                        }
                      }
                    },
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.9),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Icon(
                        isLoved ? Icons.favorite : Icons.favorite_border,
                        color:
                            isLoved ? Colors.red : PlanditColors.chicCharcoal,
                        size: 20,
                      ),
                    ),
                  ),
                ),
                // Rating Badge Overlay
                if (rating != null)
                  Positioned(
                    top: 16,
                    left: 16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.9),
                        borderRadius: BorderRadius.circular(100),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.star,
                            size: 16,
                            color: Colors.amber,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            rating.toStringAsFixed(1),
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: PlanditColors.chicCharcoal,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),

            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title
                  Text(
                    name,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 26,
                      fontWeight: FontWeight.w500,
                      color: PlanditColors.chicCharcoal,
                      height: 1.2,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 12),
                  // Location
                  if (locationText.isNotEmpty || address.isNotEmpty)
                    Row(
                      children: [
                        const Icon(
                          Icons.location_on_outlined,
                          size: 16,
                          color: PlanditColors.mutedForeground,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            address.isNotEmpty ? address : locationText,
                            style: const TextStyle(
                              fontSize: 14,
                              color: PlanditColors.mutedForeground,
                              height: 1.5,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  const SizedBox(height: 20),
                  // Metadata and Action
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Review Count
                      if (reviewCount > 0)
                        Row(
                          children: [
                            _buildMetaBadge('$reviewCount REVIEWS'),
                          ],
                        ),
                      // Gold Action Link
                      Row(
                        children: [
                          Text(
                            'VIEW DETAILS',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: PlanditColors.chicGold,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Icon(
                            Icons.arrow_forward,
                            size: 14,
                            color: PlanditColors.chicGold,
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
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

  Color _getMatchColor(double similarity) {
    if (similarity >= 0.7) return const Color(0xFF52C77A); // Green
    if (similarity >= 0.5) return const Color(0xFFE6AC1A); // Yellow
    return const Color(0xFFE67E50); // Orange
  }
}
