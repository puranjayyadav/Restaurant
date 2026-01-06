import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import '../api_service.dart';
import '../theme/design_system.dart';
import '../widgets/itinerary_card.dart';
import 'itinerary_category_selection_screen.dart';
import 'itinerary_detail_screen.dart';
import 'settings_screen.dart';
import 'new_trip_modal.dart';
import 'trip_planner_modal_premium.dart';
import 'trip_wizard_screen.dart';
import 'density_heatmap_screen.dart';

/// Main discovery hub showing featured pre-created itineraries
class DiscoveryHomeScreen extends StatefulWidget {
  const DiscoveryHomeScreen({super.key});

  @override
  State<DiscoveryHomeScreen> createState() => _DiscoveryHomeScreenState();
}

class _DiscoveryHomeScreenState extends State<DiscoveryHomeScreen> {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _featuredItineraries = [];
  List<Map<String, dynamic>> _cloneableAdventures = [];
  bool _isLoading = true;
  bool _isLoadingCloneable = true;
  String? _error;
  String? _cloneableError;
  int _selectedIndex = 0; // State for tab selection

  @override
  void initState() {
    super.initState();
    // print('DEBUG: DiscoveryHomeScreen initState() called');
    _loadFeaturedItineraries();
    _loadCloneableAdventures();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _loadFeaturedItineraries() async {
    // Disabled: Not using this endpoint
    // print('DEBUG: _loadFeaturedItineraries() called');
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Disabled: Not querying this endpoint
      // print('DEBUG: About to call getFeaturedItineraries()');
      // final itineraries = await _apiService.getFeaturedItineraries(limit: 8);
      final itineraries =
          <Map<String, dynamic>>[]; // Empty list instead of API call
      // print(
      //     'DEBUG: getFeaturedItineraries() returned ${itineraries.length} itineraries');

      // Debug: Print first itinerary structure (disabled)
      // if (itineraries.isNotEmpty) {
      //   print('DEBUG: First itinerary keys: ${itineraries[0].keys.toList()}');
      //   print('DEBUG: First itinerary title: ${itineraries[0]['title']}');
      //   print(
      //       'DEBUG: First itinerary description: ${itineraries[0]['description']}');
      //   print('DEBUG: First itinerary subtitle: ${itineraries[0]['subtitle']}');
      //   print('DEBUG: First itinerary cuisine: ${itineraries[0]['cuisine']}');
      //   print(
      //       'DEBUG: First itinerary neighborhood: ${itineraries[0]['neighborhood']}');
      //   print(
      //       'DEBUG: First itinerary sample_image_url: ${itineraries[0]['sample_image_url']}');
      //   print('DEBUG: First itinerary tags: ${itineraries[0]['tags']}');
      //   print(
      //       'DEBUG: First itinerary restaurant_count: ${itineraries[0]['restaurant_count']}');
      //   print(
      //       'DEBUG: First itinerary has itinerary_data: ${itineraries[0].containsKey('itinerary_data')}');
      //   if (itineraries[0].containsKey('itinerary_data') &&
      //       itineraries[0]['itinerary_data'] != null) {
      //     final itineraryData =
      //         itineraries[0]['itinerary_data'] as Map<String, dynamic>?;
      //     if (itineraryData != null) {
      //       print(
      //           'DEBUG: First itinerary itinerary_data keys: ${itineraryData.keys.toList()}');
      //       if (itineraryData.containsKey('itinerary')) {
      //         final itineraryItems = itineraryData['itinerary'];
      //         if (itineraryItems is List) {
      //           print(
      //               'DEBUG: First itinerary has ${itineraryItems.length} items in itinerary_data.itinerary');
      //         }
      //       }
      //     }
      //   }
      // } else {
      //   print('WARNING: No itineraries returned from API');
      // }

      setState(() {
        _featuredItineraries = itineraries;
        _isLoading = false;
      });
    } catch (e, stackTrace) {
      print('ERROR: Exception in _loadFeaturedItineraries: $e');
      print('ERROR: Stack trace: $stackTrace');
      setState(() {
        _error = 'Failed to load featured itineraries: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _loadCloneableAdventures() async {
    setState(() {
      _isLoadingCloneable = true;
      _cloneableError = null;
    });
    try {
      print('DEBUG: Starting to load cloneable adventures...');
      final items = await _apiService.getCloneableAdventures(limit: 12);
      print('DEBUG: Received ${items.length} cloneable adventures');
      setState(() {
        _cloneableAdventures = items;
        _isLoadingCloneable = false;
        // Only show error if we expected items but got none
        if (items.isEmpty && _cloneableError == null) {
          _cloneableError =
              'No cloneable adventures available. Check console for details.';
        }
      });
    } catch (e, st) {
      print('ERROR: _loadCloneableAdventures exception: $e');
      print('ERROR: Stack trace: $st');
      setState(() {
        _cloneableError =
            'Failed to load cloneable adventures. Check console logs for details.';
        _isLoadingCloneable = false;
      });
    }
  }

  void _navigateToItineraryDetail(Map<String, dynamic> itinerary) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ItineraryDetailScreen(itinerary: itinerary),
      ),
    );
  }

