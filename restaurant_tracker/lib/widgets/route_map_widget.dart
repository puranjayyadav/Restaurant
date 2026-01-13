import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;
import 'package:google_fonts/google_fonts.dart';

/// Interactive map widget showing itinerary stops with walking route.
/// Long press on the map to select a new starting point.
class RouteMapWidget extends StatefulWidget {
  final List<Map<String, dynamic>> stops;
  final Map<String, dynamic>? routeStats;
  final bool lightTheme;
  final double borderRadius;
  /// Callback when user long-presses on map to select new starting point
  final void Function(double lat, double lng)? onLongPressLocation;

  const RouteMapWidget({
    super.key,
    required this.stops,
    this.routeStats,
    this.lightTheme = false,
    this.borderRadius = 16,
    this.onLongPressLocation,
  });

  @override
  State<RouteMapWidget> createState() => _RouteMapWidgetState();
}

class _RouteMapWidgetState extends State<RouteMapWidget> {
  List<LatLng> _routePoints = [];
  bool _isLoading = true;
  final MapController _mapController = MapController();

  @override
  void initState() {
    super.initState();
    _fetchRoute();
  }

  @override
  void didUpdateWidget(RouteMapWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Check if stops have changed (new itinerary)
    if (_stopsChanged(oldWidget.stops, widget.stops)) {
      print('DEBUG: Stops changed, resetting map and fetching new route');
      // Reset state and fetch new route
      setState(() {
        _routePoints = [];
        _isLoading = true;
      });
      _fetchRoute();
      // Fit map to new bounds after a short delay
      Future.delayed(const Duration(milliseconds: 500), () {
        if (mounted) {
          final bounds = _getBounds();
          if (bounds != null) {
            _mapController.fitCamera(
              CameraFit.bounds(
                bounds: bounds,
                padding: const EdgeInsets.all(40),
              ),
            );
          }
        }
      });
    }
  }

  bool _stopsChanged(List<Map<String, dynamic>> oldStops, List<Map<String, dynamic>> newStops) {
    if (oldStops.length != newStops.length) return true;
    
    // Compare place IDs or coordinates
    for (int i = 0; i < oldStops.length; i++) {
      final oldPlaceId = oldStops[i]['place_id']?.toString() ?? 
                         oldStops[i]['postgres_data']?['place_id']?.toString();
      final newPlaceId = newStops[i]['place_id']?.toString() ?? 
                         newStops[i]['postgres_data']?['place_id']?.toString();
      
      if (oldPlaceId != newPlaceId) return true;
      
      // Also check coordinates as fallback
      final oldLat = _extractLat(oldStops[i]);
      final newLat = _extractLat(newStops[i]);
      final oldLng = _extractLng(oldStops[i]);
      final newLng = _extractLng(newStops[i]);
      
      if (oldLat != newLat || oldLng != newLng) return true;
    }
    
    return false;
  }

  double? _extractLat(Map<String, dynamic> stop) {
    final postgres = stop['postgres_data'] as Map<String, dynamic>?;
    return _toDouble(postgres?['lat']) ?? 
           _toDouble(postgres?['latitude']) ?? 
           _toDouble(stop['lat']) ?? 
           _toDouble(stop['latitude']);
  }

  double? _extractLng(Map<String, dynamic> stop) {
    final postgres = stop['postgres_data'] as Map<String, dynamic>?;
    return _toDouble(postgres?['lng']) ?? 
           _toDouble(postgres?['longitude']) ?? 
           _toDouble(stop['lng']) ?? 
           _toDouble(stop['longitude']);
  }

