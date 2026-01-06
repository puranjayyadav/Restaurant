import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:share_plus/share_plus.dart';
import '../api_service.dart';
import '../widgets/user_profile_card.dart';
import '../widgets/like_button.dart';

class PublicItineraryDetailScreen extends StatefulWidget {
  final String itineraryId;
  final Map<String, dynamic>? itinerary;

  const PublicItineraryDetailScreen({
    Key? key,
    required this.itineraryId,
    this.itinerary,
  }) : super(key: key);

  @override
  State<PublicItineraryDetailScreen> createState() =>
      _PublicItineraryDetailScreenState();
}

class _PublicItineraryDetailScreenState
    extends State<PublicItineraryDetailScreen> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic>? _itinerary;
  bool _isLoading = true;
  bool _isAddingToSchedule = false;

  @override
  void initState() {
    super.initState();
    _itinerary = widget.itinerary;
    if (_itinerary == null) {
      _loadItinerary();
    } else {
      _isLoading = false;
    }
  }

  Future<void> _loadItinerary() async {
    try {
      final result = await _apiService.getPublicItineraries(
        limit: 1,
        offset: 0,
      );

      if (result != null && mounted) {
        final itineraries = result['itineraries'] as List<dynamic>? ?? [];
        final found = itineraries.firstWhere(
          (it) => it['id'] == widget.itineraryId,
          orElse: () => null,
        );
        if (found != null && mounted) {
          setState(() {
            _itinerary = found as Map<String, dynamic>;
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      print('ERROR loading itinerary: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _shareItinerary() async {
    if (_itinerary == null) return;

    try {
      await _apiService.sharePublicItinerary(
        itineraryId: widget.itineraryId,
      );
      final shareText =
          'Check out this itinerary: ${_itinerary!['title']}\n${_itinerary!['description']}';
      await Share.share(shareText);
    } catch (e) {
      print('ERROR sharing itinerary: $e');
      if (mounted) {
        ShadToaster.of(context).show(
          ShadToast.destructive(
            title: const Text('Error'),
            description: Text('Failed to share: $e'),
          ),
        );
      }
    }
  }

  Future<void> _addToSchedule() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      ShadToaster.of(context).show(
        const ShadToast.destructive(
          title: Text('Authentication required'),
          description:
              Text('Please sign in to add itineraries to your schedule'),
        ),
      );
      return;
    }

    setState(() {
      _isAddingToSchedule = true;
    });

    try {
      final result = await _apiService.addPublicItineraryToSchedule(
        itineraryId: widget.itineraryId,
        userId: user.uid,
      );

      if (result != null && mounted) {
        ShadToaster.of(context).show(
          const ShadToast(
            title: Text('Success!'),
            description: Text('Itinerary added to your schedule'),
          ),
        );
      } else {
        if (mounted) {
          ShadToaster.of(context).show(
            const ShadToast.destructive(
              title: Text('Error'),
              description: Text('Failed to add itinerary to schedule'),
            ),
          );
        }
      }
    } catch (e) {
      print('ERROR adding to schedule: $e');
      if (mounted) {
        ShadToaster.of(context).show(
          ShadToast.destructive(
            title: const Text('Error'),
            description: Text('Failed to add to schedule: $e'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isAddingToSchedule = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Itinerary Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_itinerary == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Itinerary Details')),
        body: const Center(child: Text('Itinerary not found')),
      );
    }

    final items = _itinerary!['items'] as List<dynamic>? ?? [];
    final userStats = _itinerary!['user_stats'] as Map<String, dynamic>? ?? {};

    return Scaffold(
      appBar: AppBar(
        title: const Text('Itinerary Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: _shareItinerary,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // User Profile Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: UserProfileCard(
                  userName: _itinerary!['user_name'] as String? ?? 'Anonymous',
                  userPhotoUrl: _itinerary!['user_photo_url'] as String?,
                  totalPublicItineraries:
                      userStats['total_public_itineraries'] as int? ?? 0,
                  totalLikesReceived:
                      userStats['total_likes_received'] as int? ?? 0,
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Title
            Text(
              _itinerary!['title'] as String? ?? 'Untitled',
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            // Description
            Text(
              _itinerary!['description'] as String? ?? '',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 16),
            // Location and Categories
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Chip(
                  label: Text(_itinerary!['location'] as String? ?? 'Unknown'),
                  avatar: const Icon(Icons.location_on, size: 16),
                ),
                ...((_itinerary!['categories'] as List<dynamic>? ?? [])
                    .map((cat) => Chip(
                          label: Text(cat.toString()),
                        ))),
              ],
            ),
            const SizedBox(height: 24),
            // Actions Row
            Row(
              children: [
                Expanded(
                  child: LikeButton(
                    itineraryId: widget.itineraryId,
                    initialLikesCount: _itinerary!['likes_count'] as int? ?? 0,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 2,
                  child: ElevatedButton.icon(
                    onPressed: _isAddingToSchedule ? null : _addToSchedule,
                    icon: _isAddingToSchedule
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.add),
                    label: const Text('Add to Schedule'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            // Itinerary Items
            const Text(
              'Places',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...items.asMap().entries.map((entry) {
              final index = entry.key;
              final item = entry.value as Map<String, dynamic>;
              return _ItineraryItemCard(
                item: item,
                index: index,
                isLast: index == items.length - 1,
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _ItineraryItemCard extends StatelessWidget {
  final Map<String, dynamic> item;
  final int index;
  final bool isLast;

  const _ItineraryItemCard({
    Key? key,
    required this.item,
    required this.index,
    required this.isLast,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final photos = item['photos'] as List<dynamic>? ?? [];
    final photoUrl = photos.isNotEmpty
        ? (photos[0]['url'] as String? ??
            (photos[0]['photo_reference'] != null
                ? 'https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${photos[0]['photo_reference']}&key=YOUR_API_KEY'
                : null))
        : null;

    return Card(
      margin: EdgeInsets.only(bottom: isLast ? 0 : 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Time Slot
            Column(
              children: [
                Text(
                  item['start_time']?.toString() ?? '',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (!isLast)
                  Container(
                    width: 2,
                    height: 60,
                    color: Colors.grey[300],
                  ),
              ],
            ),
            const SizedBox(width: 16),
            // Place Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item['place_name']?.toString() ?? 'Unknown',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item['address']?.toString() ?? '',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                    ),
                  ),
                  if (item['distance_from_previous'] != null && index > 0) ...[
                    const SizedBox(height: 4),
                    Text(
                      '${item['distance_from_previous']} km from previous',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[500],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            // Photo
            if (photoUrl != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  photoUrl,
                  width: 60,
                  height: 60,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => Container(
                    width: 60,
                    height: 60,
                    color: Colors.grey[300],
                    child: const Icon(Icons.image_not_supported),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