  /// Transforms cloneable adventure data to the format expected by ItineraryDetailScreen
  Map<String, dynamic> _transformCloneableToItinerary(
      Map<String, dynamic> cloneable) {
    final stops = cloneable['stops'] as List<dynamic>? ?? [];

    // Transform stops to the format expected by ItineraryDetailScreen
    // It expects itinerary_data.itinerary array with postgres_data
    final transformedStops = stops.map((stop) {
      if (stop is Map) {
        // Safely convert Map<dynamic, dynamic> to Map<String, dynamic>
        final stopMap = Map<String, dynamic>.from(stop.cast<String, dynamic>());
        final postgresDataRaw = stopMap['postgres_data'];
        final postgresData = (postgresDataRaw is Map)
            ? Map<String, dynamic>.from(postgresDataRaw.cast<String, dynamic>())
            : null;
        return {
          'place_name': stopMap['place_name'] ?? '',
          'notes': stopMap['notes'] ?? '',
          'postgres_data': postgresData ??
              {
                'name': stopMap['place_name'] ?? '',
                'lat': stopMap['lat'],
                'lng': stopMap['lng'],
                'photos': stopMap['photos'] is List
                    ? (stopMap['photos'] as List)
                        .map((x) => x.toString())
                        .toList()
                    : [],
              },
        };
      }
      return stop;
    }).toList();

    return {
      'title': cloneable['new_title'] ?? cloneable['title'] ?? 'Adventure',
      'new_title': cloneable['new_title'], // Preserve new_title from Supabase
      'subtitle': cloneable['subtitle'] ?? '', // Use subtitle from Supabase
      'description': cloneable['subtitle'] ?? '',
      'tags': cloneable['tags'] ?? [],
      'sample_image_url': cloneable['header_image_url'],
      'itinerary_data': {
        'itinerary': transformedStops,
        'enrichment_stats': {},
        'route_stats': {},
      },
      'original_url': cloneable['original_url'] ?? cloneable['source_id'] ?? '',
    };
  }

  void _navigateToCloneableDetail(Map<String, dynamic> cloneable) {
    final itinerary = _transformCloneableToItinerary(cloneable);
    _navigateToItineraryDetail(itinerary);
  }

