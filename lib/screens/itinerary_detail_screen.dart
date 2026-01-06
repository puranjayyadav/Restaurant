import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../scout_mode_screen.dart';
import '../widgets/route_map_widget.dart';

/// Plandit V2 detail experience: cinematic header, living timeline,
/// and floating "Start Adventure" island.
class ItineraryDetailScreen extends StatelessWidget {
  final Map<String, dynamic> itinerary;

  const ItineraryDetailScreen({
    super.key,
    required this.itinerary,
  });

  List<Map<String, dynamic>> get _stops {
    final data = itinerary['itinerary_data'];
    if (data is Map) {
      final list = data['itinerary'];
      if (list is List) {
        return list
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
            .toList();
      }
    }
    // Fallback to items key if itinerary_data is missing
    final items = itinerary['items'];
    if (items is List) {
      return items
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
          .toList();
    }
    return const <Map<String, dynamic>>[];
  }

  Map<String, dynamic> get _routeStats {
    final data = itinerary['itinerary_data'];
    if (data is Map) {
      final stats = data['route_stats'];
      if (stats is Map) {
        return Map<String, dynamic>.from(stats.cast<String, dynamic>());
      }
    }
    return const {};
  }

  String _title() =>
      itinerary['new_title']?.toString() ??
      itinerary['title']?.toString() ??
      'Itinerary';

  String _subtitle() =>
      itinerary['subtitle']?.toString().trim() ??
      itinerary['description']?.toString().trim() ??
      '';

  String _vibeTag() {
    final tags = itinerary['tags'];
    if (tags is List && tags.isNotEmpty) {
      final tag = tags.first.toString();
      if (tag.isNotEmpty) return tag;
    }
    final cuisine = itinerary['cuisine']?.toString();
    if (cuisine != null && cuisine.isNotEmpty) return cuisine;
    return itinerary['neighborhood']?.toString() ?? '';
  }

  String? _heroImageUrl() {
    try {
      // Prefer explicit sample image
      final sample = itinerary['sample_image_url'];
      if (sample != null) {
        final url = sample.toString().trim();
        if (url.startsWith('http')) return url;
      }

      // Fall back to first photo in stops
      for (final stop in _stops) {
        final postgres = stop['postgres_data'];
        if (postgres is Map) {
          final photos = postgres['photos'];
          if (photos is List && photos.isNotEmpty) {
            final first = photos.first;
            if (first is String && first.startsWith('http')) return first;
            if (first is Map) {
              final url = first['url']?.toString();
              if (url != null && url.startsWith('http')) return url;
            }
          }
        }
        final photos = stop['photos'];
        if (photos is List && photos.isNotEmpty) {
          final first = photos.first;
          if (first is String && first.startsWith('http')) return first;
          if (first is Map) {
            final url = first['url']?.toString();
            if (url != null && url.startsWith('http')) return url;
          }
        }
      }
    } catch (e) {
      print('ERROR: Exception in _heroImageUrl: $e');
    }
    return null;
  }

  double _estimatedHours() => (_stops.length * 1.5).clamp(1, 12).toDouble();

  double _estimatedDistanceMiles() {
    final rawTotalKm = _routeStats['total_distance_km'];
    final totalKm = (rawTotalKm is num)
        ? rawTotalKm.toDouble()
        : double.tryParse(rawTotalKm?.toString() ?? '');
    if (totalKm != null) return (totalKm * 0.621371);
    // fallback: 0.6 miles per gap
    return ((_stops.length - 1) * 0.6).clamp(0, 25).toDouble();
  }

  String _priceRange() {
    if (_stops.isEmpty) return '\$';
    int maxPrice = 1;
    for (final stop in _stops) {
      final price = stop['price_range']?.toString() ?? '';
      final dollars = price.split('\$').length - 1;
      if (dollars > maxPrice) maxPrice = dollars;
    }
    return '\$' * maxPrice;
  }

  String _formattedTimeForStop(int index, Map<String, dynamic> stop) {
    final raw = stop['start_time']?.toString();
    if (raw != null && raw.trim().isNotEmpty) {
      try {
        final normalized = raw.replaceAll('\n', ' ').trim();
        final parsed = DateFormat.jm().parse(normalized);
        final formatted = DateFormat('h:mm a').format(parsed).split(' ');
        return '${formatted[0]}\n${formatted.length > 1 ? formatted[1].toUpperCase() : ''}';
      } catch (_) {
        final parts = raw.split(' ');
        if (parts.length >= 2)
          return '${parts[0]}\n${parts.sublist(1).join(' ').toUpperCase()}';
        return raw;
      }
    }
    final base = DateTime(2024, 1, 1, 19).add(Duration(minutes: 80 * index));
    final formatted = DateFormat('h:mm a').format(base).split(' ');
    return '${formatted[0]}\n${formatted.length > 1 ? formatted[1].toUpperCase() : ''}';
  }

