import 'dart:async';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';
import 'package:latlong2/latlong.dart';
import '../api_service.dart';

import '../widgets/density_heatmap_widget.dart';
import '../theme/plandit_design_system.dart';
import 'itinerary_detail_screen.dart';

enum DiscoveryBarFocus { address, who, vibe, map }

/// Multi-step Trip Wizard with glassmorphism, soft gradients, and editorial typography
class TripWizardScreen extends StatefulWidget {
  const TripWizardScreen({super.key});

  @override
  State<TripWizardScreen> createState() => _TripWizardScreenState();
}

class _TripWizardScreenState extends State<TripWizardScreen> with SingleTickerProviderStateMixin {
  // 1: Destination, 2: Context, 3: Vibe, 4: Loading, 5: Completion
  int _currentStep = 1;

  // User selections
  String _destination = '';
  String _currentCity = 'Chicago'; // Default fallback
  bool _isLoadingLocation = true;
  DateTime? _startDate;
  DateTime? _endDate;
  String? _selectedWho = 'Couple';
  List<String> _selectedVibes = [];
  Map<String, dynamic>? _generatedItinerary;
  final TextEditingController _destinationController = TextEditingController();
  final FocusNode _destinationFocusNode = FocusNode();
  bool _isInputFocused = false;
  bool _hasSetInitialLocation = false; // Track if we've set location once
  List<Map<String, dynamic>> _suggestions = [];
  Timer? _debounce;
  bool _isFetchingSuggestions = false;

  // Card dragging state
  double _cardHeight = 0.72; // Percentage of screen height (72%)
  late AnimationController _animationController;
  
  // ADD THIS: Track vibe state here for the filter pills
  String? _selectedVibe; 
  DiscoveryBarFocus _barFocus = DiscoveryBarFocus.address;
  LatLng? _selectedLatLng;

  // Design Constants
  final Color creamColor = const Color(0xFFF7F4EF);
  final Color darkTeal = const Color(0xFF1A3C40);
  final Color accentGreen = const Color(0xFF2C5F68);

