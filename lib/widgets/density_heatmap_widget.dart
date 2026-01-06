import 'dart:ui' as ui;
import 'dart:math' as math;
import 'dart:async'; // For Timer and debouncing
import 'package:flutter/material.dart';
import 'package:flutter/services.dart'; // For Haptics
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:google_fonts/google_fonts.dart';
import 'place_detail_sheet.dart';
import '../services/density_heatmap_service.dart';
import '../screens/itinerary_detail_screen.dart';
import '../api_service.dart';

class DensityHeatmapWidget extends StatefulWidget {
  final LatLng center;
  final String baseUrl;
  final String? selectedVibe; 
  final Function(String cellId, int placeCount)? onCellTap;

  const DensityHeatmapWidget({
    Key? key,
    required this.center,
    required this.baseUrl,
    this.selectedVibe,
    this.onCellTap,
  }) : super(key: key);

  @override
  State<DensityHeatmapWidget> createState() => _DensityHeatmapWidgetState();
}

class _DensityHeatmapWidgetState extends State<DensityHeatmapWidget> 
    with TickerProviderStateMixin { 
  
  late DensityHeatmapService _service;
  List<HeatmapPolygon> _dataPoints = []; 
  bool _isLoading = false;
  late AnimationController _pulseController; 
  late AnimationController _fadeController; // New: For smooth appearance
  late MapController _mapController; // Added controller
  Timer? _debounce; // Debouncer to prevent API spamming
  late LatLng _activeCenter; // Tracks the current center as user pans

  @override
  void initState() {
    super.initState();
    _service = DensityHeatmapService(baseUrl: widget.baseUrl);
    
    // Setup Breathing Animation (2 seconds in, 2 seconds out)
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    // Fade-in Animation for new clusters
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _mapController = MapController(); // Initialize controller
    _activeCenter = widget.center; // Initialize with starting point

    _loadHeatmap();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _pulseController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(DensityHeatmapWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedVibe != widget.selectedVibe) {
      // User clicked a filter button: Move camera to the best spot
      _loadHeatmap(shouldMoveCamera: true);
    } else if (oldWidget.center != widget.center) {
      // External center change (unlikely to be manual pan): Silent refresh
      _loadHeatmap(shouldMoveCamera: false);
    }
  }

  Future<void> _loadHeatmap({bool shouldMoveCamera = false}) async {
    if (!mounted) return;
    setState(() => _isLoading = true);

    try {
      final geojson = await _service.fetchHeatmap(
        lat: _activeCenter.latitude,
        lng: _activeCenter.longitude,
        vibe: widget.selectedVibe,
        gridSize: 0.008,
        gridCount: 12,
      );

      if (mounted) {
        final newPoints = DensityHeatmapService.geojsonToPolygons(geojson);
        setState(() {
          _dataPoints = newPoints;
          _isLoading = false;
        });
        
        // Trigger bloom/fade animation
        _fadeController.reset();
        _fadeController.forward();

        // --- THE FIX: ONLY MOVE IF EXPLICITLY REQUESTED ---
        if (shouldMoveCamera && newPoints.isNotEmpty) {
          // Sort to find the highest density cluster
          final sortedPoints = List<HeatmapPolygon>.from(newPoints);
          sortedPoints.sort((a, b) => b.densityScore.compareTo(a.densityScore));
          
          final bestSpot = sortedPoints.first;
          if (bestSpot.points.isNotEmpty) {
            // Calculate center
            double sumLat = 0;
            double sumLng = 0;
            for (var p in bestSpot.points) {
              sumLat += p.latitude;
              sumLng += p.longitude;
            }
            final hotCenter = LatLng(sumLat / bestSpot.points.length, sumLng / bestSpot.points.length);
            
            // Trigger cinematic flight
            _animatedMapMove(hotCenter, 14.5);
          }
        }
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  /// Helper for smooth map transitions
  void _animatedMapMove(LatLng destLocation, double destZoom) {
    if (!mounted) return;

    final latTween = Tween<double>(
      begin: _mapController.camera.center.latitude, 
      end: destLocation.latitude
    );
    final lngTween = Tween<double>(
      begin: _mapController.camera.center.longitude, 
      end: destLocation.longitude
    );
    final zoomTween = Tween<double>(
      begin: _mapController.camera.zoom, 
      end: destZoom
    );

    final controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this
    );

    final animation = CurvedAnimation(parent: controller, curve: Curves.fastOutSlowIn);

    controller.addListener(() {
      _mapController.move(
        LatLng(latTween.evaluate(animation), lngTween.evaluate(animation)),
        zoomTween.evaluate(animation)
      );
    });

    animation.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        controller.dispose();
      }
    });

    controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // 1. THE DARK AURA MAP
        FlutterMap(
          mapController: _mapController, // Use controller
          options: MapOptions(
            initialCenter: widget.center,
            initialZoom: 13.5,
            onPositionChanged: (position, hasGesture) {
              if (hasGesture && position.center != null) {
                _onMapMoved(position.center!);
              }
            },
            onTap: (tapPosition, latLng) => _handleSmartTap(latLng), // SMART TAP LOGIC
            interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
            ),
          ),
          children: [
            // Dark Base Layer
            TileLayer(
              urlTemplate: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
              subdomains: const ['a', 'b', 'c'],
              userAgentPackageName: 'com.plandit.app',
              retinaMode: MediaQuery.of(context).devicePixelRatio > 1.0,
            ),

            // LIQUID AURA LAYER (Living Beacons)
            CustomLayer(
              builder: (context, camera) {
                return AnimatedBuilder(
                  animation: Listenable.merge([_pulseController, _fadeController]),
                  builder: (context, child) {
                    return SizedBox.expand(
                      child: CustomPaint(
                        painter: EmojiHeatmapPainter(
                          dataPoints: _dataPoints,
                          camera: camera,
                          vibe: widget.selectedVibe,
                          pulseValue: _pulseController.value,
                          appearanceValue: _fadeController.value, // Pass fade value
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ],
        ),
        
        // Loading Indicator (Subtle)
        if (_isLoading)
          const Positioned(
            top: 140,
            right: 20,
            child: SizedBox(
              width: 16, height: 16,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white30),
            ),
          ),
      ],
    );
  }

  // --- THE DEBOUNCER ---
  void _onMapMoved(LatLng newCenter) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();

    _debounce = Timer(const Duration(milliseconds: 600), () {
      if (mounted) {
        setState(() {
          _activeCenter = newCenter;
        });
        // FALSE: Do not move the camera. User is in control.
        _loadHeatmap(shouldMoveCamera: false);
        debugPrint("Silent refresh for: $newCenter");
      }
    });
  }

  // --- "MAGNET TAP" LOGIC ---
  void _handleSmartTap(LatLng tappedPoint) {
    if (_dataPoints.isEmpty) return;

    HeatmapPolygon? nearest;
    double minDistance = double.infinity;

    const Distance distance = Distance();

    for (final point in _dataPoints) {
      if (point.points.isNotEmpty) {
        // Calculate center of the area
        double sumLat = 0;
        double sumLng = 0;
        for (var p in point.points) {
          sumLat += p.latitude;
          sumLng += p.longitude;
        }
        final center = LatLng(sumLat / point.points.length, sumLng / point.points.length);
        
        final d = distance.as(LengthUnit.Meter, tappedPoint, center);
        
        // Hit box: 1km for easier tapping
        if (d < 1000 && d < minDistance) {
          minDistance = d;
          nearest = point;
        }
      }
    }

    if (nearest != null) {
      // 1. Haptic Feedback
      HapticFeedback.lightImpact(); 

      // 2. Reveal the "Vibe Check" Pulse Card (Real Backend Generation)
      _showPulseCard(nearest);

      if (widget.onCellTap != null) {
        widget.onCellTap!(nearest.cellId, nearest.placeCount);
      }
    }
  }

  // --- PULSE CARD (THE VIBE CHECK) ---
  void _showPulseCard(HeatmapPolygon hotspot) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.5),
      isScrollControlled: true, // Allow it to expand
      builder: (context) => PulseCardContent(
        hotspot: hotspot,
        vibeName: widget.selectedVibe ?? 'Explore',
        service: _service,
      ),
    );
  }
}