  List<LatLng> get _stopCoordinates {
    final coords = <LatLng>[];
    for (final stop in widget.stops) {
      final postgres = stop['postgres_data'] as Map<String, dynamic>?;
      double? lat, lng;

      // Try postgres_data first
      if (postgres != null) {
        lat = _toDouble(postgres['lat']) ?? _toDouble(postgres['latitude']);
        lng = _toDouble(postgres['lng']) ?? _toDouble(postgres['longitude']);
      }

      // Fallback to stop-level fields
      lat ??= _toDouble(stop['lat']) ?? _toDouble(stop['latitude']);
      lng ??= _toDouble(stop['lng']) ?? _toDouble(stop['longitude']);

      if (lat != null && lng != null) {
        coords.add(LatLng(lat, lng));
      }
    }
    return coords;
  }

  double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  Future<void> _fetchRoute() async {
    print('DEBUG: Fetching route for ${widget.stops.length} stops');
    
    final coords = _stopCoordinates;
    if (coords.length < 2) {
      if (mounted) {
        setState(() {
          _routePoints = coords; // Single point or empty
          _isLoading = false;
        });
      }
      return;
    }

    print('DEBUG: Coordinates: ${coords.map((c) => "(${c.latitude.toStringAsFixed(4)}, ${c.longitude.toStringAsFixed(4)})").join(" -> ")}');

    try {
      // Build OSRM request URL (free walking directions)
      final coordString =
          coords.map((c) => '${c.longitude},${c.latitude}').join(';');
      final url = Uri.parse(
          'https://router.project-osrm.org/route/v1/foot/$coordString?overview=full&geometries=polyline');

      print('DEBUG: Fetching route from OSRM...');
      final response = await http.get(url).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final routes = data['routes'] as List?;

        if (routes != null && routes.isNotEmpty) {
          final geometry = routes[0]['geometry'] as String?;
          if (geometry != null) {
            final decodedPoints = _decodePolyline(geometry);
            print('DEBUG: Route decoded successfully: ${decodedPoints.length} points');
            if (mounted) {
              setState(() {
                _routePoints = decodedPoints;
                _isLoading = false;
              });
            }
            return;
          }
        }
      }
      
      print('DEBUG: OSRM request failed, using fallback straight lines');
    } catch (e) {
      debugPrint('Route fetch error: $e');
    }
    
