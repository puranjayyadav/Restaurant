import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../theme/design_system.dart';

class ItineraryMapScreen extends StatefulWidget {
  final List<Map<String, dynamic>> places;

  const ItineraryMapScreen({
    super.key,
    required this.places,
  });

  @override
  State<ItineraryMapScreen> createState() => _ItineraryMapScreenState();
}

class _ItineraryMapScreenState extends State<ItineraryMapScreen> {
  final MapController _mapController = MapController();
  int? _selectedMarkerIndex; // Track which marker is selected for popup

  @override
  void initState() {
    super.initState();
    // Fit camera to show all places after map is ready
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 300), () {
        _fitMapToPlaces();
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
    var lat = _toDouble(place['latitude']) ?? _toDouble(place['lat']);
    if (lat == null && place['postgres_data'] is Map) {
      final pg = place['postgres_data'] as Map;
      lat = _toDouble(pg['lat']) ?? _toDouble(pg['latitude']);
    }
    return lat;
  }

  double? _getLon(Map<String, dynamic> place) {
    var lon = _toDouble(place['longitude']) ?? _toDouble(place['lng']) ?? _toDouble(place['long']);
    if (lon == null && place['postgres_data'] is Map) {
      final pg = place['postgres_data'] as Map;
      lon = _toDouble(pg['lng']) ?? _toDouble(pg['longitude']) ?? _toDouble(pg['long']);
    }
    return lon;
  }

  void _fitMapToPlaces() {
    if (widget.places.isEmpty) return;

    final validPlaces = widget.places.where((place) {
      final lat = _getLat(place);
      final lon = _getLon(place);
      return lat != null && lon != null;
    }).toList();

    if (validPlaces.isEmpty) return;

    if (validPlaces.length == 1) {
      // Single place - just center on it
      final lat = _getLat(validPlaces[0])!;
      final lon = _getLon(validPlaces[0])!;
      _mapController.move(LatLng(lat, lon), 15.0);
    } else {
      // Multiple places - calculate bounds and fit camera
      double minLat = double.infinity;
      double maxLat = -double.infinity;
      double minLon = double.infinity;
      double maxLon = -double.infinity;

      for (var place in validPlaces) {
        final lat = _getLat(place)!;
        final lon = _getLon(place)!;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
      }

      final bounds = LatLngBounds(
        LatLng(minLat, minLon),
        LatLng(maxLat, maxLon),
      );

      _mapController.fitCamera(
        CameraFit.bounds(
          bounds: bounds,
          padding: const EdgeInsets.all(80),
        ),
      );
    }
  }

  List<LatLng> _getPolylinePoints() {
    final points = <LatLng>[];
    for (var place in widget.places) {
      final lat = _getLat(place);
      final lon = _getLon(place);
      if (lat != null && lon != null) {
        points.add(LatLng(lat, lon));
      }
    }
    return points;
  }

  List<Marker> _buildMarkers() {
    final markers = <Marker>[];
    for (int i = 0; i < widget.places.length; i++) {
      final place = widget.places[i];
      final lat = _getLat(place);
      final lon = _getLon(place);

      if (lat == null || lon == null) continue;

      final isStart = i == 0;
      final isEnd = i == widget.places.length - 1;
      // Try multiple possible field names for place name
      final placeName = (place['place_name'] as String?) ??
          (place['name'] as String?) ??
          (place['description'] as String?) ??
          'Unknown Place';
      final isSelected = _selectedMarkerIndex == i;

      markers.add(
        Marker(
          point: LatLng(lat, lon),
          width: isStart || isEnd ? 60 : 40,
          height: isStart || isEnd ? 60 : 40,
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
                // Background circle
                Container(
                  width: isStart || isEnd ? 50 : 40,
                  height: isStart || isEnd ? 50 : 40,
                  decoration: BoxDecoration(
                    color: isStart
                        ? AppColors.success
                        : isEnd
                            ? AppColors.error
                            : AppColors.primary,
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
                  child: Icon(
                    isStart
                        ? Icons.play_arrow
                        : isEnd
                            ? Icons.flag
                            : Icons.location_on,
                    color: Colors.white,
                    size: isStart || isEnd ? 28 : 24,
                  ),
                ),
                // Label for start/end
                if (isStart || isEnd)
                  Positioned(
                    bottom: -5,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: isStart ? AppColors.success : AppColors.error,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: Colors.white, width: 1),
                      ),
                      child: Text(
                        isStart ? 'START' : 'END',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                // Popup for place name
                if (isSelected)
                  Positioned(
                    bottom: (isStart || isEnd ? 50 : 40) + 10,
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
                            color: AppColors.surfaceElevated,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: AppColors.border,
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
                          child: Text(
                            placeName,
                            style: TextStyle(
                              fontSize: AppTypography.bodyMedium,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                            textAlign: TextAlign.center,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
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
                                    color: AppColors.border,
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
                              decoration: BoxDecoration(
                                border: Border(
                                  top: BorderSide(
                                    color: AppColors.surfaceElevated,
                                    width: 8,
                                  ),
                                  left: const BorderSide(
                                    color: Colors.transparent,
                                    width: 8,
                                  ),
                                  right: const BorderSide(
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
      final lon = _getLon(place);
      return lat != null && lon != null;
    }).toList();

    if (validPlaces.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Itinerary Map'),
          backgroundColor: Colors.transparent,
          elevation: 0,
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.map_outlined,
                size: 64,
                color: AppColors.textSecondary,
              ),
              const SizedBox(height: 16),
              Text(
                'No places to display',
                style: TextStyle(
                  fontSize: AppTypography.titleMedium,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      );
    }

    final polylinePoints = _getPolylinePoints();
    final markers = _buildMarkers();

    // Default center (first place or middle of bounds)
    LatLng defaultCenter;
    if (validPlaces.isNotEmpty) {
      final firstPlace = validPlaces[0];
      defaultCenter = LatLng(
        _getLat(firstPlace)!,
        _getLon(firstPlace)!,
      );
    } else {
      defaultCenter = const LatLng(40.7128, -74.0060); // Default to NYC
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Itinerary Map (${validPlaces.length} places)',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: AppTypography.titleMedium,
            fontWeight: FontWeight.w600,
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back, color: AppColors.textPrimary),
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
            initialCenter: defaultCenter,
            initialZoom: 13.0,
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
            // Polyline layer (path connecting places)
            if (polylinePoints.length > 1)
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: polylinePoints,
                    strokeWidth: 4.0,
                    color: AppColors.primary,
                  ),
                ],
              ),
            // Marker layer
            MarkerLayer(markers: markers),
          ],
        ),
      ),
    );
  }
}