class PulseCardContent extends StatefulWidget {
  final HeatmapPolygon hotspot;
  final String vibeName;
  final DensityHeatmapService service;

  const PulseCardContent({
    super.key,
    required this.hotspot,
    required this.vibeName,
    required this.service,
  });

  @override
  State<PulseCardContent> createState() => _PulseCardContentState();
}

class _PulseCardContentState extends State<PulseCardContent> {
  late Future<Map<String, dynamic>> _itineraryFuture;

  @override
  void initState() {
    super.initState();
    // THE FIX: Initialize the future ONCE in initState.
    // This prevents the Pulse Card from regenerating on every swipe/rebuild.
    final center = widget.hotspot.points[0];
    _itineraryFuture = widget.service.fetchHotspotItinerary(
      lat: center.latitude,
      lng: center.longitude,
      vibe: widget.vibeName,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _itineraryFuture,
      builder: (context, snapshot) {
        final isLoading = snapshot.connectionState == ConnectionState.waiting;
        final itinerary = snapshot.data;
        final error = snapshot.error;

        return Container(
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: const Color(0xFF121212),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.6),
                blurRadius: 40,
                offset: const Offset(0, -10),
              )
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (isLoading)
                SizedBox(
                  height: 350,
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const CircularProgressIndicator(color: Color(0xFFE91E63)),
                        const SizedBox(height: 20),
                        Text(
                          "Generating Vibe Check...",
                          style: GoogleFonts.inter(color: Colors.white70),
                        ),
                      ],
                    ),
                  ),
                )
              else if (error != null)
                SizedBox(
                  height: 250,
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Text(
                        "Failed to generate itinerary: $error",
                        style: const TextStyle(color: Colors.white60),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
                )
              else ...[
                // 1. HERO SECTION
                Stack(
                  children: [
                    SizedBox(
                      height: 240,
                      width: double.infinity,
                      child: Image.network(
                        (itinerary?['itinerary_data']['itinerary'] as List)[0]
                                ['postgres_data']?['photos']?[0] ??
                            'https://images.unsplash.com/photo-1596560548464-f010549b84d7?q=80&w=2070',
                        fit: BoxFit.cover,
                        color: Colors.black.withOpacity(0.2),
                        colorBlendMode: BlendMode.darken,
                      ),
                    ),
                    Positioned.fill(
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              Colors.transparent,
                              const Color(0xFF121212).withOpacity(0.2),
                              const Color(0xFF121212),
                            ],
                            stops: const [0.0, 0.5, 1.0],
                          ),
                        ),
                      ),
                    ),
                    // Drag Handle
                    Center(
                      child: Container(
                        width: 40,
                        height: 4,
                        margin: const EdgeInsets.only(top: 12),
                        decoration: BoxDecoration(
                          color: Colors.white24,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                    // Vibe Score Badge
                    Positioned(
                      top: 40,
                      right: 24,
                      child: _buildVibeBadge(widget.hotspot.densityScore.toInt()),
                    ),
                  ],
                ),

                // 2. CONTENT BODY
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "NEIGHBORHOOD SPOTLIGHT",
                        style: GoogleFonts.inter(
                          color: const Color(0xFFE91E63),
                          fontSize: 11,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.5,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        itinerary?['title'] ?? 'Trending Cluster',
                        style: GoogleFonts.playfairDisplay(
                          color: Colors.white,
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          height: 1.1,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          const Icon(Icons.place_outlined, color: Colors.white60, size: 16),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              "${(itinerary?['itinerary_data']['itinerary'] as List).length} curated stops",
                              style: GoogleFonts.inter(color: Colors.white60, fontSize: 13),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 16),
                          const Icon(Icons.directions_walk_rounded, color: Colors.white60, size: 16),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              itinerary?['walk_time_text'] ?? 'Short stroll',
                              style: GoogleFonts.inter(color: Colors.white60, fontSize: 13),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),

                      // 3. ROUTE VISUALIZER
                      ..._buildRouteVisualizer(itinerary?['itinerary_data']['itinerary'] as List),

                      const SizedBox(height: 32),

                      // 4. ACTION BUTTON
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: ElevatedButton(
                          onPressed: () {
                            Navigator.pop(context);
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ItineraryDetailScreen(itinerary: itinerary!),
                              ),
                            );
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: Colors.black,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(28),
                            ),
                            elevation: 0,
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                "View Full Plan",
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w900,
                                  fontSize: 16,
                                ),
                              ),
                              const SizedBox(width: 12),
                              const Icon(Icons.arrow_forward_rounded, size: 20),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildVibeBadge(int score) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFE91E63).withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFE91E63).withOpacity(0.3)),
      ),
      child: Column(
        children: [
          const Icon(Icons.local_fire_department_rounded, color: Color(0xFFE91E63), size: 22),
          Text(
            "$score",
            style: const TextStyle(
              color: Color(0xFFE91E63),
              fontWeight: FontWeight.w900,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildRouteVisualizer(List stops) {
    List<Widget> items = [];
    for (int i = 0; i < stops.length; i++) {
      items.add(_buildRouteStep(
        (i + 1).toString(),
        stops[i]['place_name'],
        stops[i]['postgres_data']?['rating']?.toString() ?? '4.5',
        stops[i],
      ));
      if (i < stops.length - 1) {
        items.add(_buildRouteConnector());
      }
    }
    return items;
  }

  Widget _buildRouteStep(String number, String name, String rating, Map<String, dynamic> place) {
    final imgUrl = place['postgres_data']?['photos']?[0];
    final placeDetailData = {
      'name': name,
      'rating': rating,
      'image_url': imgUrl,
      'categories': [place['postgres_data']?['category'] ?? 'Trending'],
      'ai_insight': place['ai_notes'],
      'price_range': place['postgres_data']?['price_range'] ?? '\$\$',
      'description': place['postgres_data']?['description'] ?? '',
    };

    return GestureDetector(
      onTap: () => showPlaceDetail(context, placeDetailData),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 4),
        color: Colors.transparent, // Improve tap target
        child: Row(
          children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white24, width: 1),
              ),
              child: Center(
                child: Text(
                  number,
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                name,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const Icon(Icons.star_rounded, color: Colors.amber, size: 14),
            const SizedBox(width: 2),
            Text(
              rating,
              style: GoogleFonts.inter(
                color: Colors.white60,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRouteConnector() {
    return Container(
      margin: const EdgeInsets.only(left: 10), // Aligns with circle center (width 20 / 2)
      height: 12,
      width: 1,
      color: Colors.white.withOpacity(0.15),
    );
  }
}

class EmojiHeatmapPainter extends CustomPainter {
  final List<HeatmapPolygon> dataPoints;
  final MapCamera camera;
  final String? vibe;
  final double pulseValue;
  final double appearanceValue; // New: Controls general opacity

  EmojiHeatmapPainter({
    required this.dataPoints,
    required this.camera,
    this.vibe,
    required this.pulseValue,
    required this.appearanceValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Sort points by density so bright ones draw on top
    final sortedPoints = List<HeatmapPolygon>.from(dataPoints)
      ..sort((a, b) => a.densityScore.compareTo(b.densityScore));

    for (final point in sortedPoints) {
      if (point.points.isEmpty) continue;

      // FILTER THE NOISE: Only draw if score is significant (e.g. > 30)
      // This removes the "checkerboard" of weak spots
      if (point.densityScore < 30) continue; 

      // 2. CONVERT & JITTER
      // We use the cellId string to generate a "consistent random" offset.
      // This ensures the point stays in the same place every frame (no shaking),
      // but doesn't look like a grid.
      final seed = point.cellId.hashCode;
      final random = math.Random(seed);
      
      // Random offset between -20px and +20px
      final dx = (random.nextDouble() - 0.5) * 40; 
      final dy = (random.nextDouble() - 0.5) * 40;

      final screenPos = camera.latLngToScreenPoint(point.points[0]);
      final offset = Offset(screenPos.x + dx, screenPos.y + dy);

      // 3. CALCULATE INTENSITY (0.0 to 1.0)
      final double intensity = (point.densityScore / 100).clamp(0.0, 1.0);

      // A. Pick Colors & Effective Vibe
      Color coreColor;
      String emoji;
      
      final effectiveVibe = (vibe == 'all' || vibe == null) 
          ? point.vibe 
          : vibe;
      
      if (effectiveVibe == 'coffee') {
        coreColor = const Color(0xFFFFB74D);
        emoji = '☕';
      } else if (effectiveVibe == 'nightlife') {
        coreColor = const Color(0xFFE040FB);
        emoji = '🍸';
      } else if (effectiveVibe == 'food') {
        coreColor = const Color(0xFF00E676);
        emoji = '🍽️';
      } else if (effectiveVibe == 'arts') {
        coreColor = const Color(0xFF29B6F6);
        emoji = '📍';
      } else {
        coreColor = const Color(0xFFB0BEC5);
        emoji = '🔍';
      }

      // --- VISUAL RENDERING ---
      
      // Layer 1: The "Atmosphere" (Scales with Score & Pulse)
      final double atmosphereRadius = 60.0 + (intensity * 120.0) + (pulseValue * 10);
      final double atmosphereOpacity = 0.2 + (intensity * 0.3); // range 0.2 -> 0.5
      
      final paintAtmosphere = Paint()
        ..shader = ui.Gradient.radial(
          offset,
          atmosphereRadius,
          [
            coreColor.withOpacity(atmosphereOpacity * appearanceValue), 
            coreColor.withOpacity(0.05 * appearanceValue), 
            Colors.transparent,
          ],
          const [0.0, 0.6, 1.0],
        )
        ..blendMode = BlendMode.screen;
      
      canvas.drawCircle(offset, atmosphereRadius, paintAtmosphere);

      // Layer 2: The "Core" (Heat Intensity)
      final double coreRadius = 30.0 + (intensity * 40.0) + (pulseValue * 5);
      final paintCore = Paint()
        ..shader = ui.Gradient.radial(
          offset,
          coreRadius,
          [
            coreColor.withOpacity(0.9 * appearanceValue), 
            coreColor.withOpacity(0.0), 
          ],
        )
        ..blendMode = BlendMode.screen;

      canvas.drawCircle(offset, coreRadius, paintCore);

      // Layer 3: The "White Hot" Center (Only for Super Hotspots > 80)
      if (point.densityScore > 80) {
        final double whiteHotRadius = 15.0 * intensity;
        final paintWhiteHot = Paint()
          ..shader = ui.Gradient.radial(
            offset,
            whiteHotRadius,
            [
              Colors.white.withOpacity(0.8 * appearanceValue), 
              Colors.white.withOpacity(0.0),
            ],
          )
          ..blendMode = BlendMode.overlay;

        canvas.drawCircle(offset, whiteHotRadius, paintWhiteHot);
      }

      // Layer 4: Emojis (Visible at high zoom)
      if (camera.zoom > 13.5) {
        final textSpan = TextSpan(
          text: emoji,
          style: TextStyle(
            fontSize: (18 + (intensity * 12)) * appearanceValue, 
            shadows: [
              Shadow(blurRadius: 15, color: coreColor, offset: Offset.zero),
              Shadow(blurRadius: 5, color: Colors.black.withOpacity(0.5), offset: Offset.zero),
            ]
          ),
        );
        
        final textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
        );
        textPainter.layout();
        
        final textOffset = Offset(
          offset.dx - (textPainter.width / 2),
          offset.dy - (textPainter.height / 2),
        );
        textPainter.paint(canvas, textOffset);
      }
    }
  }

  @override
  bool shouldRepaint(covariant EmojiHeatmapPainter oldDelegate) {
    return oldDelegate.pulseValue != pulseValue || 
           oldDelegate.appearanceValue != appearanceValue || // Track appearance changes
           oldDelegate.dataPoints != dataPoints || 
           oldDelegate.camera != camera;
  }
}

class CustomLayer extends StatelessWidget {
  final Widget Function(BuildContext, MapCamera) builder;
  const CustomLayer({super.key, required this.builder});

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);
    return builder(context, camera);
  }
}

class VibeAvatar extends StatelessWidget {
  final String category; // e.g. "Coffee", "Park", "Bar"
  final double size;

  const VibeAvatar({super.key, required this.category, this.size = 60});

  @override
  Widget build(BuildContext context) {
    final style = _getVibeStyle(category);

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        // The "Vibe" Gradient
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: style.colors,
        ),
        boxShadow: [
          BoxShadow(
            color: style.colors.first.withOpacity(0.4),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
        border: Border.all(color: Colors.white.withOpacity(0.15), width: 1),
      ),
      child: Center(
        child: Icon(
          style.icon,
          color: Colors.white.withOpacity(0.9),
          size: size * 0.4,
        ),
      ),
    );
  }

  VibeStyle _getVibeStyle(String category) {
    final cat = category.toLowerCase();
    
    // Coffee & Breakfast
    if (cat.contains('coffee') || cat.contains('cafe') || cat.contains('bakery') || cat.contains('breakfast')) {
      return VibeStyle(
        colors: [const Color(0xFFD48872), const Color(0xFF4E342E)],
        icon: Icons.coffee_rounded,
      );
    }
    // Nightlife & Drinks
    if (cat.contains('bar') || cat.contains('night') || cat.contains('club') || cat.contains('cocktail')) {
      return VibeStyle(
        colors: [const Color(0xFFE040FB), const Color(0xFF4A148C)],
        icon: Icons.local_bar_rounded,
      );
    }
    // Outdoors & Activities
    if (cat.contains('park') || cat.contains('nature') || cat.contains('garden') || cat.contains('outdoor')) {
      return VibeStyle(
        colors: [const Color(0xFF66BB6A), const Color(0xFF1B5E20)],
        icon: Icons.park_rounded,
      );
    }
    // Food & Dining
    if (cat.contains('food') || cat.contains('restaurant') || cat.contains('dinner') || cat.contains('lunch') || cat.contains('eat')) {
      return VibeStyle(
        colors: [const Color(0xFFFF7043), const Color(0xFFBF360C)],
        icon: Icons.restaurant_rounded,
      );
    }
    // Arts & Culture
    if (cat.contains('art') || cat.contains('museum') || cat.contains('gallery') || cat.contains('culture')) {
      return VibeStyle(
        colors: [const Color(0xFF4FC3F7), const Color(0xFF01579B)],
        icon: Icons.palette_rounded,
      );
    }
    // Shopping
    if (cat.contains('shop') || cat.contains('store') || cat.contains('boutique') || cat.contains('market')) {
      return VibeStyle(
        colors: [const Color(0xFFFFD54F), const Color(0xFFF57F17)],
        icon: Icons.shopping_bag_rounded,
      );
    }

    // Default / "Hidden Gem"
    return VibeStyle(
      colors: [const Color(0xFF78909C), const Color(0xFF37474F)],
      icon: Icons.auto_awesome_rounded, // Better "Gem" icon than the pin
    );
  }
}

class VibeStyle {
  final List<Color> colors;
  final IconData icon;
  VibeStyle({required this.colors, required this.icon});
}