  void _navigateToCustomItinerary() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const ItineraryCategorySelectionScreen(),
      ),
    );
  }

  Widget _buildHeroPager(BuildContext context, TextTheme textTheme) {
    return _buildGreetingCard(textTheme);
  }

  Widget _buildEditorialSection(TextTheme textTheme) {
    if (_isLoadingCloneable) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: CircularProgressIndicator(color: AppColors.orange),
        ),
      );
    }
    if (_cloneableError != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(
          _cloneableError!,
          style: textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
        ),
      );
    }
    if (_cloneableAdventures.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Curated for You',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                'See All',
                style: textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                  fontFamily: 'SF Pro Display',
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        MasonryGridView.count(
          physics: const NeverScrollableScrollPhysics(),
          shrinkWrap: true,
          crossAxisCount: 2,
          mainAxisSpacing: 16,
          crossAxisSpacing: 16,
          itemCount: _cloneableAdventures.length,
          itemBuilder: (context, index) {
            final item = _cloneableAdventures[index];
            return _EditorialCard(
              item: item,
              index: index,
              onTap: () => _navigateToCloneableDetail(item),
            );
          },
        ),
      ],
    );
  }

  Widget _buildGreetingCard(TextTheme textTheme) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.sm,
        AppSpacing.lg, // push down a bit
        AppSpacing.lg,
        AppSpacing.md,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Good Morning, Puranjay',
                  style: textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w500, // SF Pro Display Medium
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  'Where should we take you today?',
                  style: textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Transform.translate(
            offset: const Offset(0, -10),
            child: GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const SettingsScreen(),
                  ),
                );
              },
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  shape: BoxShape.circle,
                  boxShadow: AppShadows.soft,
                ),
                child: const Icon(
                  Icons.person_rounded,
                  size: 22,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar(TextTheme textTheme) {
    return Container(
      height: 58,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(32),
        boxShadow: AppShadows.soft,
      ),
      child: Row(
        children: [
          const SizedBox(width: 16),
          const Icon(
            Icons.search,
            color: Color(0xFF222222),
            size: 26,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Search for vibes, places...',
              style: textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 16),
        ],
      ),
    );
  }

  Widget _buildStaticVibeChips(TextTheme textTheme) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      clipBehavior: Clip.none, // Allows shadows to render without clipping
      child: Row(
        children: [
          _StaticChip(
            label: '☕️ Coffee',
            background: const Color(0xFFF5F0EB), // Latte Foam
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '🍷 Date Night',
            background: const Color(0xFFF3E5F5), // Lavender
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '🌿 Hidden Gems',
            background: const Color(0xFFE8F5E9), // Mint
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '🥐 Brunch',
            background: const Color(0xFFFFF3E0), // Apricot
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '🍸 Speakeasy',
            background: const Color(0xFFECEFF1), // Slate
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '📸 Photo Ops',
            background: const Color(0xFFFCE4EC), // Blush
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '🛍️ Vintage',
            background: const Color(0xFFFFFDE7), // Cream
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '🌮 Cheap Eats',
            background: const Color(0xFFE0F2F1), // Light Teal
            textColor: AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.sm),
          _StaticChip(
            label: '💻 Work Spots',
            background: const Color(0xFFF5F5F5), // Light Grey
            textColor: AppColors.textPrimary,
          ),
          // Add right padding so the last item isn't flush with the screen edge
          SizedBox(width: AppSpacing.md),
        ],
      ),
    );
  }
  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    Widget body;
    if (_selectedIndex == 1) {
      body = const DensityHeatmapScreen();
    } else if (_selectedIndex == 2) {
      body = const Center(child: Text('Saved Itineraries', style: TextStyle(color: Colors.white)));
    } else if (_selectedIndex == 3) {
      body = const Center(child: Text('User Profile', style: TextStyle(color: Colors.white)));
    } else {
      body = SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            await _loadFeaturedItineraries();
            await _loadCloneableAdventures();
          },
          child: CustomScrollView(
            key: const ValueKey('discovery_scroll'),
            slivers: [
              // Content
              if (_isLoading)
                SliverFillRemaining(
                  key: const ValueKey('loading'),
                  child: Center(
                    child: CircularProgressIndicator(
                      color: AppColors.orange,
                    ),
                  ),
                )
              else if (_error != null)
                SliverFillRemaining(
                  key: const ValueKey('error'),
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.error_outline,
                          size: 48,
                          color: AppColors.error,
                        ),
                        SizedBox(height: AppSpacing.md),
                        Text(
                          _error!,
                          style: textTheme.bodyMedium?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: AppSpacing.md),
                        ShadButton(
                          onPressed: _loadFeaturedItineraries,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              else
                SliverPadding(
                  key: const ValueKey('content'),
                  padding: EdgeInsets.only(
                    left: AppSpacing.md,
                    right: AppSpacing.md,
                    top: 0.0,
                    bottom: AppSpacing.xxl + AppSpacing.md,
                  ),
                  sliver: SliverList(
                    delegate: SliverChildListDelegate([
                      _buildHeroPager(context, textTheme),
                      SizedBox(height: AppSpacing.md),
                      _buildSearchBar(textTheme),
                      SizedBox(height: AppSpacing.md),
                      _buildStaticVibeChips(textTheme),
                      SizedBox(height: AppSpacing.lg),
                      _buildEditorialSection(textTheme),
                      SizedBox(height: AppSpacing.lg),
                      if (_featuredItineraries.isNotEmpty)
                        _buildLocalGemsSection(
                          context,
                          _featuredItineraries,
                          showPageIndicator: false,
                        ),
                    ]),
                  ),
                ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      extendBody: true,
      body: Stack(
        children: [
          body,
          Positioned(
            left: 40,
            right: 40,
            bottom: 35,
            child: FloatingNavIsland(
              selectedIndex: _selectedIndex,
              onIndexChanged: (index) => setState(() => _selectedIndex = index),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLocalGemsSection(
    BuildContext context,
    List<Map<String, dynamic>> items, {
    bool showPageIndicator = false,
    bool showBuildItineraryButton = false,
  }) {
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header
        Padding(
          padding: EdgeInsets.only(
            top: 5,
            bottom: 0.0,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Cloneable Adventures',
                style: textTheme.titleLarge?.copyWith(
                  fontFamily: 'SF Pro Display',
                  fontWeight: FontWeight.w500,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                'See all',
                style: textTheme.bodyMedium?.copyWith(
                  fontFamily: 'SF Pro Display',
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        SizedBox(height: AppSpacing.md),
        // Horizontal Scrollable Cards
        SizedBox(
          height: 300,
          child: items.isEmpty
              ? Center(
                  child: Text(
                    'No itineraries available',
                    style: textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                )
              : ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    try {
                      if (index >= items.length) {
                        return SizedBox.shrink();
                      }
                      final item = items[index];
                      if (item.isEmpty) {
                        return SizedBox.shrink();
                      }
                      return Container(
                        width: 180,
                        margin: EdgeInsets.only(
                          right: AppSpacing.md,
                        ),
                        child: showBuildItineraryButton && index == 1
                            ? _buildBuildItineraryCard(item)
                            : ItineraryCard(
                                itinerary: item,
                                onTap: () => _navigateToItineraryDetail(item),
                              ),
                      );
                    } catch (e, stackTrace) {
                      print(
                          'ERROR: Exception building itinerary card at index $index: $e');
                      print('ERROR: Stack trace: $stackTrace');
                      return Container(
                        width: 280,
                        margin: EdgeInsets.only(right: AppSpacing.md),
                        child: ShadCard(
                          child: Padding(
                            padding: EdgeInsets.all(AppSpacing.md),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.error_outline,
                                    color: AppColors.error),
                                SizedBox(height: AppSpacing.sm),
                                Text(
                                  'Error loading',
                                  style: TextStyle(
                                      color: AppColors.error, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    }
                  },
                ),
        ),
        // Page Indicator (only for first section)
        if (showPageIndicator && items.length > 0)
          Padding(
            padding: EdgeInsets.only(top: AppSpacing.sm),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                items.length,
                (index) => Container(
                  width: 8,
                  height: 8,
                  margin: EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: index == 0 ? AppColors.orange : AppColors.border,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  String? _getImageUrlFromItinerary(Map<String, dynamic> itinerary) {
    try {
      // First try sample_image_url
      final sampleImageUrl = itinerary['sample_image_url'];
      if (sampleImageUrl != null &&
          sampleImageUrl is String &&
          sampleImageUrl.isNotEmpty &&
          sampleImageUrl != 'null') {
        return sampleImageUrl;
      }

      // Try to get image from first restaurant in itinerary_data
      final itineraryData = itinerary['itinerary_data'];
      if (itineraryData != null && itineraryData is Map<String, dynamic>) {
        final itineraryItems = itineraryData['itinerary'];
        if (itineraryItems != null &&
            itineraryItems is List &&
            itineraryItems.isNotEmpty) {
          final firstRestaurant = itineraryItems[0];
          if (firstRestaurant != null &&
              firstRestaurant is Map<String, dynamic>) {
            // Try postgres_data photos
            final postgresData = firstRestaurant['postgres_data'];
            if (postgresData != null && postgresData is Map<String, dynamic>) {
              final photos = postgresData['photos'];
              if (photos != null && photos is List && photos.isNotEmpty) {
                final photoUrl = photos[0];
                if (photoUrl != null) {
                  return photoUrl.toString();
                }
              }
            }
          }
        }
      }
    } catch (e) {
      print('ERROR: Exception in _getImageUrlFromItinerary: $e');
    }

    return null;
  }

  Widget _buildBuildItineraryCard(Map<String, dynamic> itinerary) {
    try {
      final textTheme = Theme.of(context).textTheme;
      final title = (itinerary['title'] as String?) ?? 'Untitled Itinerary';
      final imageUrl = _getImageUrlFromItinerary(itinerary);

      // Safely get tags
      final tagsRaw = itinerary['tags'];
      List<dynamic> tags = [];
      if (tagsRaw != null && tagsRaw is List) {
        tags = tagsRaw;
      }
      final firstTag = tags.isNotEmpty ? (tags[0]?.toString() ?? '') : '';

      return ShadCard(
        backgroundColor: AppColors.surfaceElevated,
        padding: EdgeInsets.zero,
        child: Stack(
          children: [
            // Image
            ClipRRect(
              borderRadius: BorderRadius.circular(AppBorderRadius.medium),
              child: Container(
                height: 300,
                width: double.infinity,
                color: AppColors.surface,
                child: imageUrl != null
                    ? Image.network(
                        imageUrl,
                        fit: BoxFit.cover,
                        loadingBuilder: (context, child, loadingProgress) {
                          if (loadingProgress == null) return child;
                          return Container(
                            color: AppColors.surface,
                            child: Center(
                              child: CircularProgressIndicator(
                                value: loadingProgress.expectedTotalBytes !=
                                        null
                                    ? loadingProgress.cumulativeBytesLoaded /
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
            // Build Itinerary Button Overlay
            Positioned(
              bottom: 16,
              right: 16,
              child: GestureDetector(
                onTap: _navigateToCustomItinerary,
                child: Container(
                  padding: EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.sm,
                  ),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [AppColors.orange, AppColors.teal],
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                    ),
                    borderRadius: BorderRadius.circular(AppBorderRadius.small),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.3),
                        blurRadius: 8,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'P',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        ' Build Itinerary',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            // Tag at bottom left
            if (firstTag.isNotEmpty)
              Positioned(
                bottom: 16,
                left: 16,
                child: Container(
                  padding: EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.teal.withOpacity(0.95),
                    borderRadius: BorderRadius.circular(AppBorderRadius.small),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        blurRadius: 4,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Text(
                    firstTag.length > 12 ? firstTag.substring(0, 12) : firstTag,
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
            // Title below image
            Positioned(
              bottom: 60,
              left: 16,
              right: 16,
              child: Text(
                title,
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                  fontSize: 16,
                  shadows: [
                    Shadow(
                      offset: Offset(0, 2),
                      blurRadius: 6,
                      color: Colors.black.withOpacity(0.7),
                    ),
                  ],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      );
    } catch (e, stackTrace) {
      print('ERROR: Exception in _buildBuildItineraryCard: $e');
      print('ERROR: Stack trace: $stackTrace');
      // Return a safe fallback
      return ShadCard(
        backgroundColor: AppColors.surfaceElevated,
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.md),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, color: AppColors.error),
              SizedBox(height: AppSpacing.sm),
              Text(
                'Error loading card',
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
      color: AppColors.surface,
      child: Center(
        child: Icon(
          Icons.restaurant,
          size: 48,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}

class _StaticChip extends StatelessWidget {
  final String label;
  final Color background;
  final Color textColor;

  const _StaticChip({
    required this.label,
    required this.background,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(28),
        boxShadow: AppShadows.soft,
      ),
      child: Text(
        label,
        style: TextStyle(
          color: textColor,
          fontFamily: 'MeeraInimai', // Use MeeraInimai Regular for vibe chips
          fontWeight: FontWeight.w400,
        ),
      ),
    );
  }
}

/// Floating navigation island for the "Cinematic Socialite" look
class FloatingNavIsland extends StatefulWidget {
  final int selectedIndex;
  final Function(int) onIndexChanged;

  const FloatingNavIsland({
    super.key,
    required this.selectedIndex,
    required this.onIndexChanged,
  });

  @override
  State<FloatingNavIsland> createState() => _FloatingNavIslandState();
}

class _FloatingNavIslandState extends State<FloatingNavIsland> {

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 70,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(35),
        boxShadow: [
          // Lift shadow
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 30,
            offset: const Offset(0, 10),
            spreadRadius: 0,
          ),
          // Definition shadow
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildNavItem(0, Icons.compass_calibration_outlined, "Explore"),
          _buildNavItem(1, Icons.map_outlined, "Map"),
          _buildCenterButton(),
          _buildNavItem(2, Icons.favorite_border, "Saved"),
          _buildNavItem(3, Icons.person_outline, "Profile"),
        ],
      ),
    );
  }

  Widget _buildNavItem(int index, IconData icon, String label) {
    final bool isActive = widget.selectedIndex == index;

    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact(); // Add haptic feedback
        widget.onIndexChanged(index);
      },
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 50,
        height: 70,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              color: isActive ? const Color(0xFF222222) : Colors.grey[400],
              size: 26,
            ),
            const SizedBox(height: 6),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: isActive ? 4 : 0,
              height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFF222222),
                shape: BoxShape.circle,
                boxShadow: isActive
                    ? [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.3),
                          blurRadius: 4,
                        )
                      ]
                    : [],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCenterButton() {
    return GestureDetector(
      onTap: () {
        showTripWizard(context);
      },
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: const Color(0xFF222222),
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 10,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: const Icon(Icons.add, color: Colors.white, size: 28),
      ),
    );
  }
}

class _EditorialCard extends StatelessWidget {
  final Map<String, dynamic> item;
  final int index;
  final VoidCallback? onTap;

  const _EditorialCard({
    required this.item,
    required this.index,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isTall = index % 3 == 0;
    final double height = isTall ? 280 : 190;
    final title = item['new_title']?.toString() ??
        item['title']?.toString() ??
        'Adventure';
    final subtitle = item['subtitle']?.toString() ?? '';
    final imageUrl = item['header_image_url']?.toString() ?? '';
    String vibe = '';
    final tags = item['tags'];
    if (tags is List && tags.isNotEmpty) {
      vibe = tags.first.toString();
    }
    final stops = item['stops'];
    final stopsCount = stops is List ? stops.length : 0;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 15,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Image
              if (imageUrl.isNotEmpty)
                Image.network(
                  imageUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => _buildPlaceholder(),
                )
              else
                _buildPlaceholder(),
              // Gradient overlay
              Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black.withOpacity(0.1),
                      Colors.black.withOpacity(0.8),
                    ],
                    stops: const [0.5, 0.7, 1.0],
                  ),
                ),
              ),
              // Text overlay
              Padding(
                padding: const EdgeInsets.all(14.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Vibe tag
                    if (vibe.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: Colors.white.withOpacity(0.3), width: 0.5),
                        ),
                        child: Text(
                          vibe,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    if (vibe.isNotEmpty) const SizedBox(height: 8),
                    // Title
                    Text(
                      title,
                      style: GoogleFonts.playfairDisplay(
                        fontSize: isTall ? 22 : 18,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                        height: 1.1,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    // Subtitle (stops info)
                    if (isTall) ...[
                      const SizedBox(height: 4),
                      Text(
                        stopsCount > 0
                            ? '$stopsCount stops • 1.2 mi'
                            : (subtitle.isNotEmpty ? subtitle : ''),
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.85),
                          fontSize: 12,
                          fontFamily: 'SF Pro Display',
                        ),
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

  Widget _buildPlaceholder() {
    return Container(
      color: Colors.grey.shade200,
      child: const Icon(Icons.image_not_supported, color: Colors.grey),
    );
  }
}