    // Fallback: draw straight lines between stops
    if (mounted) {
      setState(() {
        _routePoints = coords;
        _isLoading = false;
      });
    }
  }

  /// Decode Google-style polyline to list of LatLng
  List<LatLng> _decodePolyline(String encoded) {
    final points = <LatLng>[];
    int index = 0;
    int lat = 0;
    int lng = 0;

    while (index < encoded.length) {
      int shift = 0;
      int result = 0;
      int byte;

      do {
        byte = encoded.codeUnitAt(index++) - 63;
        result |= (byte & 0x1F) << shift;
        shift += 5;
      } while (byte >= 0x20);

      int dlat = (result & 1) != 0 ? ~(result >> 1) : (result >> 1);
      lat += dlat;

      shift = 0;
      result = 0;

      do {
        byte = encoded.codeUnitAt(index++) - 63;
        result |= (byte & 0x1F) << shift;
        shift += 5;
      } while (byte >= 0x20);

      int dlng = (result & 1) != 0 ? ~(result >> 1) : (result >> 1);
      lng += dlng;

      points.add(LatLng(lat / 1e5, lng / 1e5));
    }

    return points;
  }

  LatLngBounds? _getBounds() {
    final coords = _stopCoordinates;
    if (coords.isEmpty) return null;

    double minLat = coords.first.latitude;
    double maxLat = coords.first.latitude;
    double minLng = coords.first.longitude;
    double maxLng = coords.first.longitude;

    for (final c in coords) {
      if (c.latitude < minLat) minLat = c.latitude;
      if (c.latitude > maxLat) maxLat = c.latitude;
      if (c.longitude < minLng) minLng = c.longitude;
      if (c.longitude > maxLng) maxLng = c.longitude;
    }

    // Add padding
    const padding = 0.003;
    return LatLngBounds(
      LatLng(minLat - padding, minLng - padding),
      LatLng(maxLat + padding, maxLng + padding),
    );
  }

  @override
  Widget build(BuildContext context) {
    final coords = _stopCoordinates;
    final bounds = _getBounds();

    if (coords.isEmpty) {
      return Container(
        color: Colors.grey[200],
        child: const Center(child: Text('No location data')),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(widget.borderRadius),
      child: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: coords.first,
              initialZoom: 14,
              // Always fit to bounds on initial load
              initialCameraFit: bounds != null
                  ? CameraFit.bounds(
                      bounds: bounds, 
                      padding: const EdgeInsets.all(50),
                      maxZoom: 16,
                    )
                  : null,
              interactionOptions: const InteractionOptions(
                flags: InteractiveFlag.all,
              ),
              onLongPress: (tapPosition, point) {
                if (widget.onLongPressLocation != null) {
                  _showLocationConfirmDialog(context, point);
                }
              },
              onMapReady: () {
                // Ensure map fits bounds when ready
                print('DEBUG: Map ready, fitting to bounds');
                if (bounds != null) {
                  Future.delayed(const Duration(milliseconds: 100), () {
                    if (mounted) {
                      _mapController.fitCamera(
                        CameraFit.bounds(
                          bounds: bounds,
                          padding: const EdgeInsets.all(50),
                          maxZoom: 16,
                        ),
                      );
                    }
                  });
                }
              },
            ),
            children: [
              // Map tiles - light or dark theme
              TileLayer(
                urlTemplate: widget.lightTheme
                    ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
                    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.example.restaurant_tracker',
                additionalOptions: const {
                  'attribution': '© OpenStreetMap contributors © CARTO',
                },
              ),

              // Route polyline - golden streak
              if (_routePoints.isNotEmpty)
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: _routePoints,
                      color: const Color(0xFFD4AF37), // Golden color
                      strokeWidth: 5,
                      borderColor: Colors.white.withOpacity(0.8),
                      borderStrokeWidth: 2,
                    ),
                  ],
                ),

              // Stop markers - soft golden style
              MarkerLayer(
                markers: coords.asMap().entries.map((entry) {
                  final index = entry.key;
                  final coord = entry.value;
                  final stopName =
                      widget.stops[index]['place_name']?.toString() ??
                          widget.stops[index]['name']?.toString() ??
                          'Stop ${index + 1}';

                  return Marker(
                    point: coord,
                    width: 40,
                    height: 40,
                    child: GestureDetector(
                      onTap: () => _showStopInfo(context, index, stopName),
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFFD4AF37), // Golden
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3.5),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFFD4AF37).withOpacity(0.4),
                              blurRadius: 12,
                              spreadRadius: 2,
                              offset: const Offset(0, 2),
                            ),
                            BoxShadow(
                              color: Colors.black.withOpacity(0.15),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            '${index + 1}',
                            style: GoogleFonts.mulish(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                              fontSize: 15,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),

          // Loading overlay
          if (_isLoading)
            Container(
              color: Colors.white.withOpacity(0.8),
              child: const Center(
                child: CircularProgressIndicator(color: Color(0xFFD4AF37)),
              ),
            ),
        ],
      ),
    );
  }

  void _showStopInfo(BuildContext context, int index, String name) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Stop ${index + 1}: $name'),
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _showLocationConfirmDialog(BuildContext context, LatLng point) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFD4AF37).withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.location_on,
                color: Color(0xFFD4AF37),
                size: 24,
              ),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'New Starting Point',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Regenerate itinerary from this location?',
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.my_location, size: 16, color: Colors.grey[600]),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${point.latitude.toStringAsFixed(5)}, ${point.longitude.toStringAsFixed(5)}',
                      style: TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 12,
                        color: Colors.grey[800],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              'Cancel',
              style: TextStyle(color: Colors.grey[600]),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              widget.onLongPressLocation?.call(point.latitude, point.longitude);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFD4AF37),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: const Text('Regenerate'),
          ),
        ],
      ),
    );
  }
}