  // Vibe options with emojis
  final List<Map<String, dynamic>> vibeOptions = [
    {'label': '🕯️ Cozy & Intimate', 'icon': Icons.favorite_border},
    {'label': '🎉 Lively & Social', 'icon': Icons.groups},
    {'label': '✨ Trendy & Modern', 'icon': Icons.auto_awesome},
    {'label': '🌿 Relaxed & Casual', 'icon': Icons.spa_outlined},
    {'label': '👑 Upscale & Elegant', 'icon': Icons.diamond_outlined},
  ];

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _detectUserLocation();
    _destinationFocusNode.addListener(() {
      setState(() {
        _isInputFocused = _destinationFocusNode.hasFocus;
      });
    });
  }

  @override
  void dispose() {
    _animationController.dispose();
    _destinationController.dispose();
    _destinationFocusNode.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _detectUserLocation() async {
    // Only set location once on initial load
    if (_hasSetInitialLocation) return;
    
    try {
      // Check permissions
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied || 
          permission == LocationPermission.deniedForever) {
        // Use default location
        setState(() {
          _currentCity = 'Chicago';
          _destinationController.text = 'Chicago';
          _isLoadingLocation = false;
          _hasSetInitialLocation = true;
        });
        return;
      }

      // Get current position
      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.low,
      );

      // Get city name from coordinates
      List<Placemark> placemarks = await placemarkFromCoordinates(
        position.latitude,
        position.longitude,
      );

      if (placemarks.isNotEmpty) {
        final city = placemarks[0].locality ?? 'Chicago';
        setState(() {
          _currentCity = city;
          _destinationController.text = city;
          _isLoadingLocation = false;
          _hasSetInitialLocation = true;
        });
      }
    } catch (e) {
      debugPrint('Error detecting location: $e');
      setState(() {
        _currentCity = 'Chicago';
        _destinationController.text = 'Chicago';
        _isLoadingLocation = false;
        _hasSetInitialLocation = true;
      });
    }
  }

  void _onDestinationChanged(String value) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      if (value.isNotEmpty) {
        _fetchSuggestions(value);
      } else {
        setState(() {
          _suggestions = [];
        });
      }
    });
  }

  Future<void> _fetchSuggestions(String query) async {
    setState(() {
      _isFetchingSuggestions = true;
    });
    
    try {
      final results = await ApiService().getAddressSuggestions(query);
      if (mounted) {
        setState(() {
          _suggestions = results;
          _isFetchingSuggestions = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isFetchingSuggestions = false;
        });
      }
    }
  }

  void _selectSuggestion(Map<String, dynamic> suggestion) {
    setState(() {
      final name = suggestion['display'];
      _destinationController.text = name;
      _suggestions = [];
      _destination = name;
      _selectedLatLng = LatLng(suggestion['lat'], suggestion['lng']);
      _barFocus = DiscoveryBarFocus.who; // Advance focus
    });
    _destinationFocusNode.unfocus();
  }

  Future<void> _handleMapPinSelection(LatLng location) async {
    HapticFeedback.mediumImpact();
    
    // Reverse geocode to get city name
    try {
      List<Placemark> placemarks = await placemarkFromCoordinates(
        location.latitude,
        location.longitude,
      );
      
      if (placemarks.isNotEmpty) {
        final place = placemarks[0];
        
        // Build a hyper-detailed street-level address
        List<String> addressParts = [];
        
        // 1. Street Number + Name
        if (place.thoroughfare != null && place.thoroughfare!.isNotEmpty) {
          String street = place.thoroughfare!;
          if (place.subThoroughfare != null && place.subThoroughfare!.isNotEmpty) {
            street = "${place.subThoroughfare} $street";
          }
          addressParts.add(street);
        }
        
        // 2. Neighborhood/Area
        if (place.subLocality != null && place.subLocality!.isNotEmpty) {
          addressParts.add(place.subLocality!);
        }
        
        // 3. City
        if (place.locality != null && place.locality!.isNotEmpty) {
          addressParts.add(place.locality!);
        }

        final name = addressParts.isEmpty 
            ? (place.name ?? "Selected Location") 
            : addressParts.join(", ");

        setState(() {
          _destinationController.text = name;
          _destination = name;
          _selectedLatLng = location; // Store for the pin
          _barFocus = DiscoveryBarFocus.who;
        });
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Location set to $name"),
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 2),
            margin: EdgeInsets.only(bottom: MediaQuery.of(context).size.height * 0.4),
            backgroundColor: const Color(0xFFE91E63).withOpacity(0.9),
          ),
        );
      }
    } catch (e) {
      debugPrint("Error reverse geocoding: $e");
    }
  }

  void _nextStep() {
    setState(() {
      // Skip step 2 (Context) since it's now combined with step 1
      if (_currentStep == 1) {
        _currentStep = 3; // Jump to Vibe step
      } else if (_currentStep < 5) {
        _currentStep++;
      }
    });
  }

  void _previousStep() {
    setState(() {
      // Skip step 2 when going back
      if (_currentStep == 3) {
        _currentStep = 1; // Jump back to Destination+Who step
      } else if (_currentStep > 1) {
        _currentStep--;
      }
    });
  }

  void _toggleVibe(String vibe) {
    setState(() {
      if (_selectedVibes.contains(vibe)) {
        _selectedVibes.remove(vibe);
      } else if (_selectedVibes.length < 3) {
        _selectedVibes.add(vibe);
      }
    });
  }

  // Trigger the loading sequence and create trip
  Future<void> _startGeneration() async {
    // Unfocus keyboard before transitioning to prevent deactivation errors
    FocusScope.of(context).unfocus();
    
    setState(() => _currentStep = 4); // Loading state

    _destination = _destinationController.text.trim();
    if (_destination.isEmpty) _destination = 'Chicago';

    try {
      final apiService = ApiService();
      
      // Strip emojis from vibes for API (backend expects clean strings)
      final cleanVibes = _selectedVibes.map((vibe) {
        // Remove emoji prefix (first word/emoji) and trim
        final parts = vibe.split(' ');
        if (parts.length > 1) {
          return parts.sublist(1).join(' ');
        }
        return vibe;
      }).toList();
      
      // Fetch itinerary and Instagram spots in parallel
      final results = await Future.wait([
        apiService.createItinerarySkeleton(
          destination: _destination,
          startDate: _startDate ?? DateTime.now(),
          endDate: _endDate ?? DateTime.now().add(const Duration(days: 3)),
          groupSize: _selectedWho ?? 'Couple',
          vibes: cleanVibes.isNotEmpty ? cleanVibes : ['Relaxed & Casual'],
        ),
        // Fetch Instagram spots using the selected location
        if (_selectedLatLng != null)
          apiService.getInstagramWorthyPlaces(
            lat: _selectedLatLng!.latitude,
            lng: _selectedLatLng!.longitude,
            radiusMeters: 3000,
            limit: 2,
          )
        else
          Future.value(<Map<String, dynamic>>[]),
      ]);

      final itineraryResult = results[0] as Map<String, dynamic>;
      final instagramPlaces = results[1] as List<Map<String, dynamic>>;

      // Merge Instagram places into the itinerary
      if (instagramPlaces.isNotEmpty && itineraryResult.containsKey('itinerary')) {
        final itineraryList = List<Map<String, dynamic>>.from(itineraryResult['itinerary'] ?? []);
        itineraryList.addAll(instagramPlaces);
        itineraryResult['itinerary'] = itineraryList;
        print('DEBUG: Merged ${instagramPlaces.length} Instagram spots into itinerary');
      }

      if (mounted) {
        setState(() {
          _generatedItinerary = itineraryResult;
        });
      }

      // Simulate minimum loading time for UX
      await Future.delayed(const Duration(milliseconds: 1500));

      if (mounted) {
        setState(() => _currentStep = 5); // Completion state
      }
    } catch (e) {
      debugPrint('Error creating trip: $e');
      if (mounted) {
        setState(() => _currentStep = 5); // Still show completion for demo
      }
    }
  }

  Future<void> _selectDateRange() async {
    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime.now(),
      lastDate: DateTime(2101),
      initialDateRange: _startDate != null && _endDate != null
          ? DateTimeRange(start: _startDate!, end: _endDate!)
          : null,
      builder: (context, child) {
        return Theme(
          data: ThemeData.light().copyWith(
            colorScheme: ColorScheme.light(
              primary: darkTeal,
              onPrimary: Colors.white,
              surface: creamColor,
              onSurface: darkTeal,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null) {
      setState(() {
        _startDate = picked.start;
        _endDate = picked.end;
      });
    }
  }

  String _formatDate(DateTime? date) {
    if (date == null) return 'Select';
    final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return '${months[date.month - 1]} ${date.day}';
  }

  // Get map center based on user's destination (enhanced in the future with geocoding)
  LatLng _getMapCenter() {
    // For now, return default SoHo, NYC
    // TODO: Geocode _destination to get actual coordinates
    return const LatLng(40.7216, -74.0047);  // SoHo, NYC
  }

  @override
  Widget build(BuildContext context) {
    final keyboardHeight = MediaQuery.of(context).viewInsets.bottom;
    final isKeyboardOpen = keyboardHeight > 0;
    
    // Calculate the offset for the "Search this area" button to be above the bottom bar
    double bottomOffset = 24.0;
    if (_currentStep == 1) {
      // Bottom bar components height roughly:
      // Padding (20/40) + vibes (40+12) + who (44+12) + search (60)
      bottomOffset = keyboardHeight + (isKeyboardOpen ? 160 : 230);
    }

    // Dark theme constants for the card
    final cardColor = const Color(0xFF1E1E1E).withOpacity(0.85); // Dark Glass
    final inputColor = const Color(0xFF2C2C2C); // Dark Input Field
    final textColor = Colors.white;
    final hintColor = Colors.white54;

    return Scaffold(
      backgroundColor: const Color(0xFF121212), // Dark background for safety
      resizeToAvoidBottomInset: false,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. MAP LAYER (Pass the selected vibe down)
          DensityHeatmapWidget(
            center: _getMapCenter(),
            baseUrl: ApiService.baseUrl,
            // Pass the filter selected in the UI below
            selectedVibe: _selectedVibe, 
            onCellTap: (cellId, placeCount) {},
            bottomOffset: bottomOffset,
            onMapInteraction: () {
              if (_barFocus != DiscoveryBarFocus.map) {
                setState(() => _barFocus = DiscoveryBarFocus.map);
              }
            },
            onMapLongPress: (location) => _handleMapPinSelection(location),
            selectedLocation: _selectedLatLng,
          ),

          // 2. GRADIENT OVERLAY (Darker for better text contrast)
          IgnorePointer(
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.black.withOpacity(0.9), // Darker top
                    Colors.black.withOpacity(0.4),
                    Colors.transparent,
                    Colors.black.withOpacity(0.4), // Darker bottom for card blend
                  ],
                  stops: const [0.0, 0.15, 0.5, 1.0],
                ),
              ),
            ),
          ),

          // 3. UNIFIED HEADER (Title + Filters)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              bottom: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Row 1: Title & Icons
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _buildGlassIcon(Icons.arrow_back, () => Navigator.pop(context)),
                        Text(
                          'Plandit',
                          style: GoogleFonts.playfairDisplay(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.5,
                            shadows: [Shadow(color: Colors.black, blurRadius: 10)],
                          ),
                        ),
                        _buildGlassIcon(Icons.notifications_outlined, () {}),
                      ],
                    ),
                  ),

                  // Row 2: Filters (Now safely below the title)
                  SizedBox(
                    height: 50,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      children: [
                        _buildFilterPill('All', null),
                        _buildFilterPill('Coffee', 'coffee', icon: Icons.coffee),
                        _buildFilterPill('Nightlife', 'nightlife', icon: Icons.local_bar),
                        _buildFilterPill('Food', 'restaurant', icon: Icons.restaurant),
                        _buildFilterPill('Arts', 'arts', icon: Icons.palette),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 4. DRAGGABLE CARD / BOTTOM BAR
          _buildCurrentStep(),
        ],
      ),
    );
  }

  Widget _buildBottomSearchBar() {
    final keyboardHeight = MediaQuery.of(context).viewInsets.bottom;
    final isKeyboardOpen = keyboardHeight > 0;
    
    // Auto-focus logic: if keyboard opens, we are surely in address mode
    if (isKeyboardOpen && _barFocus == DiscoveryBarFocus.map) {
      _barFocus = DiscoveryBarFocus.address;
    }

    final isMinimized = _barFocus == DiscoveryBarFocus.map;
    
    return AnimatedPositioned(
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeOutCubic,
      bottom: keyboardHeight,
      left: 0,
      right: 0,
      child: GestureDetector(
        onTap: () {
          if (isMinimized) {
            setState(() => _barFocus = DiscoveryBarFocus.address);
          }
        },
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 300),
          opacity: isMinimized ? 0.6 : 1.0,
          child: Container(
            padding: EdgeInsets.fromLTRB(20, 10, 20, isKeyboardOpen ? 20 : (isMinimized ? 20 : 40)),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Colors.transparent, Colors.black.withOpacity(isMinimized ? 0.1 : 0.2)],
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Suggestions
                if (_suggestions.isNotEmpty)
                  Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    decoration: BoxDecoration(
                      color: PlanditColors.card,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: PlanditColors.border.withOpacity(0.3)),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.1),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: ListView.separated(
                      shrinkWrap: true,
                      padding: EdgeInsets.zero,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _suggestions.length.clamp(0, 5),
                      separatorBuilder: (context, index) => Divider(height: 1, color: Colors.black.withOpacity(0.05)),
                      itemBuilder: (context, index) {
                        final s = _suggestions[index];
                        return ListTile(
                          dense: true,
                          leading: const Icon(Icons.location_on_outlined, color: PlanditColors.accent, size: 18),
                          title: Text(
                            s['display'],
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              color: PlanditColors.foreground,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          onTap: () => _selectSuggestion(s),
                        );
                      },
                    ),
                  ),
                
                // Search Bar
                Container(
                  decoration: BoxDecoration(
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(isMinimized ? 0.05 : 0.2), blurRadius: 20, offset: const Offset(0, 8))
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(30),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(isMinimized ? 0.4 : 0.85),
                          borderRadius: BorderRadius.circular(30),
                          border: Border.all(color: Colors.black.withOpacity(0.08)),
                        ),
                        child: TextField(
                          controller: _destinationController,
                          focusNode: _destinationFocusNode,
                          onTap: () => setState(() => _barFocus = DiscoveryBarFocus.address),
                          onChanged: _onDestinationChanged,
                          enabled: !isMinimized,
                          style: const TextStyle(color: Colors.black87, fontSize: 16, fontWeight: FontWeight.w600),
                          decoration: InputDecoration(
                            filled: false,
                            prefixIcon: const Icon(Icons.search_rounded, color: Color(0xFFE91E63), size: 22),
                            suffixIcon: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.location_on_outlined, color: Colors.black45, size: 20),
                                  onPressed: () => _handleMapPinSelection(_getMapCenter()),
                                  tooltip: "Select this area",
                                ),
                                IconButton(
                                  icon: const Icon(Icons.arrow_forward_rounded, color: Colors.black54, size: 20),
                                  onPressed: () {
                                    if (_destinationController.text.isNotEmpty) _startGeneration();
                                  },
                                ),
                              ],
                            ),
                            hintText: "Where to wander?",
                            hintStyle: TextStyle(color: Colors.black.withOpacity(0.4), fontSize: 15),
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
    
                // Progressive disclosure of Who & Vibe
                AnimatedSize(
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeInOut,
                  child: Column(
                    children: [
                      if (!isMinimized && (_barFocus == DiscoveryBarFocus.who || _barFocus == DiscoveryBarFocus.vibe)) ...[
                        const SizedBox(height: 12),
                        // IOS Style "Who" Segments
                        Container(
                          height: 44,
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0),
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(color: Colors.black.withOpacity(0.05)),
                          ),
                          child: Row(
                            children: [
                              _buildWhoSegment("Solo", "👤"),
                              _buildWhoSegment("Couple", "💑"),
                              _buildWhoSegment("Group", "👥"),
                            ],
                          ),
                        ),
                      ],
        
                      if (!isMinimized && _barFocus == DiscoveryBarFocus.vibe) ...[
                        const SizedBox(height: 12),
                        // Horizontal Vibe Pill Selector
                        SizedBox(
                          height: 40,
                          child: ListView.builder(
                            scrollDirection: Axis.horizontal,
                            padding: EdgeInsets.zero,
                            itemCount: vibeOptions.length,
                            itemBuilder: (context, index) {
                              final vibe = vibeOptions[index];
                              final label = vibe['label'] as String;
                              final isSelected = _selectedVibes.contains(label);
                              
                              return Padding(
                                padding: const EdgeInsets.only(right: 8.0),
                                child: GestureDetector(
                                  onTap: () {
                                    HapticFeedback.selectionClick();
                                    _toggleVibe(label);
                                  },
                                  child: AnimatedContainer(
                                    duration: const Duration(milliseconds: 200),
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: isSelected ? Colors.white : Colors.white.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(color: isSelected ? Colors.transparent : Colors.black.withOpacity(0.05)),
                                      boxShadow: isSelected ? [BoxShadow(color: Colors.black.withOpacity(0.08), blurRadius: 4, offset: const Offset(0, 2))] : [],
                                    ),
                                    child: Center(
                                      child: Text(
                                        label,
                                        style: GoogleFonts.inter(
                                          fontSize: 12,
                                          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                          color: isSelected ? Colors.black87 : Colors.black87.withOpacity(0.6),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildWhoSegment(String label, String emoji) {
    final isSelected = _selectedWho == label;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _selectedWho = label;
            _barFocus = DiscoveryBarFocus.vibe; // Advance to Vibe focus
          });
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
          decoration: BoxDecoration(
            color: isSelected ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(18),
            boxShadow: isSelected 
              ? [BoxShadow(color: Colors.black.withOpacity(0.08), blurRadius: 4, offset: const Offset(0, 2))]
              : [],
          ),
          child: Center(
            child: Text(
              "$emoji $label",
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected ? Colors.black87 : Colors.black54,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          GestureDetector(
            onTap: () => Navigator.pop(context),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(26),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.arrow_back, color: Colors.white, size: 20),
            ),
          ),
          // Spacer to balance the row if needed or just use Expanded/Center
          Text(
            'Plandit',
            style: GoogleFonts.playfairDisplay(
              color: Colors.white,
              fontSize: 28,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.5,
            ),
          ),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(26),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.notifications_outlined, color: Colors.white, size: 20),
          ),
        ],
      ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case 1:
        return _buildBottomSearchBar();
      case 3:
        return _buildStepCard(_buildVibeStep(), key: const ValueKey('vibe'));
      case 4:
        return _buildLoadingState();
      case 5:
        return _buildCompletionState();
      default:
        return Container();
    }
  }

  // Wrapper for the cream cards - Optimized Physics
  Widget _buildStepCard(Widget content, {Key? key}) {
    final screenHeight = MediaQuery.of(context).size.height;
    
    // Calculate actual pixel height based on percentage
    final double currentPixelHeight = screenHeight * _cardHeight;

    return Positioned(
      key: key,
      left: 0,
      right: 0,
      bottom: 0,
      height: currentPixelHeight,
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFF121212).withOpacity(0.85), // Dark transparent background
              borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
              border: Border(top: BorderSide(color: Colors.white.withOpacity(0.1), width: 1)),
            ),
            child: Column(
              children: [
                // DRAG HANDLE AREA
                GestureDetector(
                  onVerticalDragUpdate: (details) {
                    setState(() {
                      final delta = -details.delta.dy / screenHeight;
                      _cardHeight = (_cardHeight + delta).clamp(0.2, 0.92);
                    });
                  },
                  onVerticalDragEnd: (details) {
                    final velocity = -details.velocity.pixelsPerSecond.dy / screenHeight;
                    if (velocity > 0.5) {
                      _animateCardTo(0.92);
                    } else if (velocity < -0.5) {
                       _animateCardTo(0.3);
                    } else {
                      if (_cardHeight < 0.45) {
                        _animateCardTo(0.3);
                      } else if (_cardHeight < 0.8) {
                        _animateCardTo(0.72);
                      } else {
                        _animateCardTo(0.92);
                      }
                    }
                  },
                  behavior: HitTestBehavior.translucent,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: Center(
                      child: Container(
                        width: 40,
                        height: 5,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(2.5),
                        ),
                      ),
                    ),
                  ),
                ),
                
                // CONTENT AREA
                Expanded(
                  child: content,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _animateCardTo(double target) {
    final start = _cardHeight;
    _animationController.reset();
    
    // Animation listener to update state frame-by-frame
    final animation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeOutCubic, // Smoother "physics" feel than linear
    );

    animation.addListener(() {
      setState(() {
        _cardHeight = start + (animation.value * (target - start));
      });
    });

    _animationController.forward();
  }

  // Step 1: Destination
  Widget _buildDestinationStep() {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 12),
                  // Animated spacing: increases when focused to move search bar down
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeInOut,
                    height: _isInputFocused ? 60 : 40, // Reduced from 100 to 60 to avoid overflow
                  ),
                  
                  // 1. Centered Typography - stays visible
                  Text(
                    "Where do you\nwant to wander?",
                    textAlign: TextAlign.center,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 34,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      height: 1.1,
                      letterSpacing: -0.5,
                    ),
                  ),
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeInOut,
                    height: _isInputFocused ? 32 : 32, // Kept consistent
                  ),

                  Container(
                    decoration: BoxDecoration(
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.2), 
                          blurRadius: 15, 
                          offset: const Offset(0, 5)
                        )
                      ],
                    ),
                    child: TextField(
                      controller: _destinationController,
                      focusNode: _destinationFocusNode,
                      onChanged: _onDestinationChanged,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.white),
                      decoration: InputDecoration(
                        filled: true,
                        fillColor: const Color(0xFF2C2C2C),
                        prefixIcon: const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 16),
                          child: Icon(Icons.location_on_outlined, color: Color(0xFFE91E63), size: 26),
                        ),
                        hintText: "Chicago",
                        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 18),
                        contentPadding: const EdgeInsets.symmetric(vertical: 22),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(20),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                  ),

                  // Suggestions List
                  if (_suggestions.isNotEmpty)
                    Container(
                      margin: const EdgeInsets.only(top: 4, bottom: 12),
                      decoration: BoxDecoration(
                        color: PlanditColors.card,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: PlanditColors.border.withOpacity(0.3)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: ListView.separated(
                        shrinkWrap: true,
                        padding: EdgeInsets.zero,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: _suggestions.length.clamp(0, 5),
                        separatorBuilder: (context, index) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final suggestion = _suggestions[index];
                          return ListTile(
                            dense: true,
                            leading: const Icon(Icons.location_on_outlined, color: PlanditColors.accent, size: 18),
                            title: Text(
                              suggestion['display'],
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: PlanditColors.foreground,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            onTap: () => _selectSuggestion(suggestion),
                          );
                        },
                      ),
                    ),
                  
                  // Animated gap: collapses when focused
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeInOut,
                    height: _isInputFocused ? 12 : 32, // Extra padding when focused instead of 0
                  ),
                  
                  // Who's this trip for? section
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    curve: Curves.easeInOut,
                    height: _isInputFocused ? 0 : 200, // Collapse height when focused
                    child: AnimatedOpacity(
                      duration: const Duration(milliseconds: 200),
                      opacity: _isInputFocused ? 0.0 : 1.0,
                      child: SingleChildScrollView(
                        physics: const NeverScrollableScrollPhysics(),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            Text(
                              "Who's this trip for?",
                              textAlign: TextAlign.center,
                              style: GoogleFonts.playfairDisplay(
                                fontSize: 28,
                                fontWeight: FontWeight.w700,
                                color: Colors.white,
                                letterSpacing: -0.5,
                              ),
                            ),
                            const SizedBox(height: 20),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                GestureDetector(
                                  onTap: () => setState(() => _selectedWho = 'Solo'),
                                  child: _buildFilterChip("👤 Solo", _selectedWho == 'Solo'),
                                ),
                                const SizedBox(width: 10),
                                GestureDetector(
                                  onTap: () => setState(() => _selectedWho = 'Couple'),
                                  child: _buildFilterChip("💑 Couple", _selectedWho == 'Couple'),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            GestureDetector(
                              onTap: () => setState(() => _selectedWho = 'Group'),
                              child: _buildFilterChip("👥 Group", _selectedWho == 'Group'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 40), // Replaced Spacer with fixed spacing for ScrollView
                  
                  _buildNextButton(onTap: _nextStep),
                  const SizedBox(height: 30),
                ],
              ),
            ),
          ),
        );
      }
    );
  }

  // Step 2: Context
  Widget _buildContextStep() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: ListView(
        physics: const BouncingScrollPhysics(),
        children: [
          const SizedBox(height: 10),
          Center(
            child: Container(
              width: 32, 
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2)
              )
            )
          ),
          const SizedBox(height: 30),
          Text(
            "When & Who",
            style: GoogleFonts.playfairDisplay(
              fontSize: 36,
              fontWeight: FontWeight.w700,
              color: darkTeal,
              letterSpacing: -1.0,
            ),
          ),

          Text("Who's this trip for?", style: TextStyle(color: Colors.grey[600], fontWeight: FontWeight.w500)),
          const SizedBox(height: 16),
          Row(
            children: [
              GestureDetector(
                onTap: () => setState(() => _selectedWho = 'Solo'),
                child: _buildFilterChip("Solo", _selectedWho == 'Solo'),
              ),
              const SizedBox(width: 10),
              GestureDetector(
                onTap: () => setState(() => _selectedWho = 'Couple'),
                child: _buildFilterChip("Couple", _selectedWho == 'Couple'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          GestureDetector(
            onTap: () => setState(() => _selectedWho = 'Group'),
            child: _buildFilterChip("Group", _selectedWho == 'Group'),
          ),
          const SizedBox(height: 20),
          _buildNextButton(onTap: _nextStep),
          const SizedBox(height: 20),
        ],
      ),
    );

  }

  // Step 3: Vibe Selection
  Widget _buildVibeStep() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 10),
          Center(
            child: Container(
              width: 32, 
              height: 4, 
              decoration: BoxDecoration(
                color: Colors.grey[300], 
                borderRadius: BorderRadius.circular(2)
              )
            )
          ),
          const SizedBox(height: 20),
          Text(
            "What kind of trip\nis this?", 
            style: GoogleFonts.playfairDisplay(
              fontSize: 36, 
              fontWeight: FontWeight.w700, 
              color: Colors.white, 
              height: 1.05,
              letterSpacing: -1.0
            )
          ),
          Text("Pick up to 3 — we'll do the rest.", style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 14)),
          const SizedBox(height: 24),
          Expanded(
            child: GridView.count(
              crossAxisCount: 2,
              childAspectRatio: 1.6,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              padding: EdgeInsets.zero,
              children: vibeOptions.map((vibe) {
                final isSelected = _selectedVibes.contains(vibe['label']);
                return GestureDetector(
                  onTap: () => _toggleVibe(vibe['label']),
                  child: _buildVibeCard(vibe['icon'], vibe['label'], isSelected),
                );
              }).toList(),
            ),
          ),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _startGeneration,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFE91E63),
                foregroundColor: Colors.white,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 18),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                shadowColor: const Color(0xFFE91E63).withOpacity(0.4),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text("Generate My Trip", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 8),
                  const Icon(Icons.auto_awesome, color: Colors.white, size: 20),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // Step 4: Loading State (Glassmorphism)
  Widget _buildLoadingState() {
    final destination = _destinationController.text.trim().isNotEmpty 
        ? _destinationController.text.trim() 
        : 'Chicago';
    final vibesText = _selectedVibes.isNotEmpty 
        ? _selectedVibes.join(' • ') 
        : 'Hidden Gems • Foodie';

    return Center(
      key: const ValueKey('loading'),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            width: 300,
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E1E).withOpacity(0.8),
              border: Border.all(color: Colors.white.withOpacity(0.1)),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.auto_awesome, color: Color(0xFFE91E63), size: 40),
                const SizedBox(height: 20),
                Text(
                  "Planning your\n$destination trip...",
                  textAlign: TextAlign.center,
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 26,
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  vibesText,
                  style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 20),
                const SizedBox(
                  width: 32,
                  height: 32,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFE91E63)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // Step 5: Completion State
  Widget _buildCompletionState() {
    final destination = _destinationController.text.trim().isNotEmpty 
        ? _destinationController.text.trim() 
        : 'Chicago';
    final days = (_startDate != null && _endDate != null)
        ? _endDate!.difference(_startDate!).inDays + 1
        : 4;

    return Align(
      key: const ValueKey('completion'),
      alignment: Alignment.bottomCenter,
      child: Container(
        height: MediaQuery.of(context).size.height * 0.55,
        width: double.infinity,
        margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 20),
        decoration: BoxDecoration(
          color: const Color(0xFF1E1E1E).withOpacity(0.95),
          borderRadius: BorderRadius.circular(32),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
        ),
        child: Column(
          children: [
            Expanded(
              flex: 5,
              child: ClipRRect(
                borderRadius: const BorderRadius.only(topLeft: Radius.circular(32), topRight: Radius.circular(32)),
                child: Image.network(
                  'https://images.unsplash.com/photo-1494522855154-9297ac14b55f?q=80&w=800',
                  fit: BoxFit.cover,
                  width: double.infinity,
                  errorBuilder: (context, error, stackTrace) => Container(color: accentGreen),
                ),
              ),
            ),
            Expanded(
              flex: 4,
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _generatedItinerary?['title'] ?? "$destination: Hidden\nCorners & Iconic Eats",
                      style: GoogleFonts.playfairDisplay(
                        fontSize: 28, 
                        fontWeight: FontWeight.w700, 
                        color: Colors.white, 
                        height: 1.1,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _generatedItinerary?['subtitle'] ?? "$days days • Walkable • Curated by AI",
                      style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12),
                    ),
                    const Spacer(),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () {
                          if (_generatedItinerary != null) {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ItineraryDetailScreen(itinerary: _generatedItinerary!),
                              ),
                            ).then((_) => Navigator.pop(context));
                          } else {
                            Navigator.pop(context);
                          }
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFE91E63),
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        ),
                        child: const Text("View Trip →", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    )
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // --- HELPER WIDGETS ---

  Widget _buildNextButton({required VoidCallback onTap}) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: onTap,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.white.withOpacity(0.1),
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(vertical: 20),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(36),
            side: BorderSide(color: Colors.white.withOpacity(0.2)),
          ),
        ),
        child: const Text("Next →", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
      ),
    );
  }

  // 1. The Dark Filter Pill
  Widget _buildFilterPill(String label, String? value, {IconData? icon}) {
    final isSelected = _selectedVibe == value;
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedVibe = value);
      },
      child: Container(
        margin: const EdgeInsets.only(right: 10),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? null : Colors.white.withOpacity(0.1),
          gradient: isSelected 
              ? const LinearGradient(colors: [Color(0xFF9C27B0), Color(0xFFE91E63)])
              : null,
          borderRadius: BorderRadius.circular(25),
          border: Border.all(
            color: isSelected ? Colors.transparent : Colors.white.withOpacity(0.2),
            width: 1,
          ),
          boxShadow: isSelected 
              ? [BoxShadow(color: const Color(0xFFE91E63).withOpacity(0.4), blurRadius: 8)] 
              : [],
        ),
        child: Row(
          children: [
            if (icon != null) ...[
              Icon(icon, size: 16, color: Colors.white),
              const SizedBox(width: 6),
            ],
            Text(
              label,
              style: TextStyle(
                color: Colors.white,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // 2. The Glass Icon Button
  Widget _buildGlassIcon(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.1),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _buildImgPreview(String url) {
    return Padding(
      padding: const EdgeInsets.only(right: 16),
      child: AspectRatio(
        aspectRatio: 0.75, // Taller, editorial ratio
        child: ClipRRect(
          borderRadius: BorderRadius.circular(24),
          child: Image.network(
            url,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) => Container(
              decoration: BoxDecoration(
                color: accentGreen.withOpacity(0.3),
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.image, color: Colors.white54),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFilterChip(String label, bool isSelected) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      decoration: BoxDecoration(
        color: isSelected ? const Color(0xFFE91E63) : Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: isSelected ? Colors.transparent : Colors.white.withOpacity(0.2)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildVibeCard(IconData icon, String label, bool isSelected) {
    // Extract emoji from label (first 2 characters which is the emoji)
    final emoji = label.split(' ').first;
    final text = label.substring(emoji.length).trim();
    
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: isSelected ? const Color(0xFFE91E63).withOpacity(0.2) : Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isSelected ? const Color(0xFFE91E63) : Colors.white.withOpacity(0.1), 
          width: 1.5
        ),
        boxShadow: isSelected ? [BoxShadow(color: const Color(0xFFE91E63).withOpacity(0.2), blurRadius: 10)] : [],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            emoji,
            style: const TextStyle(fontSize: 40),
          ),
          const SizedBox(height: 8),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

/// Helper function to show the Trip Wizard as a full-screen modal
void showTripWizard(BuildContext context) {
  Navigator.push(
    context,
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (context) => const TripWizardScreen(),
    ),
  );
}
