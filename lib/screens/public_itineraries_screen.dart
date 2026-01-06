import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../api_service.dart';
import '../widgets/user_profile_card.dart';
import '../widgets/like_button.dart';
import 'public_itinerary_detail_screen.dart';
import 'package:share_plus/share_plus.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

class PublicItinerariesScreen extends StatefulWidget {
  const PublicItinerariesScreen({Key? key}) : super(key: key);

  @override
  State<PublicItinerariesScreen> createState() =>
      _PublicItinerariesScreenState();
}

class _PublicItinerariesScreenState extends State<PublicItinerariesScreen> {
  final ApiService _apiService = ApiService();
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  List<dynamic> _itineraries = [];
  bool _isLoading = false;
  bool _hasMore = true;
  int _offset = 0;
  String _sortBy = 'recent';
  String? _locationFilter;
  List<String> _selectedCategories = [];

  final List<String> _availableCategories = [
    'restaurants',
    'cafes',
    'museums',
    'parks',
    'shopping',
    'bars',
    'dessert',
  ];

  @override
  void initState() {
    super.initState();
    _loadItineraries();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent * 0.8 &&
        !_isLoading &&
        _hasMore) {
      _loadMoreItineraries();
    }
  }

  Future<void> _loadItineraries({bool refresh = false}) async {
    if (_isLoading) return;

    setState(() {
      _isLoading = true;
      if (refresh) {
        _offset = 0;
        _itineraries = [];
        _hasMore = true;
      }
    });

    try {
      final result = await _apiService.getPublicItineraries(
        location: _locationFilter,
        categories: _selectedCategories.isEmpty ? null : _selectedCategories,
        sort: _sortBy,
        limit: 20,
        offset: _offset,
      );

      if (result != null && mounted) {
        final newItineraries = result['itineraries'] as List<dynamic>? ?? [];
        setState(() {
          if (refresh) {
            _itineraries = newItineraries;
          } else {
            _itineraries.addAll(newItineraries);
          }
          _offset = _itineraries.length;
          _hasMore = newItineraries.length >= 20;
        });
      }
    } catch (e) {
      print('ERROR loading itineraries: $e');
      if (mounted) {
        ShadToaster.of(context).show(
          ShadToast.destructive(
            title: const Text('Error'),
            description: Text('Failed to load itineraries: $e'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadMoreItineraries() async {
    await _loadItineraries(refresh: false);
  }

  Future<void> _shareItinerary(Map<String, dynamic> itinerary) async {
    try {
      await _apiService.sharePublicItinerary(
        itineraryId: itinerary['id'] as String,
      );
      final shareText =
          'Check out this itinerary: ${itinerary['title']}\n${itinerary['description']}';
      await Share.share(shareText);
    } catch (e) {
      print('ERROR sharing itinerary: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Public Itineraries'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadItineraries(refresh: true),
          ),
        ],
      ),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search by location...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _locationFilter = null;
                          _loadItineraries(refresh: true);
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onSubmitted: (value) {
                _locationFilter = value.isEmpty ? null : value;
                _loadItineraries(refresh: true);
              },
            ),
          ),
          // Sort Options
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                const Text('Sort by: '),
                ChoiceChip(
                  label: const Text('Most Recent'),
                  selected: _sortBy == 'recent',
                  onSelected: (selected) {
                    if (selected) {
                      setState(() {
                        _sortBy = 'recent';
                      });
                      _loadItineraries(refresh: true);
                    }
                  },
                ),
                const SizedBox(width: 8),
                ChoiceChip(
                  label: const Text('Most Liked'),
                  selected: _sortBy == 'likes',
                  onSelected: (selected) {
                    if (selected) {
                      setState(() {
                        _sortBy = 'likes';
                      });
                      _loadItineraries(refresh: true);
                    }
                  },
                ),
              ],
            ),
          ),
          // Category Filters
          Padding(
            padding: const EdgeInsets.all(16),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _availableCategories.map((category) {
                final isSelected = _selectedCategories.contains(category);
                return FilterChip(
                  label: Text(category),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      if (selected) {
                        _selectedCategories.add(category);
                      } else {
                        _selectedCategories.remove(category);
                      }
                    });
                    _loadItineraries(refresh: true);
                  },
                );
              }).toList(),
            ),
          ),
          // Itineraries List
          Expanded(
            child: _itineraries.isEmpty && !_isLoading
                ? const Center(
                    child: Text('No itineraries found'),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: _itineraries.length + (_hasMore ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index >= _itineraries.length) {
                        return const Center(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: CircularProgressIndicator(),
                          ),
                        );
                      }

                      final itinerary = _itineraries[index];
                      return _ItineraryCard(
                        itinerary: itinerary,
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => PublicItineraryDetailScreen(
                                itineraryId: itinerary['id'] as String,
                                itinerary: itinerary,
                              ),
                            ),
                          ).then((_) {
                            // Refresh after returning from detail
                            _loadItineraries(refresh: true);
                          });
                        },
                        onShare: () => _shareItinerary(itinerary),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _ItineraryCard extends StatelessWidget {
  final Map<String, dynamic> itinerary;
  final VoidCallback onTap;
  final VoidCallback onShare;

  const _ItineraryCard({
    Key? key,
    required this.itinerary,
    required this.onTap,
    required this.onShare,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final items = itinerary['items'] as List<dynamic>? ?? [];
    final userStats = itinerary['user_stats'] as Map<String, dynamic>? ?? {};

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // User Profile
              UserProfileCard(
                userName: itinerary['user_name'] as String? ?? 'Anonymous',
                userPhotoUrl: itinerary['user_photo_url'] as String?,
                totalPublicItineraries:
                    userStats['total_public_itineraries'] as int? ?? 0,
                totalLikesReceived:
                    userStats['total_likes_received'] as int? ?? 0,
              ),
              const SizedBox(height: 16),
              // Title
              Text(
                itinerary['title'] as String? ?? 'Untitled',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              // Description
              Text(
                itinerary['description'] as String? ?? '',
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: Colors.grey[700]),
              ),
              const SizedBox(height: 12),
              // Location and Categories
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  Chip(
                    label: Text(itinerary['location'] as String? ?? 'Unknown'),
                    avatar: const Icon(Icons.location_on, size: 16),
                  ),
                  ...((itinerary['categories'] as List<dynamic>? ?? [])
                      .take(3)
                      .map((cat) => Chip(
                            label: Text(cat.toString()),
                            labelStyle: const TextStyle(fontSize: 12),
                          ))),
                ],
              ),
              const SizedBox(height: 12),
              // Preview of places
              if (items.isNotEmpty) ...[
                const Text(
                  'Places:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  items
                      .take(3)
                      .map((item) => item['place_name'] ?? 'Unknown')
                      .join(', '),
                  style: TextStyle(color: Colors.grey[600], fontSize: 12),
                ),
                if (items.length > 3)
                  Text(
                    ' +${items.length - 3} more',
                    style: TextStyle(color: Colors.grey[600], fontSize: 12),
                  ),
              ],
              const SizedBox(height: 12),
              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  LikeButton(
                    itineraryId: itinerary['id'] as String,
                    initialLikesCount: itinerary['likes_count'] as int? ?? 0,
                  ),
                  IconButton(
                    icon: const Icon(Icons.share),
                    onPressed: onShare,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
