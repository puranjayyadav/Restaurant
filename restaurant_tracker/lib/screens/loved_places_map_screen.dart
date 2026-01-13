import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../theme/plandit_design_system.dart';
import 'package:google_fonts/google_fonts.dart';

class LovedPlacesMapScreen extends StatefulWidget {
  final List<Map<String, dynamic>> places;

  const LovedPlacesMapScreen({
    super.key,
    required this.places,
  });

  @override
  State<LovedPlacesMapScreen> createState() => _LovedPlacesMapScreenState();
}

class _LovedPlacesMapScreenState extends State<LovedPlacesMapScreen> {
  final MapController _mapController = MapController();
  int? _selectedMarkerIndex; // Track which marker is selected for popup

  @override
  void initState() {
    super.initState();
    // Fit camera to show all places after map is ready
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 500), () {
        if (mounted) {
          _fitMapToPlaces();
        }
      });
    });
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }

  double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  double? _getLat(Map<String, dynamic> place) {
    return _toDouble(place['lat']) ?? _toDouble(place['latitude']);
  }

  double? _getLng(Map<String, dynamic> place) {
    return _toDouble(place['lng']) ??
        _toDouble(place['longitude']) ??
        _toDouble(place['long']);
  }

  void _fitMapToPlaces() {
    if (widget.places.isEmpty) {
      // Default to NYC if no places
      _mapController.move(const LatLng(40.7128, -74.0060), 12.0);
      return;
    }

    final validPlaces = widget.places.where((place) {
      final lat = _getLat(place);
      final lng = _getLng(place);
      // Check if coordinates are actually valid numbers and not 0
      return lat != null && lng != null && lat != 0 && lng != 0;
    }).toList();

    if (validPlaces.isEmpty) {
      // Default to NYC if no valid coordinates
      _mapController.move(const LatLng(40.7128, -74.0060), 12.0);
      return;
    }

    if (validPlaces.length == 1) {
      // Single place - just center on it with NYC as context
      final lat = _getLat(validPlaces[0])!;
      final lng = _getLng(validPlaces[0])!;
      _mapController.move(LatLng(lat, lng), 14.0);
    } else {
      // Multiple places - calculate bounds and fit camera
      double minLat = double.infinity;
      double maxLat = -double.infinity;
      double minLng = double.infinity;
      double maxLng = -double.infinity;

      for (var place in validPlaces) {
        final lat = _getLat(place)!;
        final lng = _getLng(place)!;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
        if (lng < minLng) minLng = lng;
        if (lng > maxLng) maxLng = lng;
      }

      // Validate that bounds are reasonable (within Earth's coordinates)
      if (minLat.isFinite &&
          maxLat.isFinite &&
          minLng.isFinite &&
          maxLng.isFinite &&
          minLat >= -90 &&
          maxLat <= 90 &&
          minLng >= -180 &&
          maxLng <= 180) {
        final bounds = LatLngBounds(
          LatLng(minLat, minLng),
          LatLng(maxLat, maxLng),
        );

        _mapController.fitCamera(
          CameraFit.bounds(
            bounds: bounds,
            padding: const EdgeInsets.all(80),
          ),
        );
      } else {
        // If bounds are invalid, stay on NYC
        _mapController.move(const LatLng(40.7128, -74.0060), 12.0);
      }
    }
  }

  List<Marker> _buildMarkers() {
    final markers = <Marker>[];
    for (int i = 0; i < widget.places.length; i++) {
      final place = widget.places[i];
      final lat = _getLat(place);
      final lng = _getLng(place);

      if (lat == null || lng == null) continue;

      final placeName = place['name'] ?? 'Unknown Place';
      final isSelected = _selectedMarkerIndex == i;

      markers.add(
        Marker(
          point: LatLng(lat, lng),
          width: 50,
          height: 50,
          child: GestureDetector(
            onTap: () {
              setState(() {
                _selectedMarkerIndex = _selectedMarkerIndex == i ? null : i;
              });
            },
            child: Stack(
              alignment: Alignment.center,
              clipBehavior: Clip.none,
              children: [
                // Heart marker for loved places
                Container(
                  width: 45,
                  height: 45,
                  decoration: BoxDecoration(
                    color: Colors.orange,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white,
                      width: isSelected ? 4 : 3,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.3),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.favorite,
                    color: Colors.white,
                    size: 26,
                  ),
                ),
                // Popup for place name
                if (isSelected)
                  Positioned(
                    bottom: 60,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Popup bubble
                        Container(
                          constraints: const BoxConstraints(maxWidth: 200),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: PlanditColors.border,
                              width: 1,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.2),
                                blurRadius: 8,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                placeName,
                                style: GoogleFonts.playfairDisplay(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: PlanditColors.primaryText,
                                ),
                                textAlign: TextAlign.center,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              if (place['rating'] != null) ...[
                                const SizedBox(height: 4),
                                Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.star,
                                        size: 12,
                                        color: PlanditColors.accentGold),
                                    const SizedBox(width: 4),
                                    Text(
                                      place['rating'].toString(),
                                      style: GoogleFonts.inter(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: PlanditColors.primaryText,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ],
                          ),
                        ),
                        // Arrow pointing down
                        Stack(
                          alignment: Alignment.center,
                          children: [
                            // Border arrow (slightly larger)
                            Container(
                              width: 0,
                              height: 0,
                              margin: const EdgeInsets.only(top: 1),
                              decoration: BoxDecoration(
                                border: Border(
                                  top: BorderSide(
                                    color: PlanditColors.border,
                                    width: 9,
                                  ),
                                  left: const BorderSide(
                                    color: Colors.transparent,
                                    width: 9,
                                  ),
                                  right: const BorderSide(
                                    color: Colors.transparent,
                                    width: 9,
                                  ),
                                ),
                              ),
                            ),
                            // Main arrow
                            Container(
                              width: 0,
                              height: 0,
                              decoration: const BoxDecoration(
                                border: Border(
                                  top: BorderSide(
                                    color: Colors.white,
                                    width: 8,
                                  ),
                                  left: BorderSide(
                                    color: Colors.transparent,
                                    width: 8,
                                  ),
                                  right: BorderSide(
                                    color: Colors.transparent,
                                    width: 8,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    }
    return markers;
  }

  @override
  Widget build(BuildContext context) {
    final validPlaces = widget.places.where((place) {
      final lat = _getLat(place);
      final lng = _getLng(place);
      return lat != null && lng != null;
    }).toList();

    if (validPlaces.isEmpty) {
      return Scaffold(
        backgroundColor: PlanditColors.background,
        appBar: AppBar(
          title: Text(
            'LOVED PLACES MAP',
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
          backgroundColor: Colors.white,
          elevation: 0,
          centerTitle: true,
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.map_outlined,
                size: 64,
                color: PlanditColors.secondaryText.withOpacity(0.3),
              ),
              const SizedBox(height: 16),
              Text(
                'No places to display',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  color: PlanditColors.secondaryText,
                ),
              ),
            ],
          ),
        ),
      );
    }

    final markers = _buildMarkers();

    // Always start centered on NYC
    const nycCenter = LatLng(40.7128, -74.0060);

    return Scaffold(
      backgroundColor: PlanditColors.background,
      appBar: AppBar(
        title: Text(
          'LOVED PLACES MAP (${validPlaces.length})',
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.5,
          ),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: PlanditColors.primaryText),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: GestureDetector(
        onTap: () {
          // Close popup when tapping on map
          if (_selectedMarkerIndex != null) {
            setState(() {
              _selectedMarkerIndex = null;
            });
          }
        },
        child: FlutterMap(
          mapController: _mapController,
          options: MapOptions(
            initialCenter: nycCenter,
            initialZoom: 12.0,
            minZoom: 5.0,
            maxZoom: 18.0,
            onTap: (tapPosition, point) {
              // Close popup when tapping on map
              if (_selectedMarkerIndex != null) {
                setState(() {
                  _selectedMarkerIndex = null;
                });
              }
            },
          ),
          children: [
            // OpenStreetMap tile layer
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.yourcompany.restaurant_tracker',
              maxZoom: 19,
            ),
            // Marker layer
            MarkerLayer(markers: markers),
          ],
        ),
      ),
    );
  }
}
