import 'dart:ui' as ui;
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../../theme/plandit_design_system.dart';
import '../../api_service.dart';
import 'vibe_tuner.dart';
import 'package:url_launcher/url_launcher.dart';
import 'storyboard_models.dart';
import 'itinerary_map_view.dart';

class PlanditStoryboardView extends StatefulWidget {
  final String query;
  final Map<String, dynamic>? itineraryData;
  final VoidCallback onClose;

  const PlanditStoryboardView({
    super.key,
    required this.query,
    this.itineraryData,
    required this.onClose,
  });

  @override
  State<PlanditStoryboardView> createState() => _PlanditStoryboardViewState();
}

class _PlanditStoryboardViewState extends State<PlanditStoryboardView>
    with TickerProviderStateMixin {
  bool isVisible = false;
  bool contentVisible = false;
  int activeChapter = 0;
  bool showNarrative = false;
  double vibeLevel = 50;
  VibeMode vibeMode = VibeMode.energy;
  bool isFlipping = false;
  double parallaxOffset = 0;
  
  Set<String> lovedPlaceIds = {};
  Set<String> dislikedPlaceIds = {};
  Map<String, String> _userTips = {};
  final ApiService _apiService = ApiService();
  bool _showMapHint = false;

  late ScrollController scrollController;
  late AnimationController fadeController;
  late AnimationController flipController;

  late List<GlobalKey> chapterKeys;
  late List<Chapter> chapters;

  @override
  void initState() {
    super.initState();
    
    // Initialize chapters first
    chapters = _getChapters();
    
    // Generate keys based on actual chapter count
    chapterKeys = List.generate(chapters.length, (_) => GlobalKey());
    
    scrollController = ScrollController()..addListener(_onScroll);
    fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    flipController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );

    _loadUserPreferences();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      setState(() => isVisible = true);
      Future.delayed(const Duration(milliseconds: 600), () {
        if (mounted) setState(() => contentVisible = true);
      });
    });
  }

  @override
  void dispose() {
    scrollController.dispose();
    fadeController.dispose();
    flipController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!mounted) return;
    
    setState(() {
      parallaxOffset = scrollController.offset;
    });

    // Improved detection: Find the chapter closest to the vertical center of the screen
    double minDistance = double.infinity;
    int closestChapter = activeChapter;
    
    // Check if context is valid before using MediaQuery
    final mediaQuery = MediaQuery.maybeOf(context);
    if (mediaQuery == null) return;
    
    final screenCenter = mediaQuery.size.height / 2;

    for (int i = 0; i < chapterKeys.length; i++) {
      final key = chapterKeys[i];
      final context = key.currentContext;
      if (context != null) {
        final box = context.findRenderObject() as RenderBox?;
        if (box != null) {
          final position = box.localToGlobal(Offset.zero);
          // Calculate distance from center of this chapter to center of screen
          final chapterCenter = position.dy + box.size.height / 2;
          final distance = (chapterCenter - screenCenter).abs();
          
          if (distance < minDistance) {
            minDistance = distance;
            closestChapter = i;
          }
        }
      }
    }

    if (closestChapter != activeChapter) {
      setState(() => activeChapter = closestChapter);
    }
  }

  void _handleVibeChange(double newLevel) async {
    final oldKey = _getVariantKey(vibeLevel);
    final newKey = _getVariantKey(newLevel);

    // Update immediately for smooth slider movement - check mounted for safety
    if (mounted) {
      setState(() {
        vibeLevel = newLevel;
      });
    }

    // Only flip if variant actually changed
    if (oldKey != newKey) {
      if (mounted) setState(() => isFlipping = true);
      await flipController.forward(from: 0);
      if (mounted) {
        setState(() {
          isFlipping = false;
        });
      }
    }
  }

  void _handleModeToggle() async {
    if (!mounted) return;
    setState(() => isFlipping = true);
    await flipController.forward(from: 0);
    if (mounted) {
      setState(() {
        vibeMode = vibeMode == VibeMode.energy ? VibeMode.budget : VibeMode.energy;
        isFlipping = false;
      });
    }
  }

  String _getVariantKey(double level) {
    if (level < 35) return 'chill';
    if (level < 65) return 'balanced';
    return 'hype';
  }

  VenueVariant _getVenue(Chapter chapter) {
    final key = _getVariantKey(vibeLevel);
    return vibeMode == VibeMode.energy
        ? chapter.variants[key]!
        : chapter.budgetVariants[key]!;
  }

  String _generateTitle(String query) {
    final q = query.toLowerCase();
    if (q.contains('romantic') || q.contains('date')) return 'A Night of Romance';
    if (q.contains('coffee') || q.contains('morning')) return 'The Morning Ritual';
    if (q.contains('brunch')) return 'The Art of Brunch';
    if (q.contains('chelsea')) return 'A Chelsea Romance';
    return 'Your Curated Journey';
  }

  String _generateHook(String query) {
    final q = query.toLowerCase();
    if (q.contains('romantic') || q.contains('date')) {
      return 'Start your evening away from the crowds, where the jazz is soft and the lighting is low...';
    }
    if (q.contains('coffee') || q.contains('morning')) {
      return 'Begin before the city wakes, when the espresso is freshest and the streets are yours...';
    }
    return 'An experience curated just for you, designed to unfold like the best stories do...';
  }

  void _triggerMapHint() {
    Future.delayed(const Duration(milliseconds: 800), () {
      if (!mounted) return;
      setState(() => _showMapHint = true);
      // Fade out after 10 seconds
      Future.delayed(const Duration(seconds: 10), () {
        if (mounted) setState(() => _showMapHint = false);
      });
    });
  }

  Future<void> _handleRegenerate({double? lat, double? lng}) async {
    // Show loading overlay
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: PlanditColors.card,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: PlanditColors.border.withOpacity(0.2)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(
                width: 40,
                height: 40,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  valueColor: AlwaysStoppedAnimation<Color>(PlanditColors.accent),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                lat != null ? 'Exploring this area...' : 'Finding new spots...',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: PlanditColors.foreground,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                lat != null ? 'Mapping out a local journey' : 'Same vibe, different places',
                style: TextStyle(
                  fontSize: 12,
                  color: PlanditColors.mutedForeground,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );

    try {
      final List<String> currentPlaceIds = [];
      for (var chapter in chapters) {
        for (var variant in chapter.variants.values) {
          if (variant.placeId != null) currentPlaceIds.add(variant.placeId!);
        }
      }

      final apiService = ApiService();
      // Fetch main itinerary
      final result = await apiService.generateItineraryFromQuery(
        widget.query,
        excludePlaceIds: currentPlaceIds,
        filters: {
          'latitude': lat,
          'longitude': lng,
        },
      );
      
      // Fetch Instagram worthy places from Lemon8 and inject them
      try {
        final instagramPlaces = await apiService.getInstagramWorthyPlaces(limit: 2);
        if (instagramPlaces.isNotEmpty && result != null && result['itinerary'] is List) {
          final itineraryList = List<Map<String, dynamic>>.from(result['itinerary']);
          itineraryList.addAll(instagramPlaces);
          result['itinerary'] = itineraryList;
        }
      } catch (e) {
        print('DEBUG: Non-fatal error fetching Lemon8 places: $e');
      }
      
      if (mounted) Navigator.of(context).pop();
      
      if (mounted && result != null) {
        final newChapters = _parseApiChapters(result);
        setState(() {
          chapters = newChapters;
          chapterKeys = List.generate(newChapters.length, (_) => GlobalKey());
        });
        
        if (scrollController.hasClients) {
          scrollController.jumpTo(0);
        }
        setState(() {
          parallaxOffset = 0;
        });
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(lat != null ? '✨ New area explored!' : '✨ New itinerary generated!'),
            backgroundColor: const Color(0xFFF5DEB3),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) Navigator.of(context).pop();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to regenerate: ${e.toString()}'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Future<void> _launchMaps(double lat, double lng, String label) async {
    final query = Uri.encodeComponent(label);
    final googleMapsUrl = 'https://www.google.com/maps/search/?api=1&query=$query';
    final appleMapsUrl = 'https://maps.apple.com/?q=$query';
    final geoUrl = 'geo:0,0?q=$query';

    try {
      // Try Google Maps first (Universal)
      await launchUrl(Uri.parse(googleMapsUrl), mode: LaunchMode.externalApplication);
    } catch (e) {
      try {
        // Try Apple Maps for iOS
        await launchUrl(Uri.parse(appleMapsUrl), mode: LaunchMode.externalApplication);
      } catch (e2) {
        try {
          // Fallback to Native Android Geo intent
          await launchUrl(Uri.parse(geoUrl));
        } catch (e3) {
          debugPrint("Could not launch maps: $e3");
        }
      }
    }
  }

  Future<void> _loadUserPreferences() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final lovedList = await _apiService.getLovedPlaces(user.uid);
    final dislikedList = await _apiService.getDislikedPlaceIds(user.uid);

    if (mounted) {
      setState(() {
        lovedPlaceIds = lovedList.map((e) => e['place_id'].toString()).toSet();
        dislikedPlaceIds = dislikedList.toSet();
      });
    }
  }

  Future<void> _toggleLove(VenueVariant venue) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please sign in to save places')));
      return;
    }

    final isLoved = lovedPlaceIds.contains(venue.placeId);
    bool success;
    if (isLoved) {
      success = await _apiService.unlovePlace(user.uid, venue.placeId!);
      if (success) setState(() => lovedPlaceIds.remove(venue.placeId));
    } else {
      success = await _apiService.lovePlace(
        userId: user.uid,
        placeId: venue.placeId!,
        name: venue.venue,
        rating: venue.rating,
        lat: venue.lat,
        lng: venue.lng,
      );
      if (success) setState(() => lovedPlaceIds.add(venue.placeId!));
    }

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(isLoved ? 'Removed from saved' : 'Saved to your loved places'),
          duration: const Duration(seconds: 1),
        ),
      );
    }
  }

  Future<void> _handleDislike(VenueVariant venue) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final success = await _apiService.dislikePlace(user.uid, venue.placeId!, venue.venue);
    if (success && mounted) {
      setState(() => dislikedPlaceIds.add(venue.placeId!));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Got it, we won\'t show you this place again.')),
      );
      // Optional: Regenerate or hide this venue in UI
    }
  }

  Future<void> _uploadPhoto(VenueVariant venue) async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 70);
    
    if (image == null) return;

    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Uploading photo...')));

    final fileName = 'user_${user.uid}_${venue.placeId}_${DateTime.now().millisecondsSinceEpoch}.jpg';
    final url = await _apiService.uploadImageToSupabase(fileName, File(image.path));

    if (url != null) {
      await _apiService.recordPlaceImage(user.uid, venue.placeId!, url);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Photo uploaded successfully! ✨')));
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Failed to upload photo.')));
      }
    }
  }

  Future<void> _submitTip(String placeId, String tip) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    
    if (tip.trim().isEmpty) return;

    final success = await _apiService.submitUserTip(user.uid, placeId, tip);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Thanks for your tip! It\'s been saved. ✨')));
    }
  }

  Widget _buildInteractionButton({
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
    required String label,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 2),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 8,
                fontWeight: FontWeight.w700,
                color: color,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _calculateTotalDuration() {
    // Rough estimate: 1-1.5 hours per stop
    final hours = (chapters.length * 1.25).round();
    return hours.toString();
  }

  @override
  Widget build(BuildContext context) {
    final title = _generateTitle(widget.query);
    final hook = _generateHook(widget.query);

    return AnimatedOpacity(
      opacity: isVisible ? 1.0 : 0.0,
      duration: const Duration(milliseconds: 700),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Stack(
          children: [
            // Floating Background Context (Dark & Blurred)
            Positioned.fill(
              child: Container(
                color: Colors.black.withOpacity(0.4),
                child: BackdropFilter(
                  filter: ColorFilter.mode(
                    Colors.black.withOpacity(0.2),
                    BlendMode.darken,
                  ),
                    child: BackdropFilter(
                      filter: ui.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                      child: Container(color: Colors.transparent),
                    ),
                ),
              ),
            ),

            // The Main Modal Surface
            Positioned.fill(
              child: AnimatedPadding(
                duration: const Duration(milliseconds: 800),
                curve: Curves.easeOutCubic,
                padding: EdgeInsets.only(top: contentVisible ? 60 : MediaQuery.of(context).size.height),
                child: Container(
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
                  ),
                  child: Stack(
                    children: [
                      // Header Navigation
                      Positioned(
                        top: 24,
                        left: 24,
                        right: 24,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  "CURATED FOR YOU",
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    letterSpacing: 2,
                                    fontWeight: FontWeight.w600,
                                    color: PlanditColors.secondaryText,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  "19:00 PM",
                                  style: GoogleFonts.inter(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w500,
                                    color: PlanditColors.primaryText,
                                  ),
                                ),
                              ],
                            ),
                            GestureDetector(
                              onTap: widget.onClose,
                              child: const Icon(Icons.close, color: PlanditColors.primaryText),
                            ),
                          ],
                        ),
                      ),

                      // Content
                      Padding(
                        padding: const EdgeInsets.only(top: 100),
                        child: !showNarrative ? 
                        // Hero Section
                        SingleChildScrollView(
                          padding: const EdgeInsets.symmetric(horizontal: 24),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                title,
                                style: GoogleFonts.playfairDisplay(
                                  fontSize: 48,
                                  fontWeight: FontWeight.w400,
                                  color: PlanditColors.primaryText,
                                  height: 1.1,
                                ),
                              ),
                              const SizedBox(height: 24),
                              Text(
                                hook,
                                style: GoogleFonts.playfairDisplay(
                                  fontSize: 18,
                                  fontStyle: FontStyle.italic,
                                  color: PlanditColors.secondaryText,
                                  height: 1.5,
                                ),
                              ),
                              const SizedBox(height: 48),
                              SizedBox(
                                width: double.infinity,
                                child: TextButton(
                                  onPressed: () {
                                    setState(() => showNarrative = true);
                                    _triggerMapHint();
                                  },
                                  style: TextButton.styleFrom(
                                    backgroundColor: PlanditColors.primaryText,
                                    padding: const EdgeInsets.symmetric(vertical: 20),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                  ),
                                  child: Text(
                                    "BEGIN THE JOURNEY",
                                    style: GoogleFonts.inter(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w600,
                                      letterSpacing: 1.5,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )
                        :
                        SingleChildScrollView(
                          controller: scrollController,
                          child: Column(
                            children: [
                              // Map Header (40% of screen)
                              SizedBox(
                                height: MediaQuery.of(context).size.height * 0.4,
                                child: Stack(
                                  children: [
                                    // Map with white wash overlay
                                    ItineraryMapView(
                                      chapters: chapters,
                                      isHeader: true,
                                      onLocationSelected: (point) {
                                        _handleRegenerate(lat: point.latitude, lng: point.longitude);
                                      },
                                    ),
                                    // White wash overlay for minimalist look - ignore pointers to allow map interaction
                                    IgnorePointer(
                                      child: Container(
                                        decoration: BoxDecoration(
                                          gradient: LinearGradient(
                                            begin: Alignment.topCenter,
                                            end: Alignment.bottomCenter,
                                            colors: [
                                              Colors.white.withOpacity(0.4),
                                              Colors.white.withOpacity(0.3),
                                              Colors.white.withOpacity(0.2),
                                              Colors.transparent,
                                            ],
                                            stops: const [0.0, 0.3, 0.7, 1.0],
                                          ),
                                        ),
                                      ),
                                    ),
                                    // Subtle bottom fade to content - ignore pointers to allow map interaction
                                    Positioned(
                                      bottom: 0,
                                      left: 0,
                                      right: 0,
                                      child: IgnorePointer(
                                        child: Container(
                                          height: 60,
                                          decoration: BoxDecoration(
                                            gradient: LinearGradient(
                                              begin: Alignment.topCenter,
                                              end: Alignment.bottomCenter,
                                              colors: [
                                                Colors.transparent,
                                                PlanditColors.background.withOpacity(0.9),
                                                PlanditColors.background,
                                              ],
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                    // Discovery Hint Overlay
                                    Positioned(
                                      top: 40,
                                      right: 24,
                                      child: AnimatedOpacity(
                                        opacity: _showMapHint ? 1.0 : 0.0,
                                        duration: const Duration(seconds: 2),
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                          decoration: BoxDecoration(
                                            color: Colors.white.withOpacity(0.9),
                                            borderRadius: BorderRadius.circular(12),
                                            border: Border.all(color: PlanditColors.border.withOpacity(0.1)),
                                            boxShadow: [
                                              BoxShadow(
                                                color: Colors.black.withOpacity(0.05),
                                                blurRadius: 10,
                                                offset: const Offset(0, 4),
                                              ),
                                            ],
                                          ),
                                          child: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              Icon(Icons.touch_app_outlined, size: 14, color: PlanditColors.accent),
                                              const SizedBox(width: 8),
                                              Text(
                                                "Long press map to explore elsewhere",
                                                style: GoogleFonts.inter(
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.w600,
                                                  color: PlanditColors.primaryText,
                                                  letterSpacing: 0.2,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    ),
                                    // Itinerary title overlay
                                    Positioned(
                                      top: 40,
                                      left: 24,
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                            decoration: BoxDecoration(
                                              color: Colors.white.withOpacity(0.9),
                                              borderRadius: BorderRadius.circular(100),
                                              border: Border.all(
                                                color: PlanditColors.border.withOpacity(0.3),
                                              ),
                                              boxShadow: [
                                                BoxShadow(
                                                  color: Colors.black.withOpacity(0.05),
                                                  blurRadius: 8,
                                                  offset: const Offset(0, 2),
                                                ),
                                              ],
                                            ),
                                            child: Text(
                                              '${chapters.length} stops • ${_calculateTotalDuration()} hrs',
                                              style: GoogleFonts.inter(
                                                fontSize: 11,
                                                fontWeight: FontWeight.w600,
                                                color: PlanditColors.mutedForeground,
                                                letterSpacing: 0.5,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              
                              // Chapter list
                              ...List.generate(chapters.length, (index) {
                                return _buildChapter(chapters[index], index);
                              }),
                              
                              const SizedBox(height: 60),
                              // Regenerate
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 24),
                                child: TextButton(
                                  onPressed: _handleRegenerate,
                                  child: Text(
                                    "REGENERATE ITINERARY",
                                    style: GoogleFonts.inter(
                                      color: PlanditColors.secondaryText,
                                      fontWeight: FontWeight.w600,
                                      letterSpacing: 1,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 160),
                            ],
                          ),
                        ),
                      ),

                      // Vibe Slider Bar
                      if (showNarrative)
                        VibeTuner(
                          vibeLevel: vibeLevel,
                          onVibeChange: _handleVibeChange,
                          mode: vibeMode,
                          onModeToggle: _handleModeToggle,
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChapter(Chapter chapter, int index) {
    final venue = _getVenue(chapter);

    return Container(
      key: chapterKeys[index],
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline Vertical Line Step
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // The Slender Timeline
              Column(
                children: [
                  Container(
                    width: 1,
                    height: 40,
                    color: PlanditColors.border,
                  ),
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: PlanditColors.primaryText,
                      shape: BoxShape.circle,
                    ),
                  ),
                  Container(
                    width: 1,
                    height: 200, // Dynamic height placeholder
                    color: PlanditColors.border,
                  ),
                ],
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 32),
                    Text(
                      chapter.time,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: PlanditColors.secondaryText,
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // The Card
                    _buildVenueCard(venue, chapter),
                    
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildVenueCard(VenueVariant venue, Chapter chapter) {
    if (dislikedPlaceIds.contains(venue.placeId)) {
      return Container(); // Hide disliked spots
    }
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: PlanditColors.shadowSoft,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Content Padding
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            venue.venueType.toUpperCase(),
                            style: GoogleFonts.inter(
                              fontSize: 10,
                              letterSpacing: 1.5,
                              fontWeight: FontWeight.w600,
                              color: PlanditColors.secondaryText,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            venue.venue,
                            style: GoogleFonts.playfairDisplay(
                              fontSize: 24,
                              fontWeight: FontWeight.w400,
                              color: PlanditColors.primaryText,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Rating
                    Row(
                      children: [
                        const Icon(Icons.star, size: 14, color: PlanditColors.accentGold),
                        const SizedBox(width: 4),
                        Text(
                          venue.rating.toString(),
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: PlanditColors.primaryText,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                
                // Love & Dislike Action Row
                Row(
                  children: [
                    _buildInteractionButton(
                      icon: lovedPlaceIds.contains(venue.placeId) ? Icons.favorite : Icons.favorite_border,
                      color: lovedPlaceIds.contains(venue.placeId) ? Colors.orange : PlanditColors.secondaryText,
                      onTap: () => _toggleLove(venue),
                      label: "SAVE",
                    ),
                    const SizedBox(width: 16),
                    _buildInteractionButton(
                      icon: Icons.thumb_down_outlined,
                      color: dislikedPlaceIds.contains(venue.placeId) ? Colors.red : PlanditColors.secondaryText,
                      onTap: () => _handleDislike(venue),
                      label: "DISLIKE",
                    ),
                    const Spacer(),
                    _buildInteractionButton(
                      icon: Icons.add_photo_alternate_outlined,
                      color: PlanditColors.secondaryText,
                      onTap: () => _uploadPhoto(venue),
                      label: "ADD PHOTO",
                    ),
                  ],
                ),

                const SizedBox(height: 16),
                Text(
                  venue.description,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: PlanditColors.primaryText.withOpacity(0.8),
                    height: 1.6,
                  ),
                ),
                const SizedBox(height: 16),

                // Maps Button
                if (venue.lat != null && venue.lng != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: InkWell(
                      onTap: () => _launchMaps(venue.lat!, venue.lng!, venue.venue),
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: PlanditColors.primaryText.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: PlanditColors.primaryText.withOpacity(0.1)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.map_outlined, size: 16, color: PlanditColors.primaryText),
                            const SizedBox(width: 8),
                            Text(
                              "VIEW ON MAPS",
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1,
                                color: PlanditColors.primaryText,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                // Tags
                if (venue.insiderProfile != null && venue.insiderProfile!['vibe_tags'] != null)
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: (venue.insiderProfile!['vibe_tags'] as List).map((tag) {
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: PlanditColors.tagFill,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          tag.toString(),
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: PlanditColors.secondaryText,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
              ],
            ),
          ),

          // Curator Tip Section (Beige Background)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            color: PlanditColors.curatorBackground,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Curator Tip (Only if present)
                if (venue.insiderProfile?['insider_tidbit'] != null && (venue.insiderProfile?['insider_tidbit'] as String).isNotEmpty) ...[
                  Row(
                    children: [
                      const Icon(Icons.auto_awesome, size: 14, color: PlanditColors.accentGold),
                      const SizedBox(width: 8),
                      Text(
                        "CURATOR TIP",
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          letterSpacing: 1.5,
                          fontWeight: FontWeight.w700,
                          color: PlanditColors.accentGold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    venue.insiderProfile?['insider_tidbit'],
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontStyle: FontStyle.italic,
                      color: PlanditColors.primaryText.withOpacity(0.7),
                      height: 1.5,
                    ),
                  ),
                ],

                // User Tip Contribution (if missing insider tidbit)
                if (venue.insiderProfile?['insider_tidbit'] == null || (venue.insiderProfile?['insider_tidbit'] as String).isEmpty) ...[
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.5),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: PlanditColors.accentGold.withOpacity(0.1)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "KNOW THIS SPOT?",
                          style: GoogleFonts.inter(
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1,
                            color: PlanditColors.accentGold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          style: GoogleFonts.inter(fontSize: 12),
                          decoration: InputDecoration(
                            hintText: "Add your secret tip or must-order item...",
                            hintStyle: GoogleFonts.inter(fontSize: 12, color: PlanditColors.secondaryText.withOpacity(0.5)),
                            border: InputBorder.none,
                            isDense: true,
                          ),
                          maxLines: 2,
                          onChanged: (value) {
                            setState(() {
                              if (venue.placeId != null) {
                                _userTips[venue.placeId!] = value;
                              }
                            });
                          },
                          onSubmitted: (value) {
                            if (value.trim().isNotEmpty) {
                              _submitTip(venue.placeId!, value);
                              setState(() {
                                _userTips[venue.placeId!] = "";
                              });
                            }
                          },
                        ),
                        if (venue.placeId != null && (_userTips[venue.placeId] ?? "").trim().isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Align(
                            alignment: Alignment.centerRight,
                            child: InkWell(
                              onTap: () {
                                final tip = _userTips[venue.placeId]!;
                                _submitTip(venue.placeId!, tip);
                                setState(() {
                                  _userTips[venue.placeId!] = "";
                                });
                                FocusScope.of(context).unfocus();
                              },
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                decoration: BoxDecoration(
                                  color: PlanditColors.accentGold,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  "SUBMIT TIP",
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    color: Colors.white,
                                    letterSpacing: 0.5,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],

                // Must Order
                if (venue.insiderProfile != null && venue.insiderProfile!['must_order'] != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    "MUST ORDER",
                    style: GoogleFonts.inter(
                      fontSize: 9,
                      letterSpacing: 1,
                      fontWeight: FontWeight.w800,
                      color: PlanditColors.primaryText.withOpacity(0.4),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    (venue.insiderProfile!['must_order'] as List).join(", "),
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: PlanditColors.primaryText.withOpacity(0.8),
                    ),
                  ),
                ],

                // Footer context: Occasion & Warning
                if ((venue.insiderProfile?['ideal_occasion'] != null) || (venue.insiderProfile?['warning_label'] != null)) ...[
                  const SizedBox(height: 20),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (venue.insiderProfile?['ideal_occasion'] != null)
                        Row(
                          children: [
                            Icon(Icons.event_seat_outlined, size: 12, color: PlanditColors.primaryText.withOpacity(0.4)),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                venue.insiderProfile!['ideal_occasion'],
                                style: GoogleFonts.inter(
                                  fontSize: 11,
                                  color: PlanditColors.primaryText.withOpacity(0.5),
                                ),
                              ),
                            ),
                          ],
                        ),
                      if (venue.insiderProfile?['warning_label'] != null) ...[
                        if (venue.insiderProfile?['ideal_occasion'] != null) const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.red.withOpacity(0.05),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.warning_amber_rounded, size: 12, color: Colors.redAccent),
                              const SizedBox(width: 8),
                              Flexible(
                                child: Text(
                                  venue.insiderProfile!['warning_label'].toString().toUpperCase(),
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    color: Colors.redAccent,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInsiderProfile(Map<String, dynamic> profile) {
    final vibeTags = (profile['vibe_tags'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final mustOrder = (profile['must_order'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final tidbit = profile['insider_tidbit']?.toString();
    final warning = profile['warning_label']?.toString();
    final occasion = profile['ideal_occasion']?.toString();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.03),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.black.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Vibe Tags
          if (vibeTags.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: vibeTags.map((tag) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: PlanditColors.accent.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(100),
                    border: Border.all(color: PlanditColors.accent.withOpacity(0.2)),
                  ),
                  child: Text(
                    tag,
                    style: const TextStyle(
                      fontSize: 10,
                      color: PlanditColors.accent,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                )).toList(),
              ),
            ),

          // Must Order Section
          if (mustOrder.isNotEmpty) ...[
            Row(
              children: [
                const Icon(Icons.restaurant_menu, size: 14, color: PlanditColors.accent),
                const SizedBox(width: 8),
                Text(
                  "MUST ORDER",
                  style: TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.2,
                    fontWeight: FontWeight.w700,
                    color: Colors.black.withOpacity(0.8),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...mustOrder.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 4, left: 22),
              child: Text(
                "• $item",
                style: const TextStyle(fontSize: 13, color: Colors.black54),
              ),
            )),
            const SizedBox(height: 16),
          ],

          // Insider Tidbit
          if (tidbit != null && tidbit.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.04),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 3,
                    height: 24,
                    decoration: BoxDecoration(
                      color: PlanditColors.accent,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Icon(Icons.lightbulb_outline, size: 16, color: PlanditColors.accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      tidbit,
                      style: const TextStyle(
                        fontSize: 13,
                        fontStyle: FontStyle.italic,
                        color: Colors.black87,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Footer info: Warning & Occasion
          Row(
            children: [
              if (occasion != null && occasion.isNotEmpty) ...[
                const Icon(Icons.auto_awesome, size: 12, color: Colors.black38),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    occasion,
                    style: const TextStyle(fontSize: 11, color: Colors.black38),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
              if (warning != null && warning.isNotEmpty) ...[
                if (occasion != null && occasion.isNotEmpty) const SizedBox(width: 12),
                Flexible(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.red.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.warning_amber_rounded, size: 10, color: Colors.redAccent),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            warning.toUpperCase(),
                            style: const TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              color: Colors.redAccent,
                            ),
                            maxLines: 1,
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
        ],
      ),
    );
  }

  List<Chapter> _getChapters() {
    // If we have API data, parse it
    if (widget.itineraryData != null) {
      return _parseApiChapters(widget.itineraryData!);
    }
    
    // Otherwise, fall back to hardcoded data
    return _getHardcodedChapters();
  }

  List<Chapter> _parseApiChapters(Map<String, dynamic> data) {
    print('DEBUG: _parseApiChapters called');
    print('DEBUG: Data keys: ${data.keys}');
    
    final itinerary = data['itinerary'] as List<dynamic>? ?? [];
    print('DEBUG: Itinerary length: ${itinerary.length}');
    
    if (itinerary.isEmpty) {
      print('DEBUG: Itinerary is empty, using hardcoded chapters');
      return _getHardcodedChapters();
    }

    // Group venues by slot (1-5)
    final chapters = <Chapter>[];
    
    for (int i = 0; i < itinerary.length && i < 8; i++) {
      final venue = itinerary[i] as Map<String, dynamic>;
      final bool isLemon8 = venue['is_lemon8'] ?? false;
      
      print('DEBUG: Processing venue $i: ${venue['name']} (isLemon8: $isLemon8)');
      
      final slot = venue['slot'] ?? (i + 1);
      
      // Create a single variant from the API data
      final variant = VenueVariant.fromJson(venue);
      
      // Determine chapter type and icon
      final category = (venue['category'] ?? 'Dining').toString().toLowerCase();
      IconData icon = Icons.restaurant_outlined;
      String title = isLemon8 ? 'Instagram Discovery' : 'Stop ${slot}';
      
      if (isLemon8) {
        icon = Icons.auto_awesome;
      } else if (category.contains('drink') || category.contains('bar') || category.contains('coffee')) {
        icon = Icons.local_bar_outlined;
        title = 'The Drink';
      } else if (category.contains('walk') || category.contains('activity')) {
        icon = Icons.directions_walk;
        title = 'The Walk';
      } else if (category.contains('dining') || category.contains('restaurant')) {
        icon = Icons.restaurant_outlined;
        title = 'The Dinner';
      }
      
      // Use venue image or fallback to Unsplash
      final image = venue['image_url'] ?? _getDefaultImage(category);
      
      // Calculate time (rough estimate)
      final baseTime = DateTime(2024, 1, 1, 17, 0); // Start at 5 PM
      final time = baseTime.add(Duration(hours: i * 2));
      final timeStr = '${time.hour}:${time.minute.toString().padLeft(2, '0')} ${time.hour >= 12 ? 'PM' : 'AM'}';
      
      chapters.add(Chapter(
        id: isLemon8 ? 'lemon8_$i' : 'slot_$slot',
        time: timeStr,
        title: title,
        icon: icon,
        image: image,
        duration: '1-2h',
        variants: {
          'chill': variant,
          'balanced': variant,
          'hype': variant,
        },
        budgetVariants: {
          'chill': variant,
          'balanced': variant,
          'hype': variant,
        },
      ));
    }
    
    print('DEBUG: Created ${chapters.length} chapters from API data');
    return chapters.isNotEmpty ? chapters : _getHardcodedChapters();
  }

  String _getDefaultImage(String category) {
    if (category.contains('drink') || category.contains('bar')) {
      return 'https://images.unsplash.com/photo-1534430480872-3498386e7856?w=1920&h=1080&fit=crop&q=95';
    } else if (category.contains('walk')) {
      return 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1920&h=1080&fit=crop&q=95';
    } else {
      return 'https://images.unsplash.com/photo-1555992336-03a23c7b20ee?w=1920&h=1080&fit=crop&q=95';
    }
  }

  List<Chapter> _getHardcodedChapters() {
    return [
      Chapter(
        id: 'drink',
        time: '5:00 PM',
        title: 'The Drink',
        icon: Icons.local_bar_outlined,
        image: 'https://images.unsplash.com/photo-1534430480872-3498386e7856?w=1920&h=1080&fit=crop&q=95',
        duration: '1h 30m',
        variants: {
          'chill': VenueVariant(
            venue: 'Sey Coffee',
            venueType: 'Third Wave Coffee',
            description: 'A quiet corner with pour-overs and ambient music. The kind of place where conversations flow naturally.',
            aiNote: 'Selected for its calm atmosphere — perfect for easing into the evening.',
            rating: 4.7,
            price: '\$',
          ),
          'balanced': VenueVariant(
            venue: 'Raines Law Room',
            venueType: 'Speakeasy',
            description: 'Ring the bell and step into a different era. Velvet couches, candlelit corners, and cocktails that tell stories.',
            aiNote: 'Added because you mentioned \'romantic\' — this spot has the city\'s most intimate lighting.',
            rating: 4.8,
            price: '\$\$',
          ),
          'hype': VenueVariant(
            venue: 'The Flatiron Room',
            venueType: 'Whiskey Bar',
            description: 'Live jazz, 1000+ whiskeys, and an energy that pulses through the room. Dress sharp.',
            aiNote: 'For when you want to feel the city\'s heartbeat — this place brings the energy.',
            rating: 4.6,
            price: '\$\$\$',
          ),
        },
        budgetVariants: {
          'chill': VenueVariant(
            venue: 'Nowadays',
            venueType: 'Outdoor Bar',
            description: 'Cheap beers, picnic tables, and a backyard vibe in the middle of the city.',
            aiNote: 'Best value drinks with an unpretentious crowd — your wallet will thank you.',
            rating: 4.4,
            price: '\$',
          ),
          'balanced': VenueVariant(
            venue: 'Raines Law Room',
            venueType: 'Speakeasy',
            description: 'Ring the bell and step into a different era. Velvet couches, candlelit corners, and cocktails that tell stories.',
            aiNote: 'Great cocktails at reasonable prices — the sweet spot.',
            rating: 4.8,
            price: '\$\$',
          ),
          'hype': VenueVariant(
            venue: 'Bemelmans Bar',
            venueType: 'Piano Bar',
            description: 'Gold leaf ceilings, live piano, and \$30 martinis that somehow feel worth it. This is old money Manhattan.',
            aiNote: 'An iconic splurge — the ambiance alone is worth the premium.',
            rating: 4.9,
            price: '\$\$\$\$',
          ),
        },
      ),
      Chapter(
        id: 'walk',
        time: '6:30 PM',
        title: 'The Walk',
        icon: Icons.directions_walk,
        image: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1920&h=1080&fit=crop&q=95',
        walkInfo: '12 min walk',
        variants: {
          'chill': VenueVariant(
            venue: 'Via Washington Square',
            venueType: 'Scenic Route',
            description: 'Stroll through the arch, past street musicians and chess players. No rush.',
            aiNote: 'A slower pace through the Village — take your time, people watch.',
            rating: 4.5,
            price: 'Free',
          ),
          'balanced': VenueVariant(
            venue: 'Via the High Line',
            venueType: 'Elevated Park',
            description: 'Catch the golden hour from above the city. The elevated park transforms at sunset.',
            aiNote: 'Routed through here for the sunset view at 6:45 PM — timing is everything.',
            rating: 4.8,
            price: 'Free',
          ),
          'hype': VenueVariant(
            venue: 'Through Times Square',
            venueType: 'Urban Energy',
            description: 'Lean into the chaos. Neon lights, crowds, and pure NYC sensory overload.',
            aiNote: 'For adrenaline seekers — embrace the madness before dinner.',
            rating: 4.2,
            price: 'Free',
          ),
        },
        budgetVariants: {
          'chill': VenueVariant(
            venue: 'Brooklyn Bridge Walk',
            venueType: 'Iconic Route',
            description: 'Free views that cost nothing but time. The skyline at sunset is priceless.',
            aiNote: 'The best things in NYC are free — this walk proves it.',
            rating: 4.9,
            price: 'Free',
          ),
          'balanced': VenueVariant(
            venue: 'Via the High Line',
            venueType: 'Elevated Park',
            description: 'Catch the golden hour from above the city. The elevated park transforms at sunset.',
            aiNote: 'Free to walk, priceless views — perfect balance.',
            rating: 4.8,
            price: 'Free',
          ),
          'hype': VenueVariant(
            venue: 'Private Pedicab Tour',
            venueType: 'Guided Experience',
            description: 'Your own guide through the city\'s secrets. Champagne optional but recommended.',
            aiNote: 'When walking is too pedestrian — arrive in style.',
            rating: 4.7,
            price: '\$\$\$',
          ),
        },
      ),
      Chapter(
        id: 'dinner',
        time: '7:00 PM',
        title: 'The Dinner',
        icon: Icons.restaurant_outlined,
        image: 'https://images.unsplash.com/photo-1555992336-03a23c7b20ee?w=1920&h=1080&fit=crop&q=95',
        duration: '2h',
        variants: {
          'chill': VenueVariant(
            venue: 'Via Carota',
            venueType: 'Italian',
            description: 'Farm-to-table simplicity. No reservations, just great pasta and candlelight.',
            aiNote: 'Relaxed and romantic — let the food speak for itself.',
            rating: 4.7,
            price: '\$\$',
          ),
          'balanced': VenueVariant(
            venue: 'Shukette',
            venueType: 'Mediterranean',
            description: 'Share plates designed for two. The lamb shoulder takes 45 minutes — but it\'s worth every second.',
            aiNote: 'Perfect for date night — shareable dishes encourage conversation and connection.',
            rating: 4.8,
            price: '\$\$\$',
          ),
          'hype': VenueVariant(
            venue: 'Carbone',
            venueType: 'Italian Fine Dining',
            description: 'The spicy rigatoni. The tableside Caesar. The scene. This is a New York moment.',
            aiNote: 'When you want to feel like a celebrity — this is the spot.',
            rating: 4.6,
            price: '\$\$\$\$',
          ),
        },
        budgetVariants: {
          'chill': VenueVariant(
            venue: 'L\'Industrie Pizzeria',
            venueType: 'Pizza',
            description: 'The best \$5 slice in the city. Crispy, cheesy, perfect. No frills, pure flavor.',
            aiNote: 'Proof that great food doesn\'t need a reservation or a dress code.',
            rating: 4.8,
            price: '\$',
          ),
          'balanced': VenueVariant(
            venue: 'Shukette',
            venueType: 'Mediterranean',
            description: 'Share plates designed for two. The lamb shoulder takes 45 minutes — but it\'s worth every second.',
            aiNote: 'Well-priced for the quality — an affordable splurge.',
            rating: 4.8,
            price: '\$\$\$',
          ),
          'hype': VenueVariant(
            venue: 'Le Bernardin',
            venueType: 'Fine Dining',
            description: 'Michelin stars, impeccable service, and seafood that redefines the category.',
            aiNote: 'For a once-in-a-lifetime dinner — this is the peak.',
            rating: 4.9,
            price: '\$\$\$\$',
          ),
        },
      ),
    ];
  }
}
