import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../api_service.dart';
import '../widgets/plandit/plandit_search_bar.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import '../widgets/beautiful_snackbar.dart';
import 'package:url_launcher/url_launcher.dart';

class RestaurantSearchScreen extends StatefulWidget {
  final String? initialQuery;
  const RestaurantSearchScreen({super.key, this.initialQuery});

  @override
  State<RestaurantSearchScreen> createState() => _RestaurantSearchScreenState();
}

class _RestaurantSearchScreenState extends State<RestaurantSearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final ApiService _apiService = ApiService();
  
  List<Map<String, dynamic>> _results = [];
  bool _isLoading = false;
  bool _hasSearched = false;
  String? _errorMessage;
  Timer? _debounceTimer;
  final Set<String> _lovedRecommendationEstablishmentIds = {};

  // Suggested searches for empty state
  final List<Map<String, String>> _suggestedSearches = [
    {'label': 'Handmade Pasta', 'emoji': '🍝'},
    {'label': 'Speakeasy', 'emoji': '🕵️‍♂️'},
    {'label': 'Rooftop Dining', 'emoji': '🌇'},
    {'label': 'Omakase', 'emoji': '🍣'},
    {'label': 'West Village', 'emoji': '🏘️'},
    {'label': 'Natural Wine', 'emoji': '🍷'},
    {'label': 'Brunch', 'emoji': '🍳'},
    {'label': 'Mexican', 'emoji': '🌮'},
    {'label': 'Late Night', 'emoji': '🌙'},
  ];

  // Pagination state
  final ScrollController _scrollController = ScrollController();
  int _currentOffset = 0;
  bool _isLoadingMore = false;
  bool _canLoadMore = true;
  final int _limit = 20;

  @override
  void initState() {
    super.initState();
    _fetchLovedRecommendations();
    _scrollController.addListener(_onScroll);
    if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
      _searchController.text = widget.initialQuery!;
      _performSearch(widget.initialQuery!);
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _debounceTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 200) {
      if (!_isLoadingMore && _canLoadMore && _results.isNotEmpty) {
        _loadMore();
      }
    }
  }

  Future<void> _fetchLovedRecommendations() async {
    try {
      final firebaseUser = FirebaseAuth.instance.currentUser;
      if (firebaseUser == null) return;

      final supabase = Supabase.instance.client;
      // Note: We use the unique establishment identifier (usually id from cockroachdb)
      // but in our search results it might be establishment name + neighborhood as a key if id isn't robust
      // However, let's assume 'id' column from restaurant_analysis is passed.
      final response = await supabase
          .from('reccomendation_loves')
          .select('establishment_id')
          .eq('user_id', firebaseUser.uid);

      if (mounted) {
        final lovedIds = (response as List)
            .map((item) => item['establishment_id'].toString())
            .toSet();
        setState(() {
          _lovedRecommendationEstablishmentIds.addAll(lovedIds);
        });
      }
    } catch (e) {
      debugPrint('Error fetching loved recommendations: $e');
    }
  }

  Future<void> _toggleLoveRecommendation(Map<String, dynamic> restaurant) async {
    final firebaseUser = FirebaseAuth.instance.currentUser;
    if (firebaseUser == null) {
      BeautifulSnackbar.showWarning(context, 'Please sign in to save recommendations');
      return;
    }

    final establishmentId = restaurant['id']?.toString() ?? restaurant['establishment'];
    if (establishmentId == null) return;

    final isCurrentlyLoved = _lovedRecommendationEstablishmentIds.contains(establishmentId);

    setState(() {
      if (isCurrentlyLoved) {
        _lovedRecommendationEstablishmentIds.remove(establishmentId);
      } else {
        _lovedRecommendationEstablishmentIds.add(establishmentId);
      }
    });

    try {
      final supabase = Supabase.instance.client;
      if (isCurrentlyLoved) {
        await supabase.from('reccomendation_loves').delete().match({
          'user_id': firebaseUser.uid,
          'establishment_id': establishmentId,
        });
      } else {
        await supabase.from('reccomendation_loves').insert({
          'user_id': firebaseUser.uid,
          'establishment_id': establishmentId,
          'establishment_name': restaurant['establishment'],
          'cuisine': restaurant['cuisine'],
          'neighborhood': restaurant['neighborhood'],
        });
      }

      if (mounted) {
        if (isCurrentlyLoved) {
          BeautifulSnackbar.showError(context, 'Removed from saved places');
        } else {
          BeautifulSnackbar.showSuccess(context, '✨ ${restaurant['establishment']} saved successfully! 💚');
        }
      }
    } catch (e) {
      setState(() {
        if (isCurrentlyLoved) {
          _lovedRecommendationEstablishmentIds.add(establishmentId);
        } else {
          _lovedRecommendationEstablishmentIds.remove(establishmentId);
        }
      });
      if (mounted) {
        BeautifulSnackbar.showError(context, 'Error saving: $e');
      }
    }
  }

  void _onSearchChanged(String query) {
    _debounceTimer?.cancel();
    if (query.trim().isEmpty) {
      setState(() {
        _results = [];
        _hasSearched = false;
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _hasSearched = true;
    });

    _debounceTimer = Timer(const Duration(milliseconds: 500), () {
      _performSearch(query);
    });
  }

  Future<void> _performSearch(String query) async {
    if (query.trim().isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _hasSearched = true;
      _currentOffset = 0;
      _canLoadMore = true;
    });

    try {
      final results = await _apiService.searchRestaurants(
        query: query,
        limit: _limit,
        offset: 0,
      );
      if (mounted) {
        setState(() {
          _results = results;
          _isLoading = false;
          _currentOffset = results.length;
          if (results.length < _limit) {
            _canLoadMore = false;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to search curated restaurants.';
          _isLoading = false;
          _results = [];
        });
      }
    }
  }

  Future<void> _loadMore() async {
    final query = _searchController.text;
    if (query.trim().isEmpty || _isLoadingMore || !_canLoadMore) return;

    setState(() {
      _isLoadingMore = true;
    });

    try {
      final nextResults = await _apiService.searchRestaurants(
        query: query,
        limit: _limit,
        offset: _currentOffset,
      );

      if (mounted) {
        setState(() {
          _results.addAll(nextResults);
          _isLoadingMore = false;
          _currentOffset += nextResults.length;
          if (nextResults.length < _limit) {
            _canLoadMore = false;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoadingMore = false;
        });
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
            _buildSearchHeader(),
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
          IconButton(
            icon: const Icon(Icons.arrow_back, color: PlanditColors.foreground),
            onPressed: () => Navigator.pop(context),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          const SizedBox(width: 12),
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
                  const Icon(Icons.restaurant_menu, color: PlanditColors.mutedForeground, size: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      autofocus: true,
                      decoration: const InputDecoration(
                        hintText: 'Search curated spots...',
                        hintStyle: TextStyle(color: PlanditColors.mutedForeground, fontSize: 14),
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: EdgeInsets.zero,
                      ),
                      style: const TextStyle(color: PlanditColors.foreground, fontSize: 14),
                      onChanged: _onSearchChanged,
                      onSubmitted: _performSearch,
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

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: PlanditColors.accent),
            SizedBox(height: 16),
            Text('Browsing our curated guides...', style: TextStyle(color: PlanditColors.mutedForeground)),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.redAccent),
              const SizedBox(height: 16),
              Text(_errorMessage!, textAlign: TextAlign.center, style: const TextStyle(color: PlanditColors.foreground)),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => _performSearch(_searchController.text),
                child: const Text('Retry Search'),
              ),
            ],
          ),
        ),
      );
    }

    if (!_hasSearched) {
      return _buildEmptyState();
    }

    if (_results.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.search_off, size: 48, color: PlanditColors.mutedForeground),
            const SizedBox(height: 16),
            const Text('No curated spots found matching your query.', style: TextStyle(color: PlanditColors.mutedForeground)),
            const SizedBox(height: 8),
            const Text('Try searching by neighborhood or cuisine.', style: TextStyle(color: PlanditColors.mutedForeground, fontSize: 12)),
          ],
        ),
      );
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Text(
                '${_results.length} CURATED SPOTS FOUND',
                style: GoogleFonts.mulish(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  color: PlanditColors.mutedForeground,
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.all(16),
            itemCount: _results.length + (_isLoadingMore ? 1 : 0),
            itemBuilder: (context, index) {
              if (index == _results.length) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 32),
                  child: Center(
                    child: CircularProgressIndicator(
                      color: PlanditColors.accent,
                      strokeWidth: 2,
                    ),
                  ),
                );
              }
              final restaurant = _results[index];
              return _buildRestaurantCard(restaurant);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Curated Discovery',
            style: GoogleFonts.playfairDisplay(fontSize: 24, fontWeight: FontWeight.w400),
          ),
          const SizedBox(height: 8),
          const Text('Search through our hand-picked restaurant guides.'),
          const SizedBox(height: 32),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: _suggestedSearches.map((s) => _buildSuggestionChip(s)).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSuggestionChip(Map<String, String> item) {
    final label = item['label'] ?? '';
    final emoji = item['emoji'] ?? '';
    
    return GestureDetector(
      onTap: () {
        if (label.isNotEmpty) {
          _searchController.text = label;
          _performSearch(label);
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: PlanditColors.secondary.withOpacity(0.8),
          borderRadius: BorderRadius.circular(100),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 6),
            Text(
              label, 
              style: GoogleFonts.mulish(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: PlanditColors.mutedForeground,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRestaurantCard(Map<String, dynamic> restaurant) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: PlanditColors.shadowSoft,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // If we had images in analysis table, we'd add them here
          // For now, a stylized header with info
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            color: PlanditColors.secondary.withOpacity(0.05),
            child: Row(
              children: [
                const Icon(Icons.restaurant, size: 14, color: PlanditColors.accentGold),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    restaurant['cuisine'] ?? 'Cuisine',
                    style: GoogleFonts.mulish(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: PlanditColors.accentGold,
                      letterSpacing: 0.5,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 12),
                if (restaurant['neighborhood'] != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: PlanditColors.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(100),
                    ),
                    child: Text(
                      restaurant['neighborhood'],
                      style: GoogleFonts.mulish(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: PlanditColors.primary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        restaurant['establishment'] ?? 'Unknown Restaurant',
                        style: GoogleFonts.playfairDisplay(
                          fontSize: 22,
                          fontWeight: FontWeight.w400,
                          color: PlanditColors.foreground,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    GestureDetector(
                      onTap: () => _toggleLoveRecommendation(restaurant),
                      child: Icon(
                        _lovedRecommendationEstablishmentIds.contains(restaurant['id']?.toString() ?? restaurant['establishment'])
                            ? Icons.favorite
                            : Icons.favorite_border,
                        color: _lovedRecommendationEstablishmentIds.contains(restaurant['id']?.toString() ?? restaurant['establishment'])
                            ? Colors.red
                            : PlanditColors.mutedForeground,
                        size: 24,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (restaurant['vibe'] != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                      children: [
                        const Icon(Icons.auto_awesome_outlined, size: 14, color: PlanditColors.mutedForeground),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            restaurant['vibe'],
                            style: GoogleFonts.mulish(
                              fontSize: 13,
                              color: PlanditColors.mutedForeground,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                if (restaurant['app_ready_description'] != null)
                  Text(
                    restaurant['app_ready_description'],
                    style: GoogleFonts.mulish(
                      fontSize: 14,
                      color: PlanditColors.mutedForeground,
                      height: 1.5,
                    ),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                  ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (restaurant['primary_draw'] != null)
                      Flexible(
                        child: _buildMiniBadge(restaurant['primary_draw']),
                      ),
                    const SizedBox(width: 12),
                    GestureDetector(
                      onTap: () async {
                        final name = restaurant['establishment'] ?? 'Unknown Restaurant';
                        final query = Uri.encodeComponent('$name NYC');
                        final url = Uri.parse('https://www.google.com/maps/search/?api=1&query=$query');
                        if (await canLaunchUrl(url)) {
                          await launchUrl(url, mode: LaunchMode.externalApplication);
                        } else {
                          if (mounted) {
                            BeautifulSnackbar.showError(context, 'Could not open maps');
                          }
                        }
                      },
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.map_outlined, size: 14, color: PlanditColors.primary),
                          const SizedBox(width: 6),
                          Text(
                            'VIEW ON MAPS',
                            style: GoogleFonts.mulish(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: PlanditColors.primary,
                              letterSpacing: 1,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMiniBadge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: PlanditColors.background,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: PlanditColors.border.withOpacity(0.5)),
      ),
      child: Text(
        text.toUpperCase(),
        style: GoogleFonts.mulish(
          fontSize: 10,
          fontWeight: FontWeight.bold,
          color: PlanditColors.mutedForeground,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}
