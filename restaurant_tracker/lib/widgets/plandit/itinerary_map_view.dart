import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../theme/plandit_design_system.dart';
import 'storyboard_models.dart';

class ItineraryMapView extends StatefulWidget {
  final List<Chapter> chapters;
  final String title;
  final int? activeChapter;
  final bool isHeader;
  final Function(LatLng)? onLocationSelected;

  const ItineraryMapView({
    super.key,
    required this.chapters,
    this.title = 'Your Journey',
    this.activeChapter,
    this.isHeader = false,
    this.onLocationSelected,
  });

  @override
  State<ItineraryMapView> createState() => _ItineraryMapViewState();
}

class _ItineraryMapViewState extends State<ItineraryMapView>
    with SingleTickerProviderStateMixin {
  late MapController mapController;
  List<LatLng> _routePoints = [];
  bool _isLoadingRoute = true;
  LatLng? _selectedPoint;

  @override
  void initState() {
    super.initState();
    mapController = MapController();
    
    // Load street routes
    _loadStreetRoutes();
    
    // Fit bounds after a brief delay to ensure map is ready
    Future.delayed(const Duration(milliseconds: 100), () {
      if (mounted) {
        _fitMapToBounds();
      }
    });
  }

  @override
  void didUpdateWidget(covariant ItineraryMapView oldWidget) {
    super.didUpdateWidget(oldWidget);
    // If chapters changed, reset map state and recalculate routes
    if (widget.chapters != oldWidget.chapters) {
      setState(() {
        _routePoints = [];
        _isLoadingRoute = true;
        _selectedPoint = null;
      });
      _loadStreetRoutes();
      Future.delayed(const Duration(milliseconds: 200), () {
        if (mounted) {
          _fitMapToBounds();
        }
      });
    }
  }

  void _fitMapToBounds() {
    if (!mounted) return;
    
    try {
      final venuePoints = _getVenuePoints();
      if (venuePoints.isEmpty) return;

      final bounds = _getBounds(venuePoints);
      
      // Fit the map to show all markers
      mapController.fitCamera(
        CameraFit.bounds(
          bounds: bounds,
          padding: widget.isHeader 
              ? const EdgeInsets.only(top: 120, bottom: 50, left: 50, right: 50) 
              : const EdgeInsets.all(50),
        ),
      );
    } catch (e) {
      print('Error fitting map to bounds: $e');
    }
  }

  Future<void> _loadStreetRoutes() async {
    final venuePoints = _getVenuePoints();
    if (venuePoints.length < 2) {
      if (mounted) {
        setState(() {
          _routePoints = venuePoints;
          _isLoadingRoute = false;
        });
      }
      return;
    }

    try {
      // Build coordinates string for OSRM (longitude,latitude;longitude,latitude)
      final coords = venuePoints
          .map((p) => '${p.longitude},${p.latitude}')
          .join(';');
      
      // Use OSRM for street routing (open public demo server)
      final url = 'https://router.project-osrm.org/route/v1/driving/$coords?overview=full&geometries=geojson';
      
      final response = await http.get(Uri.parse(url));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final coordinates = data['routes'][0]['geometry']['coordinates'] as List;
        
        if (mounted) {
          setState(() {
            _routePoints = coordinates
                .map((coord) => LatLng(coord[1] as double, coord[0] as double))
                .toList();
            _isLoadingRoute = false;
          });
        }
      } else {
        // Fallback to direct lines
        if (mounted) {
          setState(() {
            _routePoints = venuePoints;
            _isLoadingRoute = false;
          });
        }
      }
    } catch (e) {
      print('Error loading street routes: $e');
      // Fallback to direct lines
      if (mounted) {
        setState(() {
          _routePoints = venuePoints;
          _isLoadingRoute = false;
        });
      }
    }
  }

  @override
  void dispose() {
    super.dispose();
  }

  List<LatLng> _getVenuePoints() {
    final points = <LatLng>[];
    
    for (var chapter in widget.chapters) {
      // Get coordinates from the first variant (they're all the same for API data)
      final venue = chapter.variants['balanced'];
      if (venue != null && venue.lat != null && venue.lng != null) {
        points.add(LatLng(venue.lat!, venue.lng!));
      }
    }
    
    print('DEBUG: ItineraryMapView found ${points.length} venue points');
    return points;
  }

  LatLngBounds _getBounds(List<LatLng> points) {
    if (points.isEmpty) {
      return LatLngBounds(
        LatLng(40.7589, -73.9851),
        LatLng(40.7689, -73.9751),
      );
    }
    
    double minLat = points.first.latitude;
    double maxLat = points.first.latitude;
    double minLng = points.first.longitude;
    double maxLng = points.first.longitude;
    
    for (var point in points) {
      if (point.latitude < minLat) minLat = point.latitude;
      if (point.latitude > maxLat) maxLat = point.latitude;
      if (point.longitude < minLng) minLng = point.longitude;
      if (point.longitude > maxLng) maxLng = point.longitude;
    }
    
    // Add padding
    const padding = 0.005;
    return LatLngBounds(
      LatLng(minLat - padding, minLng - padding),
      LatLng(maxLat + padding, maxLng + padding),
    );
  }

  @override
  Widget build(BuildContext context) {
    final venuePoints = _getVenuePoints();

    if (widget.isHeader) {
      // Minimalist map view for Storyboard header
      return Stack(
        children: [
          FlutterMap(
            mapController: mapController,
            options: MapOptions(
              initialCenter: venuePoints.isNotEmpty 
                  ? venuePoints.first 
                  : LatLng(40.7589, -73.9851),
              initialZoom: 13.5,
              minZoom: 11.0,
              maxZoom: 16.0,
              interactionOptions: const InteractionOptions(
                flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
              ),
              onLongPress: (tapPosition, point) {
                if (widget.onLocationSelected != null && mounted) {
                  setState(() => _selectedPoint = point);
                }
              },
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.example.restaurant_tracker',
                retinaMode: RetinaMode.isHighDensity(context),
              ),
              if (!_isLoadingRoute && _routePoints.length > 1)
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: _routePoints,
                      strokeWidth: 3.0,
                      color: PlanditColors.accent.withOpacity(0.5),
                    ),
                  ],
                ),
              MarkerLayer(
                markers: [
                  for (int i = 0; i < venuePoints.length; i++)
                    Marker(
                      point: venuePoints[i],
                      width: 30,
                      height: 30,
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          border: Border.all(color: PlanditColors.accent, width: 2),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.1),
                              blurRadius: 4,
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            '${i + 1}',
                            style: TextStyle(
                              color: PlanditColors.accent,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                    ),
                  if (_selectedPoint != null)
                    Marker(
                      point: _selectedPoint!,
                      width: 40,
                      height: 40,
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.2),
                              blurRadius: 8,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.location_on,
                          color: Colors.blue,
                          size: 30,
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
          if (_selectedPoint != null)
            Positioned(
              bottom: 80,
              left: 0,
              right: 0,
              child: Center(
                child: ElevatedButton.icon(
                  onPressed: () {
                    if (mounted) {
                      widget.onLocationSelected?.call(_selectedPoint!);
                      setState(() => _selectedPoint = null);
                    }
                  },
                  icon: const Icon(Icons.refresh, size: 18),
                  label: const Text("GENERATE HERE"),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: PlanditColors.accent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                ),
              ),
            ),
        ],
      );
    }

    return Column(
      children: [
        // Title section - separate from map with no background
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
          child: Row(
            children: [
              Container(
                width: 4,
                height: 24,
                decoration: BoxDecoration(
                  color: const Color(0xFFF5DEB3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Your Journey',
                    style: GoogleFonts.inter(
                      fontSize: 32,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${widget.chapters.length} carefully curated stops',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      color: Colors.white.withOpacity(0.6),
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        // Map - padding and smaller markers
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Container(
            height: MediaQuery.of(context).size.height * 0.45, // Slightly taller map
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: Colors.white.withOpacity(0.1),
                width: 1,
              ),
            ),
            child: Stack(
              children: [
                FlutterMap(
                  mapController: mapController,
                  options: MapOptions(
                    initialCenter: venuePoints.isNotEmpty 
                        ? venuePoints.first 
                        : LatLng(40.7589, -73.9851),
                    initialZoom: 13.5,
                    minZoom: 11.0,
                    maxZoom: 16.0,
                    interactionOptions: const InteractionOptions(
                      flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
                    ),
                  ),
                  children: [
                    // Light map tiles (CartoDB Positron)
                    TileLayer(
                      urlTemplate: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                      subdomains: const ['a', 'b', 'c', 'd'],
                      userAgentPackageName: 'com.example.restaurant_tracker',
                      retinaMode: RetinaMode.isHighDensity(context),
                    ),
                    
                    // Street route polyline
                    if (!_isLoadingRoute && _routePoints.length > 1)
                      PolylineLayer(
                        polylines: [
                          Polyline(
                            points: _routePoints,
                            strokeWidth: 3.0,
                            color: const Color(0xFFF5DEB3),
                            borderStrokeWidth: 1.0,
                            borderColor: const Color(0xFF8B7355),
                          ),
                        ],
                      ),
                    
                    // Markers for each venue
                    MarkerLayer(
                      markers: [
                        for (int i = 0; i < venuePoints.length; i++)
                          Marker(
                            point: venuePoints[i],
                            width: 50,
                            height: 50,
                            child: GestureDetector(
                              onTap: () {
                                _showVenueDetails(context, i);
                              },
                              child: Column(
                                children: [
                                  Container(
                                    width: 32,
                                    height: 32,
                                    decoration: BoxDecoration(
                                      color: i == 0
                                          ? const Color(0xFF4CAF50)
                                          : i == venuePoints.length - 1
                                              ? const Color(0xFFE53935)
                                              : const Color(0xFFF5DEB3),
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: Colors.white,
                                        width: 2.5,
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withOpacity(0.4),
                                          blurRadius: 8,
                                          offset: const Offset(0, 3),
                                        ),
                                      ],
                                    ),
                                    child: Center(
                                      child: Text(
                                        '${i + 1}',
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 14,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
                
                // Legend at bottom
                Positioned(
                  bottom: 24,
                  left: 24,
                  right: 24,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1A1A1A).withOpacity(0.95),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: const Color(0xFFF5DEB3).withOpacity(0.3),
                        width: 1,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.5),
                          blurRadius: 20,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildLegendItem(Icons.play_circle_filled, 'Start', const Color(0xFF4CAF50)),
                        _buildLegendItem(Icons.location_on, 'Stops', const Color(0xFFF5DEB3)),
                        _buildLegendItem(Icons.flag, 'End', const Color(0xFFE53935)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLegendItem(IconData icon, String label, Color color) {
    return Row(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.9),
            fontSize: 13,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.3,
          ),
        ),
      ],
    );
  }

  void _showVenueDetails(BuildContext context, int index) {
    if (index >= widget.chapters.length) return;
    
    final chapter = widget.chapters[index];
    final venue = chapter.variants['balanced'];
    
    if (venue == null) return;
    
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: PlanditColors.card,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5DEB3).withOpacity(0.2),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '${index + 1}',
                      style: const TextStyle(
                        color: Color(0xFFF5DEB3),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        venue.venue,
                        style: GoogleFonts.playfairDisplay(
                          fontSize: 20,
                          fontWeight: FontWeight.w600,
                          color: PlanditColors.foreground,
                        ),
                      ),
                      Text(
                        venue.venueType,
                        style: TextStyle(
                          fontSize: 12,
                          color: PlanditColors.mutedForeground,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              venue.description,
              style: TextStyle(
                fontSize: 14,
                color: PlanditColors.mutedForeground,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Icon(Icons.star, color: Colors.amber, size: 16),
                const SizedBox(width: 4),
                Text(
                  venue.rating.toString(),
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: 16),
                Text(
                  venue.price,
                  style: TextStyle(
                    fontSize: 14,
                    color: PlanditColors.mutedForeground,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
