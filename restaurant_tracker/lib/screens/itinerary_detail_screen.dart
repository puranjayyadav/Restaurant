import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../widgets/route_map_widget.dart';
import '../widgets/rich_venue_card.dart';
import '../widgets/inline_venue_search_panel.dart';
import '../widgets/beautiful_snackbar.dart';
import '../api_service.dart';

/// Plandit V2 detail experience: cinematic header, living timeline,
/// and floating "Start Adventure" island.
class ItineraryDetailScreen extends StatefulWidget {
  final Map<String, dynamic> itinerary;

  const ItineraryDetailScreen({
    super.key,
    required this.itinerary,
  });

  @override
  State<ItineraryDetailScreen> createState() => _ItineraryDetailScreenState();
}

class _ItineraryDetailScreenState extends State<ItineraryDetailScreen> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic>? _richItineraryData;
  bool _isLoadingRichData = false;
  bool _isRegenerating = false;
  late Map<String, dynamic> _currentItinerary;
  int? _expandedGapIndex; // Track which gap has the search panel expanded

  @override
  void initState() {
    super.initState();
    _currentItinerary = widget.itinerary;
    _fetchRichData();
  }

  /// Regenerate itinerary from a new starting point
  Future<void> _regenerateFromLocation(double lat, double lng) async {
    setState(() => _isRegenerating = true);

    try {
      // Extract current filters from the itinerary
      final itineraryData =
          _currentItinerary['itinerary_data'] as Map<String, dynamic>?;
      final selectedVibe = itineraryData?['selected_vibe'] ??
          _currentItinerary['selected_vibe'] ??
          'dinner_date';
      final socialContext = itineraryData?['social_context'] ??
          _currentItinerary['social_context'] ??
          'couple';
      final cuisinePreferences = itineraryData?['cuisine_preferences'] ??
          _currentItinerary['cuisine_preferences'];

      print('DEBUG: Regenerating itinerary from ($lat, $lng)');
      print(
          'DEBUG: Vibe: $selectedVibe, Social: $socialContext, Cuisine: $cuisinePreferences');

      // Call API to regenerate
      final newItinerary = await _apiService.generateItinerary(
        startLat: lat,
        startLong: lng,
        selectedVibe: selectedVibe?.toString() ?? 'dinner_date',
        socialContext: socialContext?.toString() ?? 'couple',
        cuisinePreferences: cuisinePreferences is List
            ? cuisinePreferences.map((e) => e.toString()).toList()
            : null,
        radiusMeters: 3000,
        localTimeStart: '19:00',
      );

      if (!mounted) return;

      // Update the current itinerary with new data
      setState(() {
        _currentItinerary = {
          ..._currentItinerary,
          'itinerary_data': newItinerary,
        };
        _richItineraryData = null;
        _isRegenerating = false;
      });

      // Fetch rich data for new stops
      _fetchRichData();

      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: const [
              Icon(Icons.check_circle, color: Colors.white),
              SizedBox(width: 12),
              Text('Itinerary regenerated from new location!'),
            ],
          ),
          backgroundColor: const Color(0xFF4CAF50),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      );
    } catch (e) {
      print('DEBUG: Regeneration error: $e');
      if (mounted) {
        setState(() => _isRegenerating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: const [
                Icon(Icons.error_outline, color: Colors.white),
                SizedBox(width: 12),
                Expanded(
                    child: Text(
                        'Failed to regenerate. Try a different location.')),
              ],
            ),
            backgroundColor: Colors.red[700],
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
        );
      }
    }
  }

  Future<void> _fetchRichData() async {
    setState(() => _isLoadingRichData = true);

    print('DEBUG: Fetching rich data for ${_stops.length} stops');

    // Extract place IDs from stops
    final placeIds = <String>[];
    for (final stop in _stops) {
      print('DEBUG: Stop data: ${stop.keys}');
      final placeId = stop['place_id']?.toString() ??
          stop['postgres_data']?['place_id']?.toString();
      print('DEBUG: Extracted place_id: $placeId');
      if (placeId != null && placeId.isNotEmpty) {
        placeIds.add(placeId);
      }
    }

    print('DEBUG: Collected ${placeIds.length} place IDs: $placeIds');

    if (placeIds.isNotEmpty) {
      final richData = await _apiService.fetchItineraryDetails(placeIds);
      print('DEBUG: Received rich data: ${richData != null ? "YES" : "NO"}');
      if (richData != null) {
        print('DEBUG: Rich data keys: ${richData.keys}');
        final venues = richData['venues'] as List<dynamic>?;
        print('DEBUG: Number of venues: ${venues?.length ?? 0}');
      }
      if (mounted) {
        setState(() {
          _richItineraryData = richData;
          _isLoadingRichData = false;
        });
      }
    } else {
      print('DEBUG: No place IDs found, skipping API call');
      setState(() => _isLoadingRichData = false);
    }
  }

  List<Map<String, dynamic>> get _stops {
    final data = _currentItinerary['itinerary_data'];
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
    final items = _currentItinerary['items'];
    if (items is List) {
      return items
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
          .toList();
    }
    return const <Map<String, dynamic>>[];
  }

  Map<String, dynamic> get _routeStats {
    final data = _currentItinerary['itinerary_data'];
    if (data is Map) {
      final stats = data['route_stats'];
      if (stats is Map) {
        return Map<String, dynamic>.from(stats.cast<String, dynamic>());
      }
    }
    return const {};
  }

  String _title() =>
      _currentItinerary['new_title']?.toString() ??
      _currentItinerary['title']?.toString() ??
      'Itinerary';

  String _subtitle() =>
      _currentItinerary['subtitle']?.toString().trim() ??
      _currentItinerary['description']?.toString().trim() ??
      '';

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

  String _calculateTimeForInsertPosition(int insertIndex, List<dynamic> stops) {
    // Calculate time based on position between stops
    if (stops.isEmpty) {
      return '10:00 AM';
    }
    
    if (insertIndex < 0) {
      insertIndex = 0;
    }
    if (insertIndex >= stops.length) {
      insertIndex = stops.length - 1;
    }
    
    // Get the time from the stop before the insertion point
    String? beforeTime;
    if (insertIndex >= 0 && insertIndex < stops.length) {
      final beforeStop = stops[insertIndex] as Map<String, dynamic>?;
      beforeTime = beforeStop?['start_time']?.toString();
    }
    
    // Get the time from the stop after the insertion point
    String? afterTime;
    if (insertIndex + 1 < stops.length) {
      final afterStop = stops[insertIndex + 1] as Map<String, dynamic>?;
      afterTime = afterStop?['start_time']?.toString();
    }
    
    // Try to parse and calculate midpoint time
    try {
      DateTime? beforeDateTime;
      DateTime? afterDateTime;
      
      if (beforeTime != null && beforeTime.trim().isNotEmpty) {
        beforeDateTime = DateFormat.jm().parse(beforeTime.replaceAll('\n', ' ').trim());
      }
      if (afterTime != null && afterTime.trim().isNotEmpty) {
        afterDateTime = DateFormat.jm().parse(afterTime.replaceAll('\n', ' ').trim());
      }
      
      if (beforeDateTime != null && afterDateTime != null) {
        // Calculate midpoint between two times
        final diff = afterDateTime.difference(beforeDateTime);
        final midpoint = beforeDateTime.add(Duration(milliseconds: diff.inMilliseconds ~/ 2));
        return DateFormat('h:mm a').format(midpoint);
      } else if (beforeDateTime != null) {
        // Add 1.5 hours after the previous stop
        final nextTime = beforeDateTime.add(const Duration(hours: 1, minutes: 30));
        return DateFormat('h:mm a').format(nextTime);
      } else if (afterDateTime != null) {
        // Subtract 1.5 hours before the next stop
        final prevTime = afterDateTime.subtract(const Duration(hours: 1, minutes: 30));
        return DateFormat('h:mm a').format(prevTime);
      }
    } catch (e) {
      // Fall through to default calculation
    }
    
    // Default: calculate based on index (1.5 hours per stop)
    final base = DateTime(2024, 1, 1, 10).add(Duration(minutes: 90 * (insertIndex + 1)));
    return DateFormat('h:mm a').format(base);
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
      if (categoryNormalized is String &&
          categoryNormalized.trim().isNotEmpty &&
          categoryNormalized.toLowerCase() != 'general') {
        return categoryNormalized;
      }

      // Priority 2: category from postgres_data
      final category = postgresData['category'];
      if (category is String &&
          category.trim().isNotEmpty &&
          category.toLowerCase() != 'general') {
        return category;
      }
    }

    // Priority 3: Direct category field from stop
    final stopCategory = stop['category'];
    if (stopCategory is String &&
        stopCategory.trim().isNotEmpty &&
        stopCategory.toLowerCase() != 'general') {
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
      if (candidate is String &&
          candidate.trim().isNotEmpty &&
          candidate.toLowerCase() != 'explore' &&
          candidate.toLowerCase() != 'general') {
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

  @override
  Widget build(BuildContext context) {
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
                      // Map header - long press to regenerate from new location
                      RouteMapWidget(
                        stops: _stops,
                        routeStats: _routeStats,
                        lightTheme: true,
                        borderRadius: 0,
                        onLongPressLocation: _regenerateFromLocation,
                      ),
                      // Regenerating overlay
                      if (_isRegenerating)
                        Container(
                          color: Colors.black.withOpacity(0.5),
                          child: Center(
                            child: Container(
                              padding: const EdgeInsets.all(24),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(16),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withOpacity(0.2),
                                    blurRadius: 20,
                                  ),
                                ],
                              ),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const CircularProgressIndicator(
                                    color: Color(0xFFD4AF37),
                                    strokeWidth: 3,
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    'Regenerating itinerary...',
                                    style: GoogleFonts.mulish(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      IgnorePointer(
                        child: Container(
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
                      ),
                      // Living Timeline label (above the black fade)
                      Positioned(
                        bottom: 16,
                        left: 0,
                        right: 0,
                        child: Center(
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 20, vertical: 10),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.95),
                              borderRadius: BorderRadius.circular(24),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.1),
                                  blurRadius: 16,
                                  spreadRadius: 1,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  width: 6,
                                  height: 6,
                                  decoration: const BoxDecoration(
                                    color: Color(0xFFD4AF37),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Text(
                                  'Living Timeline',
                                  style: GoogleFonts.mulish(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 15,
                                    color: const Color(0xFF1A1A1A),
                                    letterSpacing: 0.3,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Text(
                                  '${_stops.length} stops',
                                  style: GoogleFonts.mulish(
                                    fontWeight: FontWeight.w500,
                                    fontSize: 13,
                                    color: Colors.grey[600],
                                  ),
                                ),
                              ],
                            ),
                          ),
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
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(24, 32, 24, 140),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
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
        ],
      ),
    );
  }

  List<Widget> _buildTimeline() {
    final widgets = <Widget>[];
    final venues = _richItineraryData?['venues'] as List<dynamic>?;

    print('DEBUG: Building timeline with ${_stops.length} stops');
    print('DEBUG: Rich data available: ${_richItineraryData != null}');
    print(
        'DEBUG: Venues available: ${venues != null}, count: ${venues?.length ?? 0}');

    for (var i = 0; i < _stops.length; i++) {
      final stop = _stops[i];

      // Try to find matching rich venue data
      Map<String, dynamic>? matchingVenue;
      if (venues != null) {
        final stopPlaceId = stop['place_id']?.toString() ??
            stop['postgres_data']?['place_id']?.toString();
        print('DEBUG: Stop $i place_id: $stopPlaceId');
        if (stopPlaceId != null) {
          try {
            matchingVenue = venues.firstWhere(
              (v) => v['place_id']?.toString() == stopPlaceId,
              orElse: () => null,
            );
            print('DEBUG: Matching venue found: ${matchingVenue != null}');
          } catch (e) {
            print('DEBUG: Error finding venue: $e');
            matchingVenue = null;
          }
        }
      }

      // Use rich venue card if available, otherwise fallback to basic
      if (matchingVenue != null) {
        print('DEBUG: Adding RichVenueCard for stop $i');
        widgets.add(RichVenueCard(
          venue: matchingVenue,
          stopNumber: i + 1,
        ));
      } else {
        print('DEBUG: Adding basic timeline item for stop $i');
        // Fallback to basic timeline item
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
      }

      if (i != _stops.length - 1) {
        widgets.add(_buildWalkingGap(
          index: i,
          minutes: _walkMinutesBetween(i),
          distance: _walkDistanceBetween(i),
          showAddStop: i == 0 || i == _stops.length - 2,
        ));
      }
    }

    // Show loading indicator if still fetching
    if (_isLoadingRichData && widgets.isEmpty) {
      widgets.add(
        const Center(
          child: Padding(
            padding: EdgeInsets.all(40.0),
            child: CircularProgressIndicator(
              color: Color(0xFFD4AF37),
            ),
          ),
        ),
      );
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
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
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
    required int index,
    required int minutes,
    required String distance,
    bool showAddStop = true,
  }) {
    final isExpanded = _expandedGapIndex == index;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const SizedBox(width: 50),
            SizedBox(
              width: 12,
              child: Column(
                children: List.generate(
                  4,
                  (idx) => Container(
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
                    GestureDetector(
                      onTap: () {
                        setState(() {
                          _expandedGapIndex = isExpanded ? null : index;
                        });
                      },
                      child: Text(
                        'Add stop?',
                        style: TextStyle(
                          color: Colors.blue,
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        // Inline search panel when expanded
        if (isExpanded && showAddStop)
          Padding(
            padding: const EdgeInsets.only(left: 82, right: 24, bottom: 16),
            child: _buildInlineVenueSearchPanel(index),
          ),
      ],
    );
  }
  
  Widget _buildInlineVenueSearchPanel(int insertIndex) {
    // Get current location from the first stop or use default
    double? currentLat;
    double? currentLon;
    
    if (_stops.isNotEmpty && insertIndex < _stops.length) {
      final stop = _stops[insertIndex];
      currentLat = (stop['latitude'] as num?)?.toDouble() ?? 
                   (stop['postgres_data']?['latitude'] as num?)?.toDouble();
      currentLon = (stop['longitude'] as num?)?.toDouble() ?? 
                   (stop['postgres_data']?['longitude'] as num?)?.toDouble();
    }
    
    return InlineVenueSearchPanel(
      itineraryId: _currentItinerary['id']?.toString() ?? 
                   _currentItinerary['firestore_id']?.toString(),
      insertPosition: insertIndex + 1,
      currentLatitude: currentLat,
      currentLongitude: currentLon,
      onStopCreated: (stopData) {
        // Handle stop creation - add stop to itinerary
        setState(() {
          _expandedGapIndex = null;
          
          // Get the current itinerary data
          final itineraryData = _currentItinerary['itinerary_data'] as Map<String, dynamic>? ?? {};
          final stops = itineraryData['itinerary'] as List<dynamic>? ?? 
                       _currentItinerary['items'] as List<dynamic>? ?? [];
          
          // Create the new stop object
          final venue = stopData['venue'] as Map<String, dynamic>? ?? {};
          final newStop = {
            'place_id': venue['id'] ?? stopData['venue_id'],
            'place_name': venue['name'] ?? 'New Stop',
            'name': venue['name'] ?? 'New Stop',
            'latitude': venue['latitude'],
            'longitude': venue['longitude'],
            'address': venue['address'] ?? '',
            'rating': venue['rating'],
            'category': venue['categories']?.isNotEmpty == true 
                ? (venue['categories'] as List).first.toString()
                : 'Spot',
            'start_time': _calculateTimeForInsertPosition(insertIndex, stops),
            'postgres_data': {
              'place_id': venue['id'] ?? stopData['venue_id'],
              'name': venue['name'] ?? 'New Stop',
              'latitude': venue['latitude'],
              'longitude': venue['longitude'],
              'address': venue['address'] ?? '',
              'rating': venue['rating'],
              'category': venue['categories']?.isNotEmpty == true 
                  ? (venue['categories'] as List).first.toString()
                  : 'Spot',
            },
          };
          
          // Insert the stop at the correct position
          final updatedStops = List<Map<String, dynamic>>.from(
            stops.map((s) => Map<String, dynamic>.from(s as Map))
          );
          updatedStops.insert(insertIndex + 1, newStop);
          
          // Update the itinerary data
          final updatedItineraryData = Map<String, dynamic>.from(itineraryData);
          updatedItineraryData['itinerary'] = updatedStops;
          
          // Update the current itinerary
          _currentItinerary = Map<String, dynamic>.from(_currentItinerary);
          _currentItinerary['itinerary_data'] = updatedItineraryData;
          
          // Also update items if it exists
          if (_currentItinerary.containsKey('items')) {
            _currentItinerary['items'] = updatedStops;
          }
        });
        
        // Refresh rich data to show new stop
        _fetchRichData();
        
        // Show success message using the same style as saving itinerary
        BeautifulSnackbar.showSuccess(context, 'Stop added successfully! 💚');
      },
      onCancel: () {
        setState(() {
          _expandedGapIndex = null;
        });
      },
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