  String _categoryForStop(Map<String, dynamic> stop) {
    final postgresData = stop['postgres_data'];
    
    // Priority 1: category_normalized from postgres_data (most accurate)
    if (postgresData is Map) {
      final categoryNormalized = postgresData['category_normalized'];
      if (categoryNormalized is String && categoryNormalized.trim().isNotEmpty && categoryNormalized.toLowerCase() != 'general') {
        return categoryNormalized;
      }
      
      // Priority 2: category from postgres_data
      final category = postgresData['category'];
      if (category is String && category.trim().isNotEmpty && category.toLowerCase() != 'general') {
        return category;
      }
    }
    
    // Priority 3: Direct category field from stop
    final stopCategory = stop['category'];
    if (stopCategory is String && stopCategory.trim().isNotEmpty && stopCategory.toLowerCase() != 'general') {
      return stopCategory;
    }
    
    // Priority 4: Extract from types array (clean up underscores and make readable)
    final postgresTypes = postgresData is Map ? postgresData['types'] : null;
    if (postgresTypes is List && postgresTypes.isNotEmpty) {
      final firstType = postgresTypes.first.toString();
      // Clean up common type formats
      final cleaned = firstType
          .replaceAll('_', ' ')
          .replaceAll('restaurant', '')
          .replaceAll('establishment', '')
          .trim();
      if (cleaned.isNotEmpty) {
        return cleaned;
      }
    }
    
    // Priority 5: Other stop fields
    final candidates = [
      stop['vibe'],
      stop['type'],
      stop['tag'],
    ];
    
    for (final candidate in candidates) {
      if (candidate is String && candidate.trim().isNotEmpty && candidate.toLowerCase() != 'explore' && candidate.toLowerCase() != 'general') {
        return candidate;
      }
    }
    
    return 'Place';
  }

  String _noteForStop(Map<String, dynamic> stop) {
    final candidates = [
      stop['tip'],
      stop['insider_tip'],
      stop['notes'],
      stop['note'],
      stop['description'],
    ];
    for (final candidate in candidates) {
      if (candidate is String && candidate.trim().isNotEmpty) {
        return candidate.trim();
      }
    }
    return 'Order the house favorite and ask for the local secret.';
  }

  int _walkMinutesBetween(int index) {
    final nextStop = index + 1 < _stops.length ? _stops[index + 1] : null;
    final candidates = [
      nextStop?['walk_time_minutes'],
      nextStop?['duration_from_previous_min'],
      nextStop?['duration_from_previous_minutes'],
    ];
    for (final c in candidates) {
      if (c is num) return c.round().clamp(2, 60);
      if (c is String) {
        final parsed = num.tryParse(c.replaceAll(RegExp(r'[^0-9.]'), ''));
        if (parsed != null) return parsed.round().clamp(2, 60);
      }
    }

    final segmentDurations = _asNumList(_routeStats['segment_durations_min']);
    if (segmentDurations != null && index < segmentDurations.length) {
      return segmentDurations[index].round().clamp(2, 60);
    }

    return 8 + (index % 4) * 2;
  }

  String _walkDistanceBetween(int index) {
    final nextStop = index + 1 < _stops.length ? _stops[index + 1] : null;
    final candidates = [
      nextStop?['distance_from_previous'],
      nextStop?['distance_from_previous_miles'],
      nextStop?['distance_from_previous_km'],
    ];
    for (final c in candidates) {
      if (c is num) {
        final miles = c.toDouble();
        return miles < 5
            ? '${miles.toStringAsFixed(1)} mi'
            : '${(miles * 0.621371).toStringAsFixed(1)} mi';
      }
      if (c is String && c.trim().isNotEmpty) {
        final lower = c.toLowerCase();
        final parsed = num.tryParse(lower.replaceAll(RegExp(r'[^0-9.]'), ''));
        if (parsed != null) {
          final isKm = lower.contains('km');
          final miles = isKm ? parsed * 0.621371 : parsed;
          return '${miles.toStringAsFixed(1)} mi';
        }
        return c;
      }
    }

    final segmentDistances = _asNumList(_routeStats['segment_distances_km']);
    if (segmentDistances != null && index < segmentDistances.length) {
      final miles = segmentDistances[index] * 0.621371;
      return '${miles.toStringAsFixed(1)} mi';
    }

    return '${(0.5 + index * 0.15).toStringAsFixed(1)} mi';
  }

