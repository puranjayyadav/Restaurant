import 'dart:ui' as ui;
import 'dart:math' as math;
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:google_fonts/google_fonts.dart';
import 'place_detail_sheet.dart';
import '../theme/design_system.dart';
import '../services/density_heatmap_service.dart';
import '../screens/itinerary_detail_screen.dart';
import '../api_service.dart';

class DensityHeatmapWidget extends StatefulWidget {
  final LatLng center;
  final String baseUrl;
  final String? selectedVibe; 
  final Function(String cellId, int placeCount)? onCellTap;
  final VoidCallback? onMapInteraction;
  final Function(LatLng location)? onMapLongPress;
  final LatLng? selectedLocation;

  const DensityHeatmapWidget({
    Key? key,
    required this.center,
    required this.baseUrl,
    this.selectedVibe,
    this.onCellTap,
    this.bottomOffset = 24.0, // Default to top if not specified? No, user wants it above bottom bar.
    this.onMapInteraction,
    this.onMapLongPress,
    this.selectedLocation,
  }) : super(key: key);

  final double bottomOffset;

  @override
  State<DensityHeatmapWidget> createState() => _DensityHeatmapWidgetState();
}

class _DensityHeatmapWidgetState extends State<DensityHeatmapWidget> 
    with TickerProviderStateMixin { 
  
  late DensityHeatmapService _service;
  List<HeatmapPolygon> _dataPoints = []; 
  List<Map<String, dynamic>> _rawPlaces = []; // NEW: Individual places
  bool _isLoading = false;
  bool _showMarkers = true; // NEW: Toggle for individual markers
  late AnimationController _pulseController; 
  late AnimationController _fadeController;
  late AnimationController _insightController; // New: For insight bubble
  late MapController _mapController;
  Timer? _debounce;
  Timer? _insightTimer; // Rotates insights
  late LatLng _activeCenter;
  HeatmapPolygon? _highlightedPoint; // Point currently showing insight
  String _currentInsight = "";
  bool _showSearchButton = false;
  bool _showingAllGlobal = false; // NEW: Toggle state for showing all Supabase places vs local

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

    // Insight Animation (Fade in/out tooltips)
    _insightController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _mapController = MapController();
    _activeCenter = widget.center;

    _loadHeatmap();
    _startInsightRotation();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _insightTimer?.cancel();
    _pulseController.dispose();
    _fadeController.dispose();
    _insightController.dispose();
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

    // Fetch both heatmap and raw markers in parallel
    try {
      final results = await Future.wait([
        _service.fetchHeatmap(
          lat: _activeCenter.latitude,
          lng: _activeCenter.longitude,
          vibe: widget.selectedVibe,
          gridSize: 0.003,
          gridCount: 30, // 30x30 grid for maximum population
        ),
        _loadMarkers(),
      ]);

      if (!mounted) return;

      final geojson = results[0] as Map<String, dynamic>;
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
          final hotCenter = LatLng(
              sumLat / bestSpot.points.length, sumLng / bestSpot.points.length);

          // Trigger cinematic flight
          _animatedMapMove(hotCenter, 14.5);
        }
      }
    } catch (e) {
      debugPrint("DEBUG: Error in _loadHeatmap: $e");
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadMarkers() async {
    if (!mounted) return;
    
    // If showing global data, don't use local markers
    if (_showingAllGlobal) return;

    try {
      final api = ApiService();
      final places = await api.getScrapedRestaurants(
        lat: _activeCenter.latitude,
        lng: _activeCenter.longitude,
        radiusKm: 2.0, // Smaller radius for individual markers
        limit: 80,
      );
      
      if (mounted) {
        setState(() {
          _rawPlaces = places;
        });
      }
    } catch (e) {
      debugPrint("DEBUG: Error loading raw markers: $e");
    }
  }

  Future<void> _loadAllPlaces() async {
    if (!mounted) return;
    setState(() => _isLoading = true);

    try {
      final api = ApiService();
      final places = await api.getSupabaseAllPlaces(limit: 1500);
      
      if (mounted) {
        setState(() {
          _rawPlaces = places;
          _isLoading = false;
          _showMarkers = true; // Force show if fetching all
        });
      }
    } catch (e) {
      debugPrint("DEBUG: Error loading all places: $e");
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

  // --- INSIGHT ROTATION LOGIC ---
  void _startInsightRotation() {
    _insightTimer?.cancel();
    _insightTimer = Timer.periodic(const Duration(seconds: 10), (timer) {
      if (!mounted || _dataPoints.isEmpty) {
        debugPrint("Insight Check: No data points or not mounted. skipping.");
        return;
      }

      // Filter for strong points visible in current viewport
      final bounds = _mapController.camera.visibleBounds;
      final candidates = _dataPoints.where((p) {
        if (p.densityScore <= 30) return false;
        if (p.points.isEmpty) return false;
        // Check if point is onscreen
        return bounds.contains(p.points.first);
      }).toList();

      if (candidates.isEmpty) {
        debugPrint("Insight Check: No visible candidates > 30 density.");
        return;
      }

      // Pick random hotspot
      final nextPoint = candidates[math.Random().nextInt(candidates.length)];
      debugPrint("Insight Selected: ${nextPoint.vibe} at ${nextPoint.cellId}");
      
      // Generate hook
      final hook = _generateContextualHook(nextPoint);

      if (mounted) {
        // 1. Fade OUT old one (if any)
        _insightController.reverse().then((_) {
          if (!mounted) return;
          setState(() {
            _highlightedPoint = nextPoint;
            _currentInsight = hook;
          });
          // 2. Fade IN new one
          _insightController.forward().then((_) {
            // 3. Wait and fade out
            Future.delayed(const Duration(seconds: 6), () {
              if (mounted) _insightController.reverse();
            });
          });
        });
      }
    });
  }

  String _generateContextualHook(HeatmapPolygon point) {
    // ---------- helpers ----------
    final rnd = math.Random();

    String pick(List<String> list) => list[rnd.nextInt(list.length)];

    String trimBubble(String s, {int max = 38}) {
      if (s.length <= max) return s;
      return "${s.substring(0, max - 3)}...";
    }

    bool hasAny(String vibe, List<String> keys) =>
        keys.any((k) => vibe.contains(k));

    // Soft context tags you can sprinkle in (kept short)
    String? ratingTag() {
      final r = point.avgRating;
      if (r >= 4.8) return "Elite-rated ⭐";
      if (r >= 4.6) return "Top-rated ⭐";
      if (r >= 4.4) return "Crowd favorite ⭐";
      return null;
    }

    String? densityTag() {
      final c = point.placeCount;
      if (c >= 30) return "Packed zone 🔥";
      if (c >= 18) return "Hot cluster 🔥";
      if (c >= 10) return "Lots to do 👀";
      return null;
    }

    // Randomly attach a tag sometimes
    String maybeTag(String base) {
      final tags = <String?>[ratingTag(), densityTag()];
      final available = tags.whereType<String>().toList();
      if (available.isEmpty) return base;

      // ~35% chance to append tag for variety
      if (rnd.nextDouble() < 0.35) {
        return "$base · ${pick(available)}";
      }
      return base;
    }

    // ---------- 1) real backend notes ----------
    if (point.notes.isNotEmpty) {
      final realNotes = point.notes.where((n) => n.trim().length < 45).toList();
      if (realNotes.isNotEmpty) return trimBubble(pick(realNotes), max: 42);

      final note = pick(point.notes);
      return trimBubble(note, max: 42);
    }

    // ---------- 2) generated hooks ----------
    final vibe = (point.vibe ?? 'explore').toLowerCase();

    // Big library of hooks (keep each string bubble-friendly)
    final Map<String, List<String>> hooks = {
      // COFFEE / CAFES
      "coffee": [
        "Morning fuel spot ☕",
        "Hidden espresso bar 🔥",
        "Best work + wifi 💻",
        "Quiet corner café 🤫",
        "Pour-over heaven ✨",
        "Iced latte go-to 🧊",
        "Barista’s pick 👀",
        "Cozy vibes inside 🕯️",
        "Coffee + pastries 💛",
        "Local favorite café ⭐",
        "Perfect rainy-day sip 🌧️",
        "Your new caffeine ritual ⚡",
        "Walk in, stay awhile 🪑",
        "Study mode activated 📚",
        "Cold brew hit list 🧊",
        "Matcha moment 🍵",
        "Cute café aesthetic 📸",
        "Quick grab-and-go ☕",
        "Slow morning energy 🌤️",
        "Playlist is elite 🎧",
      ],

      // BAKERY / PASTRY / DESSERT
      "bakery": [
        "Fresh-baked smells 🤤",
        "Croissant level: insane 🥐",
        "Sweet tooth stop 🍰",
        "Dessert worth detouring 🍮",
        "Iconic pastry counter ✨",
        "Warm cookies nearby 🍪",
        "Creamy gelato run 🍨",
        "Late-night dessert fix 🌙",
        "Tiramisu check ✅",
        "Cinnamon roll therapy 🌀",
        "Best bite-sized treats 😋",
        "Cute dessert date 🍓",
        "Cake slice heaven 🍰",
        "Just one more… 🍩",
        "Bakery gem alert 🚨",
      ],

      // BRUNCH
      "brunch": [
        "Brunch line = worth it 🥑",
        "Weekend ritual spot 🍳",
        "Eggs + vibes ✅",
        "Pancakes are the move 🥞",
        "Mimosas + sunlight 🥂",
        "Cozy brunch nook 🪟",
        "Best benedict in town 🍳",
        "Biscuit energy 😮‍💨",
        "Brunch date approved 💛",
        "Savory or sweet? both 😌",
        "Wake up + treat yourself 🌞",
      ],

      // FOOD (GENERIC)
      "food": [
        "Must-try eats 🍜",
        "Chef’s choice energy 👨‍🍳",
        "Always busy for a reason 🔥",
        "Comfort food zone 🫶",
        "Flavor bomb incoming 💥",
        "Go-to dinner pick 🍽️",
        "Casual bite, big taste 😋",
        "Your next obsession 👀",
        "Worth the hype ✅",
        "Local legend spot ⭐",
        "Best bang-for-buck 💸",
        "Bring friends, share plates 🍴",
        "No bad orders here 😮‍💨",
        "Peak cravings satisfied 🤤",
        "One of those places ✨",
      ],

      // STREET FOOD / QUICK BITES
      "street": [
        "Quick bite, huge payoff 🌮",
        "Street food paradise 🔥",
        "Late snack mission ✅",
        "Grab it + keep moving 🏃",
        "Crispy, spicy, perfect 🌶️",
        "Fast, messy, worth it 😅",
        "Takeout king 👑",
        "You’ll want seconds 😋",
        "Under-\$15 hero 💸",
      ],

      // RAMEN / NOODLES
      "ramen": [
        "Broth that heals 🍜",
        "Ramen weather spot ❄️",
        "Noodle slurp heaven 😮‍💨",
        "Spicy miso challenge 🌶️",
        "Perfect late-night bowl 🌙",
        "Tonkotsu dreams 🐷",
        "Hand-pulled noodles 👀",
        "Comfort bowl unlocked 🔓",
        "Instant serotonin 🍜",
      ],

      // PIZZA
      "pizza": [
        "Slice you’ll remember 🍕",
        "Crispy crust perfection 🔥",
        "Late-night pizza run 🌙",
        "Cheese pull moment 🧀",
        "Neighborhood slice spot ⭐",
        "Sauce is elite 🍅",
        "One more slice… 😅",
        "Group-friendly feast 🍕",
      ],

      // BURGERS
      "burger": [
        "Burger cravings solved 🍔",
        "Smashburger magic 🔥",
        "Juicy + messy + perfect 😅",
        "Fries are mandatory 🍟",
        "Classic done right ✅",
        "Secret sauce situation 👀",
        "Top-tier combo meal 🍔",
      ],

      // SUSHI
      "sushi": [
        "Fresh fish flex 🐟",
        "Omakase energy ✨",
        "Sushi date night 💛",
        "Nigiri you’ll dream of 😮‍💨",
        "Hidden sushi gem 🚨",
        "Rolls on point ✅",
        "Clean, calm, perfect 🍣",
      ],

      // TACOS / MEXICAN
      "tacos": [
        "Taco run time 🌮",
        "Birria cravings here 🔥",
        "Salsa level: dangerous 🌶️",
        "Street tacos done right ✅",
        "Al pastor perfection 🐖",
        "Late-night tacos 🌙",
        "Fresh tortillas alert 👀",
      ],

      // ASIAN (GENERAL)
      "asian": [
        "Spice + umami hit 😮‍💨",
        "Comfort classics ✅",
        "Wok hei energy 🔥",
        "Dumpling mission 🥟",
        "Soup + vibes 🍲",
        "Share plates with friends 🍴",
        "Hidden menu vibes 👀",
      ],

      // VEGAN / HEALTH
      "vegan": [
        "Plant-based done right 🌿",
        "Fresh + clean eats 🥗",
        "Protein without heaviness 💪",
        "Feel-good lunch spot ✨",
        "Vegan comfort food 🤤",
        "Glow-up meal ✅",
        "Healthy but tasty 😌",
      ],

      // BAR / NIGHTLIFE
      "bar": [
        "Great cocktails here 🍸",
        "Mood setter spot ✨",
        "Pre-game headquarters 🍻",
        "Hidden speakeasy vibes 🥃",
        "Date night drinks 💛",
        "Neon nights ahead 🌙",
        "Loud laughs, good pours 😄",
        "One more round? 😅",
        "Perfect group hang 🔥",
        "Bartender knows best 👀",
      ],

      // ROOFTOP
      "rooftop": [
        "Rooftop views = insane 🌆",
        "Golden hour drinks 🌅",
        "Skyline moment �",
        "Wind-down up top ✨",
        "Dress up a little 💫",
        "Best night view 🌙",
      ],

      // LIVE MUSIC
      "music": [
        "Live music tonight 🎶",
        "Hidden stage energy 🔥",
        "Dance-floor temptation 💃",
        "Indie gig vibes 🎸",
        "DJ nights here 🎧",
        "Loud + fun + perfect 😄",
        "Showtime spot 🎤",
      ],

      // PARK / WALK / NATURE
      "park": [
        "Scenic route 🌿",
        "Quiet oasis 🍃",
        "Best sunset view 🌅",
        "Picnic energy 🧺",
        "Nature reset spot 🌳",
        "Breathe here 😮‍💨",
        "Golden hour stroll ✨",
        "Dog-walk friendly 🐶",
        "Shady + peaceful 🌤️",
      ],

      // VIEWPOINT / PHOTO SPOT
      "view": [
        "Photo spot alert 📸",
        "View is unreal 🌅",
        "Golden hour magnet ✨",
        "Postcard moment 🗺️",
        "Panorama vibes 🌆",
        "Camera roll upgrade 📸",
      ],

      // SHOPPING
      "shopping": [
        "Cute finds inside 🛍️",
        "Window-shopping heaven ✨",
        "Treat yourself zone 💸",
        "Local brands here 👀",
        "Walk in, leave happy 😌",
        "Hidden shop gem 🚨",
      ],

      // THRIFT / VINTAGE
      "thrift": [
        "Vintage finds waiting 👀",
        "Thrift gold mine 💎",
        "One-of-one pieces ✨",
        "Dig through treasures 🧤",
        "Cheap + cool combo 💸",
        "Style hunt time 🛍️",
      ],

      // ART / MUSEUM
      "museum": [
        "Art break 🎨",
        "Museum date idea 💛",
        "Quiet + inspiring ✨",
        "Gallery hop energy �️",
        "Culture fix ✅",
        "Spend an hour here ⏳",
      ],

      // BOOKSTORE / STUDY
      "books": [
        "Bookstore calm 📚",
        "Quiet reading corner 🤫",
        "Study-friendly spot 💻",
        "Browse + decompress 😌",
        "Hidden shelves 👀",
        "Coffee + books combo ☕",
      ],

      // FAMILY / KIDS
      "family": [
        "Kid-friendly stop 👶",
        "Easy family outing ✅",
        "Low-stress fun 🎈",
        "Everyone will like this 😄",
        "Quick + safe choice 👍",
      ],

      // DATE NIGHT
      "date": [
        "Date night approved 💛",
        "Romantic corner ✨",
        "Soft lights + vibes 🕯️",
        "Dress up energy 💫",
        "Two-person perfect 🍷",
        "Main character moment 🎬",
      ],

      // ADVENTURE / UNIQUE
      "unique": [
        "You haven’t seen this 😮‍💨",
        "Hidden gem alert 🚨",
        "Local secret spot 🤫",
        "Worth the detour ✅",
        "Unexpectedly amazing 👀",
        "New vibe unlocked 🔓",
        "This place surprises you ✨",
      ],

      // DEFAULT EXPLORE
      "explore": [
        "Check this out ✨",
        "Try something new 👀",
        "Solid stop nearby ✅",
        "Quick detour idea 🗺️",
        "Explore mode on 🔥",
        "Little discovery moment ✨",
        "Worth a look 👀",
      ],
    };

    // ---------- vibe routing ----------
    // Note: lots of overlapping keywords so “coffee + work” still hits coffee.
    List<String> pool;

    if (hasAny(vibe, ["coffee", "cafe", "espresso", "latte", "matcha"])) {
      pool = hooks["coffee"]!;
    } else if (hasAny(vibe, ["bakery", "pastry", "dessert", "gelato", "ice", "cake", "donut"])) {
      pool = hooks["bakery"]!;
    } else if (hasAny(vibe, ["brunch", "breakfast", "bfast"])) {
      pool = hooks["brunch"]!;
    } else if (hasAny(vibe, ["ramen", "noodle", "pho", "udon"])) {
      pool = hooks["ramen"]!;
    } else if (hasAny(vibe, ["pizza"])) {
      pool = hooks["pizza"]!;
    } else if (hasAny(vibe, ["burger", "smash"])) {
      pool = hooks["burger"]!;
    } else if (hasAny(vibe, ["sushi", "omakase"])) {
      pool = hooks["sushi"]!;
    } else if (hasAny(vibe, ["taco", "mex", "birria"])) {
      pool = hooks["tacos"]!;
    } else if (hasAny(vibe, ["vegan", "healthy", "salad", "fitness"])) {
      pool = hooks["vegan"]!;
    } else if (hasAny(vibe, ["bar", "night", "club", "cocktail", "pub"])) {
      pool = hooks["bar"]!;
    } else if (hasAny(vibe, ["rooftop", "skyline"])) {
      pool = hooks["rooftop"]!;
    } else if (hasAny(vibe, ["music", "live", "concert", "dj"])) {
      pool = hooks["music"]!;
    } else if (hasAny(vibe, ["park", "walk", "trail", "nature", "garden"])) {
      pool = hooks["park"]!;
    } else if (hasAny(vibe, ["view", "photo", "scenic", "sunset"])) {
      pool = hooks["view"]!;
    } else if (hasAny(vibe, ["thrift", "vintage"])) {
      pool = hooks["thrift"]!;
    } else if (hasAny(vibe, ["shop", "shopping", "boutique", "market"])) {
      pool = hooks["shopping"]!;
    } else if (hasAny(vibe, ["museum", "art", "gallery"])) {
      pool = hooks["museum"]!;
    } else if (hasAny(vibe, ["book", "study", "library"])) {
      pool = hooks["books"]!;
    } else if (hasAny(vibe, ["date", "romantic"])) {
      pool = hooks["date"]!;
    } else if (hasAny(vibe, ["family", "kids", "child"])) {
      pool = hooks["family"]!;
    } else if (hasAny(vibe, ["street", "quick", "takeout", "grab"])) {
      pool = hooks["street"]!;
    } else if (hasAny(vibe, ["food", "dinner", "lunch", "eat"])) {
      pool = hooks["food"]!;
    } else if (hasAny(vibe, ["hidden", "unique", "secret", "gem"])) {
      pool = hooks["unique"]!;
    } else {
      pool = hooks["explore"]!;
    }

    // ---------- global “quality” overrides ----------
    // Keep your original logic but make it less repetitive by randomizing within a set
    final qualityHooks = <String>[];
    if (point.avgRating >= 4.7) qualityHooks.addAll([
      "Top neighborhood gem ✨",
      "Elite local favorite ⭐",
      "Best in the area ✅",
      "People swear by this 🔥",
      "Consistently amazing ⭐",
    ]);
    if (point.placeCount >= 20) qualityHooks.addAll([
      "Busy social hub 🔥",
      "Hotspot cluster 👀",
      "Lots happening here ⚡",
      "Crowded for a reason 🔥",
      "Peak vibes zone ✨",
    ]);

    // 20% chance to use a quality hook if available
    String base;
    if (qualityHooks.isNotEmpty && rnd.nextDouble() < 0.20) {
      base = pick(qualityHooks);
    } else {
      // Otherwise use vibe pool
      base = pick(pool);
    }

    // Add a contextual tag sometimes
    final hooked = maybeTag(base);

    // Bubble-safe trim
    return trimBubble(hooked, max: 42);
  }


  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // 1. BRIGHT AIRY MAP (Light café aesthetic)
        FlutterMap(
          mapController: _mapController, // Use controller
          options: MapOptions(
            initialCenter: widget.center,
            initialZoom: 13.5,
            onPositionChanged: (position, hasGesture) {
              if (hasGesture && position.center != null) {
                _onMapMoved(position.center!);
                widget.onMapInteraction?.call();
              }
            },
            onTap: (tapPosition, latLng) => _handleSmartTap(latLng), // SMART TAP LOGIC
            onLongPress: (tapPosition, latLng) => widget.onMapLongPress?.call(latLng),
            interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
            ),
          ),
          children: [
            // Light, Clean Base Layer (CartoDB Positron - Bright and minimal)
            TileLayer(
              urlTemplate: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
              subdomains: const ['a', 'b', 'c', 'd'],
              userAgentPackageName: 'com.example.restaurant_tracker',
              retinaMode: MediaQuery.of(context).devicePixelRatio > 1.0,
            ),

            // 2. RAW PLACES MARKERS (The request)
            if (_showMarkers)
              MarkerLayer(
                markers: _rawPlaces.map((place) {
                  return Marker(
                    point: LatLng(
                      double.tryParse(place['latitude'].toString()) ?? 0.0,
                      double.tryParse(place['longitude'].toString()) ?? 0.0,
                    ),
                    width: 45,
                    height: 45,
                    child: GestureDetector(
                      onTap: () => showPlaceDetail(context, place),
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.1),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                          border: Border.all(color: AppColors.orange.withOpacity(0.8), width: 2),
                        ),
                        child: const Center(
                          child: Icon(
                            Icons.location_on_rounded, // Use a more distinct discovery icon
                            size: 18,
                            color: AppColors.orange,
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),

            CustomLayer(
              builder: (context, camera) {
                // Safety check: ensure controllers are initialized before building
                // This prevents crashes during hot reloads when new state fields are added
                return AnimatedBuilder(
                  animation: Listenable.merge([
                    _pulseController, 
                    _fadeController, 
                    _insightController
                  ]),
                  builder: (context, child) {
                    return SizedBox.expand(
                      child: CustomPaint(
                        painter: EmojiMarkerPainter(
                          dataPoints: _dataPoints,
                          camera: camera,
                          vibe: widget.selectedVibe,
                          pulseValue: _pulseController.value,
                          appearanceValue: _fadeController.value,
                          highlightedPoint: _highlightedPoint,
                          insightMessage: _currentInsight,
                          insightOpacity: _insightController.value,
                        ),
                      ),
                    );
                  },
                );
              },
            ),
            
            if (widget.selectedLocation != null)
              MarkerLayer(
                markers: [
                  Marker(
                    point: widget.selectedLocation!,
                    width: 40,
                    height: 40,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        // Soft shadow for depth
                        Container(
                          width: 8, height: 8,
                          decoration: BoxDecoration(
                            color: Colors.black26,
                            borderRadius: BorderRadius.circular(4),
                            boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 10, spreadRadius: 2)],
                          ),
                        ),
                        // The actual Pin icon
                        const Icon(
                          Icons.location_on, 
                          color: Color(0xFFE91E63), 
                          size: 40,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
          ],
        ),
        
        // Subtle Vignette Overlay - Soft focus effect for light theme
        IgnorePointer(
          child: Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: Alignment.center,
                radius: 1.3,
                colors: [
                  Colors.transparent,
                  Colors.white.withOpacity(0.05),
                  Colors.white.withOpacity(0.15),
                ],
                stops: const [0.5, 0.8, 1.0],
              ),
            ),
          ),
        ),

        // 4. MARKER TOGGLE (Manual verification helper)
        Positioned(
          top: 140,
          right: 20,
          child: Column(
            children: [
              GestureDetector(
                onTap: () => setState(() => _showMarkers = !_showMarkers),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.9),
                    shape: BoxShape.circle,
                    boxShadow: AppShadows.soft,
                    border: Border.all(color: Colors.black.withOpacity(0.05)),
                  ),
                  child: Icon(
                    _showMarkers ? Icons.visibility : Icons.visibility_off,
                    color: AppColors.orange,
                    size: 20,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              // NEW: Global Toggle
              GestureDetector(
                onTap: () {
                  setState(() {
                    _showingAllGlobal = !_showingAllGlobal;
                  });
                  if (_showingAllGlobal) {
                    _loadAllPlaces();
                  } else {
                    _loadMarkers();
                  }
                },
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _showingAllGlobal ? AppColors.orange : Colors.white.withOpacity(0.9),
                    shape: BoxShape.circle,
                    boxShadow: AppShadows.soft,
                    border: Border.all(color: Colors.black.withOpacity(0.05)),
                  ),
                  child: Icon(
                    Icons.public,
                    color: _showingAllGlobal ? Colors.white : AppColors.orange,
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ),

        // Loading Indicator (Subtle, dark for light theme)
        if (_isLoading)
          Positioned(
            top: 200, // Push down below toggle
            right: 20,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: BackdropFilter(
                filter: ui.ImageFilter.blur(sigmaX: 5, sigmaY: 5),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.7),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.black.withOpacity(0.05)),
                  ),
                  child: const SizedBox(
                    width: 16, height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black38),
                  ),
                ),
              ),
            ),
          ),

        // 4. "Search this area" Button
        if (_showSearchButton && !_isLoading)
          AnimatedPositioned(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            bottom: widget.bottomOffset, 
            left: 0,
            right: 0,
            child: Center(
              child: _buildSearchAreaButton(),
            ),
          ),
      ],
    );
  }

  Widget _buildSearchAreaButton() {
    return GestureDetector(
      onTap: () {
        setState(() => _showSearchButton = false);
        _loadHeatmap(shouldMoveCamera: false);
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ui.ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.9),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.black.withOpacity(0.08)),
              boxShadow: [
                BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 10, offset: const Offset(0, 4))
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.search_rounded, size: 16, color: Colors.black87),
                const SizedBox(width: 8),
                Text(
                  "Search this area",
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Colors.black87,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // --- SMART DEBOUNCER: Auto-reload with manual override ---
  void _onMapMoved(LatLng newCenter) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();

    // Show button immediately for manual control
    if (mounted) {
      setState(() {
        _activeCenter = newCenter;
        _showSearchButton = true;
      });
    }

    // Auto-reload after 1 second of no movement
    _debounce = Timer(const Duration(milliseconds: 1000), () {
      if (mounted && _showSearchButton) {
        debugPrint("Auto-reloading heatmap for new area");
        _loadHeatmap(shouldMoveCamera: false);
        setState(() => _showSearchButton = false);
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
                        _getHeroImageUrl(itinerary),
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
                              "${(itinerary?['itinerary_data']?['itinerary'] as List?)?.length ?? 0} curated stops",
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
                      ..._buildRouteVisualizer((itinerary?['itinerary_data']?['itinerary'] as List?) ?? []),

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

  String _getHeroImageUrl(Map<String, dynamic>? itinerary) {
    // Try hero_image_url first
    if (itinerary?['hero_image_url'] != null) {
      return itinerary!['hero_image_url'] as String;
    }
    
    // Try to get from first stop's photos
    final itineraryList = itinerary?['itinerary_data']?['itinerary'] as List?;
    if (itineraryList != null && itineraryList.isNotEmpty) {
      final firstStop = itineraryList[0] as Map<String, dynamic>?;
      final photos = firstStop?['postgres_data']?['photos'] as List?;
      if (photos != null && photos.isNotEmpty) {
        return photos[0] as String;
      }
    }
    
    // Default fallback image
    return 'https://images.unsplash.com/photo-1596560548464-f010549b84d7?q=80&w=2070';
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

/// Emoji Marker Painter - Clean iOS-style emoji markers
class EmojiMarkerPainter extends CustomPainter {
  final List<HeatmapPolygon> dataPoints;
  final MapCamera camera;
  final String? vibe;
  final double pulseValue;
  final double appearanceValue;
  final HeatmapPolygon? highlightedPoint;
  final String insightMessage;
  final double insightOpacity;

  EmojiMarkerPainter({
    required this.dataPoints,
    required this.camera,
    this.vibe,
    required this.pulseValue,
    required this.appearanceValue,
    this.highlightedPoint,
    this.insightMessage = "",
    this.insightOpacity = 0.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final sortedPoints = List<HeatmapPolygon>.from(dataPoints)
      ..sort((a, b) => a.densityScore.compareTo(b.densityScore));

    for (final point in sortedPoints) {
      if (point.points.isEmpty) continue;
      if (point.densityScore < 1) continue; // Only show meaningful hotspots

      final seed = point.cellId.hashCode;
      final random = math.Random(seed);
      final dx = (random.nextDouble() - 0.5) * 35;
      final dy = (random.nextDouble() - 0.5) * 35;

      final screenPos = camera.latLngToScreenPoint(point.points[0]);
      final offset = Offset(screenPos.x + dx, screenPos.y + dy);
      final intensity = (point.densityScore / 100).clamp(0.0, 1.0);

      final emoji = _getEmojiForCategory(point.vibe ?? vibe ?? 'explore');
      final accentColor = _getColorForCategory(point.vibe ?? vibe ?? 'explore');

      _paintEmoji(canvas, offset, emoji, accentColor, intensity, pulseValue, appearanceValue);

      // Render Insight Bubble if this is the highlighted point
      if (point.cellId == highlightedPoint?.cellId && insightOpacity > 0) {
        _paintInsightBubble(canvas, offset, insightMessage, insightOpacity);
      }
    }
  }

  void _paintInsightBubble(Canvas canvas, Offset emojiCenter, String message, double opacity) {
    final bubbleOffset = emojiCenter.translate(0, -35); // Above emoji
    
    final textSpan = TextSpan(
      text: message,
      style: GoogleFonts.nanumPenScript(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: Colors.black.withOpacity(opacity),
        letterSpacing: 0.0,
      ),
    );

    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();

    // Bubble Background (Glassmorphic toolip)
    final bubbleWidth = textPainter.width + 20;
    final bubbleHeight = textPainter.height + 12;
    final rect = Rect.fromCenter(center: bubbleOffset, width: bubbleWidth, height: bubbleHeight);
    
    final rRect = RRect.fromRectAndRadius(rect, const Radius.circular(20));
    
    // Shadow
    canvas.drawRRect(
      rRect.shift(const Offset(0, 4)),
      Paint()
        ..color = Colors.black.withOpacity(opacity * 0.1)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );

    // Body
    canvas.drawRRect(
      rRect,
      Paint()..color = Colors.white.withOpacity(opacity * 0.95),
    );

    // Border (soft)
    canvas.drawRRect(
      rRect,
      Paint()
        ..color = Colors.black.withOpacity(opacity * 0.05)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );

    // Pointer (little triangle)
    final path = ui.Path()
      ..moveTo(bubbleOffset.dx - 6, bubbleOffset.dy + bubbleHeight/2)
      ..lineTo(bubbleOffset.dx + 6, bubbleOffset.dy + bubbleHeight/2)
      ..lineTo(bubbleOffset.dx, bubbleOffset.dy + bubbleHeight/2 + 6)
      ..close();
    
    canvas.drawPath(
      path,
      Paint()..color = Colors.white.withOpacity(opacity * 0.95),
    );

    // Paint Text
    textPainter.paint(
      canvas, 
      bubbleOffset.translate(-textPainter.width / 2, -textPainter.height / 2),
    );
  }

  void _paintEmoji(
    Canvas canvas,
    Offset center,
    String emoji,
    Color accentColor,
    double intensity,
    double pulseValue,
    double appearanceValue,
  ) {
    final baseSize = 30.0 + (intensity * 12.0);
    final fontSize = baseSize * appearanceValue;

    // Subtle drop shadow
    final shadowPaint = Paint()
      ..color = Colors.black.withOpacity(0.15 * appearanceValue)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    
    canvas.drawCircle(center.translate(0, 2), fontSize * 0.4, shadowPaint);

    // Optional subtle glow for high-intensity spots
    if (intensity > 0.6) {
      final glowPaint = Paint()
        ..shader = ui.Gradient.radial(
          center,
          fontSize * 0.8,
          [
            accentColor.withOpacity(0.15 * appearanceValue),
            Colors.transparent,
          ],
        )
        ..blendMode = BlendMode.screen;
      
      canvas.drawCircle(center, fontSize * 0.8, glowPaint);
    }

    // Render emoji
    final textSpan = TextSpan(
      text: emoji,
      style: TextStyle(
        fontSize: fontSize,
        fontFamilyFallback: const [
          'Apple Color Emoji',
          'Segoe UI Emoji',
          'Noto Color Emoji',
        ],
        shadows: [
          Shadow(
            blurRadius: 2,
            color: Colors.white.withOpacity(0.8),
            offset: const Offset(0, 0),
          ),
        ],
      ),
    );

    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();

    final textOffset = Offset(
      center.dx - (textPainter.width / 2),
      center.dy - (textPainter.height / 2),
    );
    textPainter.paint(canvas, textOffset);
  }

  String _getEmojiForCategory(String category) {
    final cat = category.toLowerCase();

    // Primary Categories
    if (cat.contains('coffee') || cat.contains('cafe')) return '☕️'; // ceramic cup, very iOS
    if (cat.contains('nightlife') || cat.contains('bar') || cat.contains('cocktail')) return '🍷'; // warmer & cozier than 🍸
    if (cat.contains('park') || cat.contains('nature') || cat.contains('outdoor')) return '🌿'; // calm, breathable
    if (cat.contains('shopping') || cat.contains('shop') || cat.contains('boutique')) return '🛍️'; // subtle iOS bag
    if (cat.contains('landmark') || cat.contains('view') || cat.contains('scenic')) return '📍'; // location-first, not camera-heavy
    if (cat.contains('arts') || cat.contains('museum') || cat.contains('gallery')) return '🖼️'; // iOS-style framed art
    if (cat.contains('entertainment') || cat.contains('music') || cat.contains('theatre')) return '🎶'; // softer than 🎭
    if (cat.contains('hotel') || cat.contains('stay')) return '🛎️'; // hospitality feel > building emoji
    if (cat.contains('wellness') || cat.contains('spa') || cat.contains('yoga')) return '🧘‍♀️'; // calmer than 🧖

    // Food Categories - More Variety!
    if (cat.contains('pizza') || cat.contains('italian')) return '🍕';
    if (cat.contains('sushi') || cat.contains('japanese') || cat.contains('ramen')) return '🍜';
    if (cat.contains('burger') || cat.contains('american')) return '🍔';
    if (cat.contains('taco') || cat.contains('mexican') || cat.contains('burrito')) return '🌮';
    if (cat.contains('chinese') || cat.contains('dim sum') || cat.contains('noodle')) return '🥡';
    if (cat.contains('thai') || cat.contains('curry') || cat.contains('asian')) return '🍛';
    if (cat.contains('french') || cat.contains('bistro')) return '🥖';
    if (cat.contains('seafood') || cat.contains('fish')) return '🦞';
    if (cat.contains('steak') || cat.contains('bbq') || cat.contains('grill')) return '🥩';
    if (cat.contains('salad') || cat.contains('healthy') || cat.contains('vegan')) return '🥗';
    if (cat.contains('sandwich') || cat.contains('deli')) return '🥪';
    if (cat.contains('bakery') || cat.contains('bread')) return '🥐';
    if (cat.contains('ice cream') || cat.contains('gelato')) return '🍦';
    if (cat.contains('wine') || cat.contains('vineyard')) return '🍷';
    if (cat.contains('beer') || cat.contains('brewery') || cat.contains('pub')) return '🍺';
    
    // Meal Times
    if (cat.contains('brunch') || cat.contains('breakfast')) return '🥐'; // perfect cozy emoji
    if (cat.contains('lunch')) return '🥙';
    if (cat.contains('dinner')) return '🍽️';
    
    // Desserts & Sweets
    if (cat.contains('dessert') || cat.contains('sweet')) return '🍰';
    if (cat.contains('donut') || cat.contains('doughnut')) return '🍩';
    if (cat.contains('cake') || cat.contains('pastry')) return '🧁';
    
    // Other Categories
    if (cat.contains('sunset') || cat.contains('evening')) return '🌇'; // VERY cozy for maps
    if (cat.contains('walk') || cat.contains('stroll')) return '🚶‍♂️';
    
    // Generic food fallback (if it contains 'food' or 'restaurant' but no specific type)
    if (cat.contains('food') || cat.contains('restaurant') || cat.contains('dining')) return '🍽️';

    return '✨'; // default: soft highlight instead of hard pin
  }


  Color _getColorForCategory(String category) {
    final cat = category.toLowerCase();

    // Premium, muted discovery palette
    if (cat.contains('coffee')) return const Color(0xFF8D6E63); // Warm Espresso
    if (cat.contains('dinner') || cat.contains('food')) return const Color(0xFFD84315); // Deep Saffron
    if (cat.contains('nightlife')) return const Color(0xFF7E57C2); // Royal Purple
    if (cat.contains('park')) return const Color(0xFF43A047); // Lush Green
    if (cat.contains('shopping')) return const Color(0xFFEC407A); // Chic Pink
    if (cat.contains('landmark')) return const Color(0xFF00ACC1); // Sky Teal
    if (cat.contains('arts')) return const Color(0xFFFFB300); // Golden Ochre
    if (cat.contains('entertainment')) return const Color(0xFFE53935); // Velvet Red
    if (cat.contains('hotel')) return const Color(0xFF546E7A); // Slate Blue
    if (cat.contains('wellness')) return const Color(0xFF26A69A); // Mint Green
    
    return AppColors.orange;
  }

  @override
  bool shouldRepaint(covariant EmojiMarkerPainter oldDelegate) {
    return oldDelegate.pulseValue != pulseValue ||
           oldDelegate.appearanceValue != appearanceValue ||
           oldDelegate.dataPoints != dataPoints ||
           oldDelegate.camera != camera ||
           oldDelegate.highlightedPoint != highlightedPoint ||
           oldDelegate.insightOpacity != insightOpacity;
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
