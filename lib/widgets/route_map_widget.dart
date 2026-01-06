import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;
import 'package:google_fonts/google_fonts.dart';

/// Interactive map widget showing itinerary stops with walking route.
class RouteMapWidget extends StatefulWidget {
  final List<Map<String, dynamic>> stops;
  
  const RouteMapWidget({super.key, required this.stops});

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
    final coords = _stopCoordinates;
    if (coords.length < 2) {
      setState(() => _isLoading = false);
      return;
    }

    try {
      // Build OSRM request URL (free walking directions)
      final coordString = coords.map((c) => '${c.longitude},${c.latitude}').join(';');
      final url = Uri.parse(
        'https://router.project-osrm.org/route/v1/foot/$coordString?overview=full&geometries=polyline'
      );

      final response = await http.get(url).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final routes = data['routes'] as List?;
        
        if (routes != null && routes.isNotEmpty) {
          final geometry = routes[0]['geometry'] as String?;
          if (geometry != null) {
            _routePoints = _decodePolyline(geometry);
          }
        }
      }
    } catch (e) {
      debugPrint('Route fetch error: $e');
      // Fallback: draw straight lines between stops
      _routePoints = coords;
    }

    if (mounted) {
      setState(() => _isLoading = false);
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
      borderRadius: BorderRadius.circular(16),
      child: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: coords.first,
              initialZoom: 14,
              initialCameraFit: bounds != null 
                ? CameraFit.bounds(bounds: bounds, padding: const EdgeInsets.all(40))
                : null,
              interactionOptions: const InteractionOptions(
                flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag,
              ),
            ),
            children: [
              // Map tiles
              TileLayer(
                urlTemplate: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.plandit.app',
              ),
              
              // Route polyline
              if (_routePoints.isNotEmpty)
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: _routePoints,
                      color: const Color(0xFFE91E63),
                      strokeWidth: 4,
                      borderColor: Colors.white,
                      borderStrokeWidth: 2,
                    ),
                  ],
                ),
              
              // Stop markers
              MarkerLayer(
                markers: coords.asMap().entries.map((entry) {
                  final index = entry.key;
                  final coord = entry.value;
                  final stopName = widget.stops[index]['place_name']?.toString() ??
                      widget.stops[index]['name']?.toString() ??
                      'Stop ${index + 1}';
                  
                  return Marker(
                    point: coord,
                    width: 36,
                    height: 36,
                    child: GestureDetector(
                      onTap: () => _showStopInfo(context, index, stopName),
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFFE91E63),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.3),
                              blurRadius: 6,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            '${index + 1}',
                            style: GoogleFonts.inter(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
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
              color: Colors.white.withOpacity(0.7),
              child: const Center(
                child: CircularProgressIndicator(color: Color(0xFFE91E63)),
              ),
            ),
          
          // Route info chip
          if (!_isLoading && _routePoints.isNotEmpty)
            Positioned(
              bottom: 12,
              left: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.15),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.directions_walk, size: 16, color: Color(0xFFE91E63)),
                    const SizedBox(width: 6),
                    Text(
                      '${coords.length} stops',
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                        color: Colors.grey[800],
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

  void _showStopInfo(BuildContext context, int index, String name) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Stop ${index + 1}: $name'),
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