  List<double>? _asNumList(dynamic value) {
    if (value is List) {
      final list = <double>[];
      for (final v in value) {
        if (v is num) list.add(v.toDouble());
        if (v is String) {
          final parsed = num.tryParse(v);
          if (parsed != null) list.add(parsed.toDouble());
        }
      }
      return list;
    }
    return null;
  }

  void _startItinerary(BuildContext context) {
    final data = itinerary['itinerary_data'] as Map<String, dynamic>? ?? {};
    final rawStops = (data['itinerary'] as List<dynamic>?) ?? _stops;
    final initialStops = rawStops
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
        .toList();
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ScoutModeScreen(
          initialItinerary: initialStops,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final heroImageUrl = _heroImageUrl();
    final vibe = _vibeTag();
    final subtitle = _subtitle();

    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        children: [
          CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 450,
                pinned: true,
                backgroundColor: Colors.white,
                elevation: 0,
                surfaceTintColor: Colors.white,
                leading: Container(
                  margin: const EdgeInsets.all(8),
                  decoration: const BoxDecoration(
                    color: Colors.black26,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.arrow_back, color: Colors.white),
                    onPressed: () => Navigator.pop(context),
                  ),
                ),
                flexibleSpace: FlexibleSpaceBar(
                  background: Stack(
                    fit: StackFit.expand,
                    children: [
                      heroImageUrl != null
                          ? Image.network(
                              heroImageUrl,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) =>
                                  _buildPlaceholderHero(),
                            )
                          : _buildPlaceholderHero(),
                      Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              Colors.transparent,
                              Colors.black.withOpacity(0.8),
                            ],
                            stops: const [0.5, 1.0],
                          ),
                        ),
                      ),
                      Positioned(
                        bottom: 30,
                        left: 24,
                        right: 24,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (vibe.isNotEmpty)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: Colors.white30),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.local_bar,
                                        color: Colors.white, size: 14),
                                    const SizedBox(width: 6),
                                    Text(
                                      vibe,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            const SizedBox(height: 16),
                            Text(
                              _title(),
                              style: GoogleFonts.playfairDisplay(
                                fontSize: 42,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                                height: 1.1,
                              ),
                            ),
                            const SizedBox(height: 12),
                            if (subtitle.isNotEmpty)
                              Text(
                                subtitle,
                                style: const TextStyle(
                                  color: Colors.white70,
                                  fontSize: 15,
                                  height: 1.4,
                                ),
                                maxLines: 2,
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SliverPersistentHeader(
                pinned: true,
                delegate: _StickyStatsDelegate(
                  durationLabel:
                      '${_estimatedHours().toStringAsFixed(1)} Hours',
                  distanceLabel:
                      '${_estimatedDistanceMiles().toStringAsFixed(1)} Miles',
                  priceLabel: _priceRange().isNotEmpty ? _priceRange() : '\$\$',
                ),
              ),
              // Route Map Section
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 16, 24, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Your Route',
                        style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        height: 220,
                        child: RouteMapWidget(stops: _stops),
                      ),
                    ],
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(24, 10, 24, 140),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    const Text(
                      'Living Timeline',
                      style:
                          TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 32),
                    if (_stops.isEmpty)
                      const Text(
                        'No stops yet — come back soon.',
                        style: TextStyle(color: Colors.grey),
                      )
                    else
                      ..._buildTimeline(),
                  ]),
                ),
              ),
            ],
          ),
          Positioned(
            bottom: 40,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: const Color(0xFF1A1A1A),
                borderRadius: BorderRadius.circular(32),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.3),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
                title: const Text(
                  'Start Adventure',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                subtitle: Text(
                  '${_stops.length} stops • ${_estimatedDistanceMiles().toStringAsFixed(1)} mi to first stop',
                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                ),
                trailing: const Icon(Icons.arrow_forward_ios,
                    color: Colors.white, size: 16),
                onTap: () => _startItinerary(context),
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildTimeline() {
    final widgets = <Widget>[];
    for (var i = 0; i < _stops.length; i++) {
      final stop = _stops[i];
      widgets.add(_buildTimelineItem(
        time: _formattedTimeForStop(i, stop),
        title: stop['place_name']?.toString() ??
            stop['name']?.toString() ??
            'Untitled',
        category: _categoryForStop(stop),
        note: _noteForStop(stop),
        isFirst: i == 0,
        isLast: i == _stops.length - 1,
      ));
      if (i != _stops.length - 1) {
        widgets.add(_buildWalkingGap(
          minutes: _walkMinutesBetween(i),
          distance: _walkDistanceBetween(i),
          showAddStop: i == 0 || i == _stops.length - 2,
        ));
      }
    }
    return widgets;
  }

  Widget _buildTimelineItem({
    required String time,
    required String title,
    required String category,
    required String note,
    bool isFirst = false,
    bool isLast = false,
  }) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 50,
            child: Text(
              time,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: Color(0xFF64748B),
                height: 1.2,
              ),
              textAlign: TextAlign.center,
            ),
          ),
          Column(
            children: [
              Container(
                width: 2,
                height: 20,
                decoration: BoxDecoration(
                  color: isFirst ? Colors.transparent : Colors.grey[200],
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
              Container(
                width: 12,
                height: 12,
                decoration: const BoxDecoration(
                  color: Color(0xFF333333),
                  shape: BoxShape.circle,
                ),
              ),
              Expanded(
                child: Container(
                  width: 2,
                  decoration: BoxDecoration(
                    color: isLast ? Colors.transparent : Colors.grey[200],
                    borderRadius: BorderRadius.circular(6),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 30),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Flexible(
                        child: Text(
                          title,
                          style: GoogleFonts.playfairDisplay(
                            fontSize: 24,
                            fontWeight: FontWeight.w600,
                            color: const Color(0xFF1A1A1A),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1A1A1A),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          category.toUpperCase(),
                          style: const TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF3F4F6),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      note,
                      style: const TextStyle(
                        color: Color(0xFF4B5563),
                        height: 1.5,
                        fontSize: 14,
                      ),
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

  Widget _buildWalkingGap({
    required int minutes,
    required String distance,
    bool showAddStop = true,
  }) {
    return Row(
      children: [
        const SizedBox(width: 50),
        SizedBox(
          width: 12,
          child: Column(
            children: List.generate(
              4,
              (index) => Container(
                width: 2,
                height: 4,
                color: Colors.grey[300],
                margin: const EdgeInsets.symmetric(vertical: 2),
              ),
            ),
          ),
        ),
        const SizedBox(width: 20),
        Container(
          margin: const EdgeInsets.symmetric(vertical: 16),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[300]!),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            children: [
              Icon(Icons.directions_walk, size: 16, color: Colors.grey[600]),
              const SizedBox(width: 8),
              Text(
                '$minutes min walk ($distance)',
                style: TextStyle(
                  color: Colors.grey[700],
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
              if (showAddStop) ...[
                Container(
                  height: 12,
                  width: 1,
                  color: Colors.grey[300],
                  margin: const EdgeInsets.symmetric(horizontal: 10),
                ),
                const Text(
                  'Add stop?',
                  style: TextStyle(
                    color: Colors.blue,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPlaceholderHero() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFFF1E6), Color(0xFFE6F3FF)],
        ),
      ),
      child: const Center(
        child: Icon(
          Icons.restaurant_menu,
          size: 80,
          color: Colors.white70,
        ),
      ),
    );
  }
}

class _StickyStatsDelegate extends SliverPersistentHeaderDelegate {
  final String durationLabel;
  final String distanceLabel;
  final String priceLabel;

  _StickyStatsDelegate({
    required this.durationLabel,
    required this.distanceLabel,
    required this.priceLabel,
  });

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    final height = maxExtent;
    return SizedBox(
      height: height,
      child: Container(
        color: Colors.white.withOpacity(0.95),
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildStat(Icons.schedule, durationLabel),
            Container(
                height: 16,
                width: 1,
                color: Colors.grey[300],
                margin: const EdgeInsets.symmetric(horizontal: 24)),
            _buildStat(Icons.directions_walk, distanceLabel),
            Container(
                height: 16,
                width: 1,
                color: Colors.grey[300],
                margin: const EdgeInsets.symmetric(horizontal: 24)),
            _buildStat(Icons.payments_outlined, priceLabel),
          ],
        ),
      ),
    );
  }

  Widget _buildStat(IconData icon, String text) => Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey[600]),
          const SizedBox(width: 8),
          Text(
            text,
            style: TextStyle(
              fontFamily: 'SF Pro Display',
              fontWeight: FontWeight.w500,
              fontSize: 17,
              color: const Color(0xFF334155),
            ),
          ),
        ],
      );

  @override
  double get maxExtent => 70;

  @override
  double get minExtent => 70;

  @override
  bool shouldRebuild(covariant SliverPersistentHeaderDelegate oldDelegate) =>
      false;
}
