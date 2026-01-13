import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../theme/design_system.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class PlaceDetailScreen extends StatefulWidget {
  final Map<String, dynamic> place;

  const PlaceDetailScreen({
    Key? key,
    required this.place,
  }) : super(key: key);

  @override
  State<PlaceDetailScreen> createState() => _PlaceDetailScreenState();
}

class _PlaceDetailScreenState extends State<PlaceDetailScreen> {
  late Map<String, dynamic> _place;
  final MapController _mapController = MapController();
  bool _isHoursExpanded = false;

  @override
  void initState() {
    super.initState();
    _place = Map<String, dynamic>.from(widget.place);
    // Initialize map position after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeMap();
    });
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }

  void _initializeMap() {
    final lat = _place['lat'] as double? ??
        (_place['geometry']?['location']?['lat'] as double?);
    final lon = _place['long'] as double? ??
        (_place['geometry']?['location']?['lng'] as double?);

    if (lat != null && lon != null) {
      Future.delayed(const Duration(milliseconds: 300), () {
        if (mounted) {
          _mapController.move(LatLng(lat, lon), 15.0);
        }
      });
    }
  }

  String _formatPriceLevel(int? priceLevel) {
    if (priceLevel == null) return 'Price not available';
    return '\$' * priceLevel;
  }

  String _formatDayName(dynamic day) {
    if (day == null) return '';
    final dayStr = day.toString().toLowerCase();
    final dayMap = {
      '0': 'Monday',
      '1': 'Tuesday',
      '2': 'Wednesday',
      '3': 'Thursday',
      '4': 'Friday',
      '5': 'Saturday',
      '6': 'Sunday',
      'monday': 'Monday',
      'tuesday': 'Tuesday',
      'wednesday': 'Wednesday',
      'thursday': 'Thursday',
      'friday': 'Friday',
      'saturday': 'Saturday',
      'sunday': 'Sunday',
    };
    return dayMap[dayStr] ?? dayStr;
  }

  String _formatHoursEntry(Map<String, dynamic> entry) {
    final day = _formatDayName(entry['day']);
    final hours = entry['hours']?.toString() ?? '';
    final open24Hour = entry['open24Hour']?.toString();
    final close24Hour = entry['close24Hour']?.toString();

    if (hours.isNotEmpty) {
      return '$day: $hours';
    } else if (open24Hour != null && close24Hour != null) {
      // Format 24-hour time to 12-hour format
      try {
        final openHour = int.parse(open24Hour);
        final closeHour = int.parse(close24Hour);
        final openTime = _format24Hour(openHour);
        final closeTime = _format24Hour(closeHour);
        return '$day: $openTime - $closeTime';
      } catch (e) {
        return '$day: $open24Hour - $close24Hour';
      }
    } else {
      return '$day: Closed';
    }
  }

  String _format24Hour(int hour24) {
    if (hour24 == 0) return '12:00 AM';
    if (hour24 < 12) return '$hour24:00 AM';
    if (hour24 == 12) return '12:00 PM';
    return '${hour24 - 12}:00 PM';
  }

  List<Map<String, dynamic>> _parseHours(List? hours) {
    if (hours == null || hours.isEmpty) return [];

    final parsed = <Map<String, dynamic>>[];
    for (var hour in hours) {
      if (hour is Map<String, dynamic>) {
        parsed.add(hour);
      } else if (hour is List && hour.isNotEmpty) {
        // Try to parse as structured data
        try {
          final day = hour[0];
          final hoursValue = hour.length > 3 ? hour[3] : null;
          String? hoursStr;
          String? open24Hour;
          String? close24Hour;

          if (hoursValue is List && hoursValue.isNotEmpty) {
            final hoursData = hoursValue[0];
            if (hoursData is List && hoursData.isNotEmpty) {
              hoursStr = hoursData[0]?.toString();
              if (hoursData.length > 1 && hoursData[1] is List) {
                final timeData = hoursData[1] as List;
                if (timeData.isNotEmpty && timeData[0] is List) {
                  open24Hour = timeData[0][0]?.toString();
                }
                if (timeData.length > 1 && timeData[1] is List) {
                  close24Hour = timeData[1][0]?.toString();
                }
              }
            }
          }

          parsed.add({
            'day': day,
            'hours': hoursStr,
            'open24Hour': open24Hour,
            'close24Hour': close24Hour,
          });
        } catch (e) {
          // If parsing fails, try to use as string
          parsed.add({
            'day': hour[0]?.toString() ?? '',
            'hours': hour.toString(),
            'open24Hour': null,
            'close24Hour': null,
          });
        }
      } else {
        // Fallback: treat as string
        parsed.add({
          'day': '',
          'hours': hour.toString(),
          'open24Hour': null,
          'close24Hour': null,
        });
      }
    }
    return parsed;
  }

  Future<void> _openWebsite(BuildContext context, String? url) async {
    if (url == null || url.isEmpty) return;

    try {
      final uri = Uri.parse(url);
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not open website')),
          );
        }
      }
    } catch (e) {
      print('Error opening website: $e');
    }
  }

  Future<void> _makePhoneCall(BuildContext context, String? phone) async {
    if (phone == null || phone.isEmpty) return;

    try {
      final uri = Uri.parse('tel:$phone');
      if (!await launchUrl(uri)) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not make phone call')),
          );
        }
      }
    } catch (e) {
      print('Error making phone call: $e');
    }
  }

  Future<void> _openDirections(
      BuildContext context, double? lat, double? lon, String? name) async {
    if (lat == null || lon == null) return;

    try {
      final query = Uri.encodeComponent(name ?? '');
      final uri = Uri.parse(
          'https://www.google.com/maps/search/?api=1&query=$lat,$lon&query_place_id=$query');
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not open maps')),
          );
        }
      }
    } catch (e) {
      print('Error opening directions: $e');
    }
  }

  Future<void> _makeReservation(BuildContext context) async {
    final name = _place['name'] as String? ?? '';
    final website = _place['website'] as String?;
    final fullAddress = _place['full_address'] as String? ??
        _place['formatted_address'] as String? ??
        _place['vicinity'] as String? ??
        '';
    final city = _place['city'] as String? ?? '';

    // Check if website contains Resy or OpenTable
    if (website != null && website.isNotEmpty) {
      final websiteLower = website.toLowerCase();
      if (websiteLower.contains('resy.com')) {
        await _openWebsite(context, website);
        return;
      } else if (websiteLower.contains('opentable.com')) {
        await _openWebsite(context, website);
        return;
      }
    }

    // Try to search on Resy first
    try {
      final query = Uri.encodeComponent('$name $city');
      final resyUrl = 'https://resy.com/cities/$query';
      final resyUri = Uri.parse(resyUrl);

      // Try Resy first
      if (await launchUrl(resyUri, mode: LaunchMode.externalApplication)) {
        return;
      }
    } catch (e) {
      print('Error opening Resy: $e');
    }

    // Fallback to OpenTable
    try {
      final query = Uri.encodeComponent('$name $fullAddress');
      final openTableUrl = 'https://www.opentable.com/s/?query=$query';
      final openTableUri = Uri.parse(openTableUrl);

      if (await launchUrl(openTableUri, mode: LaunchMode.externalApplication)) {
        return;
      }
    } catch (e) {
      print('Error opening OpenTable: $e');
    }

    // If both fail, show message
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
              'Could not find reservation link. Please search for this restaurant on Resy or OpenTable.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final name = _place['name'] as String? ?? 'Unknown Place';
    final streetAddress = _place['street_address'] as String? ?? '';
    final city = _place['city'] as String? ?? '';
    final zip = _place['zip'] as String? ?? '';
    final state = _place['state'] as String? ?? '';
    final countryCode = _place['country_code'] as String? ?? '';
    final fullAddress = _place['full_address'] as String? ??
        _place['formatted_address'] as String? ??
        _place['vicinity'] as String? ??
        '';
    final website = _place['website'] as String?;
    final avgRating =
        _place['avg_rating'] as double? ?? _place['rating'] as double?;
    final totalReviews =
        _place['total_reviews'] as int? ?? _place['user_ratings_total'] as int?;
    final tags = _place['tags'] as List<dynamic>? ??
        _place['types'] as List<dynamic>? ??
        [];
    final phone = _place['phone'] as String? ??
        _place['formatted_phone_number'] as String?;
    final hours = _place['hours'] as List? ?? _place['opening_hours'] as List?;
    final priceLevel = _place['price_level'] as int?;
    final lat = _place['lat'] as double? ??
        (_place['geometry']?['location']?['lat'] as double?);
    final lon = _place['long'] as double? ??
        (_place['geometry']?['location']?['lng'] as double?);

    final screenHeight = MediaQuery.of(context).size.height;
    final mapHeight = screenHeight * 0.30; // Reduced from 45% to 30%

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          name,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: AppTypography.titleLarge,
            fontWeight: FontWeight.w600,
          ),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Column(
        children: [
          // Map at top with fade effect
          if (lat != null && lon != null)
            Builder(
              builder: (context) {
                final latitude = lat;
                final longitude = lon;
                return Stack(
                  children: [
                    // Map
                    Container(
                      height: mapHeight,
                      width: double.infinity,
                      child: FlutterMap(
                        mapController: _mapController,
                        options: MapOptions(
                          initialCenter: LatLng(latitude, longitude),
                          initialZoom: 15.0,
                          minZoom: 10.0,
                          maxZoom: 18.0,
                          interactionOptions: const InteractionOptions(
                            flags:
                                InteractiveFlag.all & ~InteractiveFlag.rotate,
                          ),
                        ),
                        children: [
                          TileLayer(
                            urlTemplate:
                                'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                            userAgentPackageName:
                                'com.example.restaurant_tracker',
                          ),
                          MarkerLayer(
                            markers: [
                              Marker(
                                point: LatLng(latitude, longitude),
                                width: 40,
                                height: 40,
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: AppColors.primary,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: Colors.white,
                                      width: 3,
                                    ),
                                  ),
                                  child: Icon(
                                    Icons.location_on,
                                    color: Colors.white,
                                    size: 24,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    // Gradient fade overlay (only on lower part)
                    Positioned(
                      bottom: 0,
                      left: 0,
                      right: 0,
                      child: Container(
                        height: mapHeight * 0.4, // Only cover bottom 40% of map
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              AppColors.background.withOpacity(
                                  0.0), // Fully transparent at top of fade area
                              AppColors.background
                                  .withOpacity(0.4), // Slightly visible
                              AppColors.background
                                  .withOpacity(0.7), // More visible
                              AppColors.background
                                  .withOpacity(0.95), // Almost opaque
                              AppColors.background, // Fully opaque at bottom
                            ],
                            stops: const [0.0, 0.3, 0.6, 0.85, 1.0],
                          ),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),

          // Scrollable content below map
          Expanded(
            child: SingleChildScrollView(
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Name and Rating
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                name,
                                style: TextStyle(
                                  fontSize: AppTypography.titleLarge,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              if (avgRating != null) ...[
                                SizedBox(height: AppSpacing.xs),
                                Row(
                                  children: [
                                    ...List.generate(5, (index) {
                                      return Icon(
                                        index < avgRating.round()
                                            ? Icons.star
                                            : Icons.star_border,
                                        color: Colors.amber,
                                        size: 20,
                                      );
                                    }),
                                    SizedBox(width: AppSpacing.xs),
                                    Text(
                                      avgRating.toStringAsFixed(1),
                                      style: TextStyle(
                                        fontSize: AppTypography.bodyMedium,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textPrimary,
                                      ),
                                    ),
                                    if (totalReviews != null) ...[
                                      SizedBox(width: AppSpacing.xs),
                                      Text(
                                        '($totalReviews reviews)',
                                        style: TextStyle(
                                          fontSize: AppTypography.bodySmall,
                                          color: AppColors.textSecondary,
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ],
                            ],
                          ),
                        ),
                        if (priceLevel != null)
                          Container(
                            padding: EdgeInsets.symmetric(
                              horizontal: AppSpacing.sm,
                              vertical: AppSpacing.xs,
                            ),
                            decoration: BoxDecoration(
                              color: AppColors.surface,
                              borderRadius:
                                  BorderRadius.circular(AppBorderRadius.small),
                            ),
                            child: Text(
                              _formatPriceLevel(priceLevel),
                              style: TextStyle(
                                fontSize: AppTypography.bodyMedium,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                      ],
                    ),

                    SizedBox(height: AppSpacing.lg),

                    // Reservation Button
                    SizedBox(
                      width: double.infinity,
                      child: ShadButton(
                        size: ShadButtonSize.lg,
                        backgroundColor: AppColors.primary,
                        onPressed: () => _makeReservation(context),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.restaurant_menu, color: Colors.white),
                            SizedBox(width: AppSpacing.sm),
                            Text(
                              'Make Reservation',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: AppTypography.titleSmall,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    SizedBox(height: AppSpacing.lg),

                    // Address Section
                    ShadCard(
                      backgroundColor: AppColors.surfaceElevated,
                      padding: EdgeInsets.all(AppSpacing.md),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.location_on,
                                  color: AppColors.primary, size: 20),
                              SizedBox(width: AppSpacing.sm),
                              Text(
                                'Address',
                                style: TextStyle(
                                  fontSize: AppTypography.titleSmall,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ],
                          ),
                          SizedBox(height: AppSpacing.sm),
                          if (fullAddress.isNotEmpty)
                            Text(
                              fullAddress,
                              style: TextStyle(
                                fontSize: AppTypography.bodyMedium,
                                color: AppColors.textPrimary,
                              ),
                            )
                          else ...[
                            if (streetAddress.isNotEmpty)
                              Text(
                                streetAddress,
                                style: TextStyle(
                                  fontSize: AppTypography.bodyMedium,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            if (city.isNotEmpty ||
                                state.isNotEmpty ||
                                zip.isNotEmpty) ...[
                              SizedBox(height: 4),
                              Text(
                                [
                                  if (city.isNotEmpty) city,
                                  if (state.isNotEmpty) state,
                                  if (zip.isNotEmpty) zip,
                                  if (countryCode.isNotEmpty) countryCode,
                                ].join(', '),
                                style: TextStyle(
                                  fontSize: AppTypography.bodyMedium,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ],
                          ],
                          if (lat != null && lon != null) ...[
                            SizedBox(height: AppSpacing.sm),
                            ShadButton.outline(
                              size: ShadButtonSize.sm,
                              onPressed: () =>
                                  _openDirections(context, lat, lon, name),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.directions, size: 16),
                                  SizedBox(width: AppSpacing.xs),
                                  Text('Get Directions'),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),

                    SizedBox(height: AppSpacing.md),

                    // Contact Information
                    if (phone != null || website != null)
                      ShadCard(
                        backgroundColor: AppColors.surfaceElevated,
                        padding: EdgeInsets.all(AppSpacing.md),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.contact_phone,
                                    color: AppColors.primary, size: 20),
                                SizedBox(width: AppSpacing.sm),
                                Text(
                                  'Contact',
                                  style: TextStyle(
                                    fontSize: AppTypography.titleSmall,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: AppSpacing.sm),
                            if (phone != null && phone.isNotEmpty) ...[
                              InkWell(
                                onTap: () => _makePhoneCall(context, phone),
                                child: Padding(
                                  padding: EdgeInsets.symmetric(
                                      vertical: AppSpacing.xs),
                                  child: Row(
                                    children: [
                                      Icon(Icons.phone,
                                          size: 18, color: AppColors.primary),
                                      SizedBox(width: AppSpacing.sm),
                                      Text(
                                        phone,
                                        style: TextStyle(
                                          fontSize: AppTypography.bodyMedium,
                                          color: AppColors.primary,
                                          decoration: TextDecoration.underline,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                            if (website != null && website.isNotEmpty) ...[
                              SizedBox(height: AppSpacing.xs),
                              InkWell(
                                onTap: () => _openWebsite(context, website),
                                child: Padding(
                                  padding: EdgeInsets.symmetric(
                                      vertical: AppSpacing.xs),
                                  child: Row(
                                    children: [
                                      Icon(Icons.language,
                                          size: 18, color: AppColors.primary),
                                      SizedBox(width: AppSpacing.sm),
                                      Expanded(
                                        child: Text(
                                          website,
                                          style: TextStyle(
                                            fontSize: AppTypography.bodyMedium,
                                            color: AppColors.primary,
                                            decoration:
                                                TextDecoration.underline,
                                          ),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),

                    if (phone != null || website != null)
                      SizedBox(height: AppSpacing.md),

                    // Postgres Enrichment Section
                    if (_place['is_enriched'] == true)
                      _buildEnrichmentSection(),

                    if (_place['is_enriched'] == true)
                      SizedBox(height: AppSpacing.md),

                    // Opening Hours (Dropdown)
                    if (hours != null && hours.isNotEmpty)
                      ShadCard(
                        backgroundColor: AppColors.surfaceElevated,
                        padding: EdgeInsets.zero,
                        child: ExpansionTile(
                          initiallyExpanded: _isHoursExpanded,
                          onExpansionChanged: (expanded) {
                            setState(() {
                              _isHoursExpanded = expanded;
                            });
                          },
                          leading: Icon(Icons.access_time,
                              color: AppColors.primary, size: 20),
                          title: Text(
                            'Opening Hours',
                            style: TextStyle(
                              fontSize: AppTypography.titleSmall,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          trailing: Icon(
                            _isHoursExpanded
                                ? Icons.expand_less
                                : Icons.expand_more,
                            color: AppColors.textSecondary,
                          ),
                          children: [
                            Padding(
                              padding: EdgeInsets.all(AppSpacing.md),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: _parseHours(hours)
                                    .map((entry) => Padding(
                                          padding: EdgeInsets.only(
                                              bottom: AppSpacing.sm),
                                          child: Text(
                                            _formatHoursEntry(entry),
                                            style: TextStyle(
                                              fontSize:
                                                  AppTypography.bodyMedium,
                                              color: AppColors.textPrimary,
                                            ),
                                          ),
                                        ))
                                    .toList(),
                              ),
                            ),
                          ],
                        ),
                      ),

                    if (hours != null && hours.isNotEmpty)
                      SizedBox(height: AppSpacing.md),

                    // Reviews Section
                    if (totalReviews != null && totalReviews > 0)
                      Builder(
                        builder: (context) {
                          final reviewCount = totalReviews;
                          return ShadCard(
                            backgroundColor: AppColors.surfaceElevated,
                            padding: EdgeInsets.all(AppSpacing.md),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(Icons.star,
                                        color: AppColors.primary, size: 20),
                                    SizedBox(width: AppSpacing.sm),
                                    Text(
                                      'Top Reviews',
                                      style: TextStyle(
                                        fontSize: AppTypography.titleSmall,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textPrimary,
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(height: AppSpacing.md),
                                // Display 1-2 reviews
                                ...List.generate(
                                  reviewCount > 0
                                      ? (reviewCount >= 2 ? 2 : 1)
                                      : 0,
                                  (index) {
                                    // For now, show placeholder reviews since we don't have review data
                                    // In the future, this can be replaced with actual review data
                                    return Container(
                                      margin: EdgeInsets.only(
                                          bottom: AppSpacing.md),
                                      padding: EdgeInsets.all(AppSpacing.sm),
                                      decoration: BoxDecoration(
                                        color: AppColors.surface,
                                        borderRadius: BorderRadius.circular(
                                            AppBorderRadius.small),
                                      ),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              // Reviewer name placeholder
                                              Container(
                                                width: 32,
                                                height: 32,
                                                decoration: BoxDecoration(
                                                  color: AppColors.primary
                                                      .withOpacity(0.2),
                                                  shape: BoxShape.circle,
                                                ),
                                                child: Icon(
                                                  Icons.person,
                                                  size: 18,
                                                  color: AppColors.primary,
                                                ),
                                              ),
                                              SizedBox(width: AppSpacing.sm),
                                              Expanded(
                                                child: Column(
                                                  crossAxisAlignment:
                                                      CrossAxisAlignment.start,
                                                  children: [
                                                    Text(
                                                      'Reviewer ${index + 1}',
                                                      style: TextStyle(
                                                        fontSize: AppTypography
                                                            .bodyMedium,
                                                        fontWeight:
                                                            FontWeight.w600,
                                                        color: AppColors
                                                            .textPrimary,
                                                      ),
                                                    ),
                                                    Row(
                                                      children: List.generate(
                                                        5,
                                                        (starIndex) => Icon(
                                                          starIndex <
                                                                  (avgRating ??
                                                                          0)
                                                                      .round()
                                                              ? Icons.star
                                                              : Icons
                                                                  .star_border,
                                                          color: Colors.amber,
                                                          size: 14,
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ],
                                          ),
                                          SizedBox(height: AppSpacing.xs),
                                          Text(
                                            'This is a sample review. Actual review data will be displayed here once available from the API.',
                                            style: TextStyle(
                                              fontSize: AppTypography.bodySmall,
                                              color: AppColors.textSecondary,
                                              height: 1.4,
                                            ),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
                                ),
                                if (reviewCount > 2)
                                  Padding(
                                    padding:
                                        EdgeInsets.only(top: AppSpacing.xs),
                                    child: Text(
                                      'View all $reviewCount reviews',
                                      style: TextStyle(
                                        fontSize: AppTypography.bodySmall,
                                        color: AppColors.primary,
                                        decoration: TextDecoration.underline,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          );
                        },
                      ),

                    if (totalReviews != null && totalReviews > 0)
                      SizedBox(height: AppSpacing.md),

                    // Categories/Tags
                    if (tags.isNotEmpty)
                      ShadCard(
                        backgroundColor: AppColors.surfaceElevated,
                        padding: EdgeInsets.all(AppSpacing.md),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.category,
                                    color: AppColors.primary, size: 20),
                                SizedBox(width: AppSpacing.sm),
                                Text(
                                  'Categories',
                                  style: TextStyle(
                                    fontSize: AppTypography.titleSmall,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: AppSpacing.sm),
                            Wrap(
                              spacing: AppSpacing.xs,
                              runSpacing: AppSpacing.xs,
                              children: tags
                                  .where((tag) =>
                                      tag != null && tag.toString().isNotEmpty)
                                  .take(10)
                                  .map((tag) {
                                final tagStr = tag.toString();
                                // Filter out generic tags
                                if ([
                                  'point_of_interest',
                                  'establishment',
                                  'food'
                                ].contains(tagStr.toLowerCase())) {
                                  return const SizedBox.shrink();
                                }
                                return Chip(
                                  label: Text(
                                    tagStr
                                        .split('_')
                                        .map((word) => word.isEmpty
                                            ? ''
                                            : '${word[0].toUpperCase()}${word.substring(1)}')
                                        .join(' '),
                                    style: TextStyle(fontSize: 12),
                                  ),
                                  backgroundColor: AppColors.surface,
                                  padding: EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      ),

                    SizedBox(height: AppSpacing.xl),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEnrichmentSection() {
    final postgresData = _place['postgres_data'] as Map<String, dynamic>? ?? {};
    final menuItems = postgresData['menu_items'] as List<dynamic>? ?? [];
    final reviews = postgresData['reviews'] as List<dynamic>? ?? [];
    final tags = postgresData['tags'] as List<dynamic>? ?? [];
    final about = postgresData['about'] as String? ?? '';

    return ShadCard(
      backgroundColor: AppColors.surfaceElevated,
      padding: EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome, color: AppColors.primary, size: 20),
              SizedBox(width: AppSpacing.sm),
              Text(
                'Enhanced Information',
                style: TextStyle(
                  fontSize: AppTypography.titleSmall,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              SizedBox(width: AppSpacing.xs),
              Container(
                padding: EdgeInsets.symmetric(
                  horizontal: AppSpacing.xs,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: AppColors.success.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(AppBorderRadius.small),
                ),
                child: Text(
                  'ENRICHED',
                  style: TextStyle(
                    fontSize: AppTypography.labelSmall,
                    fontWeight: FontWeight.w600,
                    color: AppColors.success,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.md),
          // About/Description
          if (about.isNotEmpty) ...[
            Text(
              about,
              style: TextStyle(
                fontSize: AppTypography.bodyMedium,
                color: AppColors.textPrimary,
                height: 1.5,
              ),
            ),
            SizedBox(height: AppSpacing.md),
          ],
          // Tags
          if (tags.isNotEmpty) ...[
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: tags.map((tag) {
                return Container(
                  padding: EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm,
                    vertical: AppSpacing.xs,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(AppBorderRadius.small),
                    border: Border.all(
                      color: AppColors.primary.withOpacity(0.3),
                    ),
                  ),
                  child: Text(
                    tag.toString(),
                    style: TextStyle(
                      fontSize: AppTypography.labelSmall,
                      color: AppColors.primary,
                    ),
                  ),
                );
              }).toList(),
            ),
            SizedBox(height: AppSpacing.md),
          ],
          // Menu Items
          if (menuItems.isNotEmpty) ...[
            Text(
              'Menu Items',
              style: TextStyle(
                fontSize: AppTypography.titleSmall,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: AppSpacing.sm),
            ...menuItems.take(5).map((item) {
              final itemName = item['name'] as String? ?? '';
              final itemPrice = item['price'] as String? ?? '';
              return Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.xs),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        itemName,
                        style: TextStyle(
                          fontSize: AppTypography.bodySmall,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                    if (itemPrice.isNotEmpty)
                      Text(
                        itemPrice,
                        style: TextStyle(
                          fontSize: AppTypography.bodySmall,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                  ],
                ),
              );
            }).toList(),
            if (menuItems.length > 5)
              Text(
                '... and ${menuItems.length - 5} more items',
                style: TextStyle(
                  fontSize: AppTypography.bodySmall,
                  color: AppColors.textSecondary,
                  fontStyle: FontStyle.italic,
                ),
              ),
            SizedBox(height: AppSpacing.md),
          ],
          // Reviews breakdown
          if (reviews.isNotEmpty) ...[
            Text(
              'Review Insights',
              style: TextStyle(
                fontSize: AppTypography.titleSmall,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: AppSpacing.sm),
            ...reviews.take(3).map((review) {
              final foodRating = review['food_rating'] as double?;
              final serviceRating = review['service_rating'] as double?;
              final ambienceRating = review['ambience_rating'] as double?;
              final comment = review['comment'] as String? ?? '';

              return Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.sm),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (foodRating != null ||
                        serviceRating != null ||
                        ambienceRating != null)
                      Row(
                        children: [
                          if (foodRating != null)
                            Expanded(
                              child: _buildRatingBar('Food', foodRating),
                            ),
                          if (serviceRating != null)
                            Expanded(
                              child: _buildRatingBar('Service', serviceRating),
                            ),
                          if (ambienceRating != null)
                            Expanded(
                              child:
                                  _buildRatingBar('Ambience', ambienceRating),
                            ),
                        ],
                      ),
                    if (comment.isNotEmpty) ...[
                      SizedBox(height: AppSpacing.xs),
                      Text(
                        comment,
                        style: TextStyle(
                          fontSize: AppTypography.bodySmall,
                          color: AppColors.textSecondary,
                          fontStyle: FontStyle.italic,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              );
            }).toList(),
          ],
        ],
      ),
    );
  }

  Widget _buildRatingBar(String label, double rating) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: AppTypography.labelSmall,
            color: AppColors.textSecondary,
          ),
        ),
        SizedBox(height: AppSpacing.xs),
        Row(
          children: [
            ...List.generate(5, (index) {
              return Icon(
                index < rating.round() ? Icons.star : Icons.star_border,
                size: 12,
                color: Colors.amber,
              );
            }),
            SizedBox(width: AppSpacing.xs),
            Text(
              rating.toStringAsFixed(1),
              style: TextStyle(
                fontSize: AppTypography.labelSmall,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
