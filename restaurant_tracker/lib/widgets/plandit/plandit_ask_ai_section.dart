import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import '../../api_service.dart';
import 'plandit_filter_sheet.dart';
import '../../screens/curated_journey_preview_screen.dart';
import 'dart:async';

class CuratedSuggestion {
  final String id;
  final String text;
  final IconData icon;
  final String category;

  CuratedSuggestion({
    required this.id,
    required this.text,
    required this.icon,
    required this.category,
  });
}

class PlanditAskAISection extends StatefulWidget {
  const PlanditAskAISection({super.key});

  @override
  State<PlanditAskAISection> createState() => _PlanditAskAISectionState();
}

class _PlanditAskAISectionState extends State<PlanditAskAISection> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isFocused = false;

  // Filter state
  String? _selectedLocation;
  String? _selectedVibe;
  String? _selectedSocialContext;
  String? _selectedTimeOfDay;
  List<String> _selectedCuisines = [];

  final List<Map<String, String>> quickFilters = [
    {'id': 'coffee', 'label': 'Coffee Run', 'emoji': '☕️'},
    {'id': 'work', 'label': 'Work Friendly', 'emoji': '💻'},
    {'id': 'breakfast', 'label': 'Breakfast Classic', 'emoji': '🥐'},
    {'id': 'brunch', 'label': 'Brunch Spot', 'emoji': '🍳'},
    {'id': 'date-night', 'label': 'Date Night', 'emoji': '🍷'},
  ];

  final List<CuratedSuggestion> curatedSuggestions = [
    CuratedSuggestion(
      id: "speakeasy",
      text: "Hidden speakeasies in the West Village",
      icon: Icons.local_bar_outlined,
      category: "Nightlife",
    ),
    CuratedSuggestion(
      id: "date-night",
      text: "Romantic date night in Brooklyn",
      icon: Icons.auto_awesome_outlined,
      category: "Date Ideas",
    ),
    CuratedSuggestion(
      id: "coffee",
      text: "Best third-wave coffee spots in SoHo",
      icon: Icons.coffee_outlined,
      category: "Coffee",
    ),
    CuratedSuggestion(
      id: "jazz",
      text: "Live jazz & craft cocktails evening",
      icon: Icons.music_note_outlined,
      category: "Music",
    ),
    CuratedSuggestion(
      id: "foodie",
      text: "Michelin-worthy tasting menus under \$100",
      icon: Icons.restaurant_outlined,
      category: "Dining",
    ),
    CuratedSuggestion(
      id: "neighborhood",
      text: "A perfect afternoon in DUMBO",
      icon: Icons.location_on_outlined,
      category: "Explore",
    ),
  ];

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(() {
      setState(() {
        _isFocused = _focusNode.hasFocus;
      });
    });
  }

  List<CuratedSuggestion> get _filteredSuggestions {
    final query = _controller.text.trim().toLowerCase();
    if (query.isEmpty) return curatedSuggestions;
    return curatedSuggestions
        .where((s) =>
            s.text.toLowerCase().contains(query) ||
            s.category.toLowerCase().contains(query))
        .toList();
  }

  String _getSubtitleFromFilters(Map<String, dynamic>? filters) {
    if (filters == null) return '';
    final parts = <String>[];
    if (filters['timeOfDay'] != null) {
      parts.add(filters['timeOfDay'].toString());
    }
    if (filters['vibe'] != null) {
      parts.add(filters['vibe'].toString());
    }
    if (parts.isEmpty && filters['socialContext'] != null) {
      parts.add(filters['socialContext'].toString());
    }
    return parts.join(' • ');
  }

  Future<void> _handleSubmit() async {
    if (_controller.text.trim().isEmpty) return;

    final query = _controller.text.trim();
    _focusNode.unfocus();

    // Show loading dialog
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
                  valueColor:
                      AlwaysStoppedAnimation<Color>(PlanditColors.accent),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Crafting your itinerary...',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: PlanditColors.foreground,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Parsing "$query"',
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
      // Call the API
      final apiService = ApiService();

      Map<String, dynamic>? activeFilters;
      if (_selectedLocation != null ||
          _selectedVibe != null ||
          _selectedSocialContext != null ||
          _selectedTimeOfDay != null ||
          _selectedCuisines.isNotEmpty) {
        activeFilters = {
          'vibe': _selectedVibe,
          'socialContext': _selectedSocialContext,
          'timeOfDay': _selectedTimeOfDay,
          'cuisines': _selectedCuisines,
        };

        // If manual location provided, geocode it
        if (_selectedLocation != null) {
          try {
            final results =
                await apiService.geocodeNominatim(_selectedLocation!);
            if (results.isNotEmpty) {
              final firstResult = results.first;
              activeFilters['latitude'] =
                  firstResult['geometry']['location']['lat'];
              activeFilters['longitude'] =
                  firstResult['geometry']['location']['lng'];
            }
          } catch (e) {
            print('ERROR: Geocoding failed for filter location: $e');
          }
        }
      }

      final result = await apiService.generateItineraryFromQuery(
        query,
        filters: activeFilters,
      );

      // Close loading dialog
      if (mounted) Navigator.of(context).pop();

      // Transform result to match preview screen format
      final previewItinerary = {
        'title': query,
        'new_title': query,
        'subtitle': _getSubtitleFromFilters(activeFilters),
        'description':
            'An experience curated just for you, designed to unfold like the best stories do...',
        'itinerary_id':
            result['itinerary_id'], // Preserve itinerary_id for tracking
        'narrative': result['narrative'],
        'total_walk_time_mins': result['total_walk_time_mins'],
        'filters': activeFilters,
        'itinerary_data': {
          'itinerary': result['itinerary'] ?? [],
        },
      };

      // Navigate to CuratedJourneyPreviewScreen
      if (mounted) {
        Navigator.of(context).push(
          MaterialPageRoute(
            fullscreenDialog: true,
            builder: (context) => CuratedJourneyPreviewScreen(
              itinerary: previewItinerary,
              onClose: () {
                Navigator.of(context).pop();
                _controller.clear();
              },
            ),
          ),
        );
      }
    } catch (e) {
      // Close loading dialog
      if (mounted) Navigator.of(context).pop();

      // Show error dialog
      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            backgroundColor: PlanditColors.card,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            title: Row(
              children: [
                const Icon(Icons.error_outline, color: Colors.red, size: 24),
                const SizedBox(width: 12),
                Text(
                  'Oops!',
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            content: Text(
              'We couldn\'t generate your itinerary. Please try again.\n\nError: ${e.toString()}',
              style: const TextStyle(
                fontSize: 14,
                color: PlanditColors.mutedForeground,
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text(
                  'OK',
                  style: TextStyle(color: PlanditColors.accent),
                ),
              ),
            ],
          ),
        );
      }
    }
  }

  void _handleFilterClick(String label) {
    _controller.text = label;
    _focusNode.unfocus();
    setState(() {});

    // Auto-submit after brief delay
    Future.delayed(const Duration(milliseconds: 100), () {
      _handleSubmit();
    });
  }

  void _handleSuggestionClick(String suggestionText) {
    _controller.text = suggestionText;
    _focusNode.unfocus();
    setState(() {});

    // Auto-submit after selection
    Future.delayed(const Duration(milliseconds: 100), () {
      _handleSubmit();
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredSuggestions;
    final showSuggestions = _isFocused && filtered.isNotEmpty;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        children: [
          // Search Table/Container
          Container(
            decoration: BoxDecoration(
              color: PlanditColors.card,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: _isFocused
                    ? PlanditColors.border
                    : PlanditColors.border.withOpacity(0.3),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(_isFocused ? 0.1 : 0.05),
                  blurRadius: _isFocused ? 12 : 4,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Search Bar
                GestureDetector(
                  onTap: () => _focusNode.requestFocus(),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 12),
                    color:
                        Colors.transparent, // Ensure the whole area is tappable
                    child: Row(
                      children: [
                        Icon(
                          Icons.auto_awesome_outlined,
                          size: 16,
                          color: _controller.text.isNotEmpty
                              ? PlanditColors.accent
                              : PlanditColors.mutedForeground.withOpacity(0.6),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _controller,
                            focusNode: _focusNode,
                            decoration: InputDecoration(
                              hintText: 'Plan a date night in Chelsea...',
                              hintStyle: GoogleFonts.playfairDisplay(
                                fontSize: 14,
                                color: PlanditColors.mutedForeground
                                    .withOpacity(0.5),
                                fontStyle: FontStyle.italic,
                              ),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: EdgeInsets.zero,
                            ),
                            style: const TextStyle(
                              fontSize: 14,
                              color: PlanditColors.foreground,
                            ),
                            onChanged: (value) => setState(() {}),
                            onSubmitted: (_) => _handleSubmit(),
                          ),
                        ),
                        const SizedBox(width: 12),
                        // Filter Button
                        GestureDetector(
                          onTap: () async {
                            final result = await showModalBottomSheet<
                                Map<String, dynamic>>(
                              context: context,
                              isScrollControlled: true,
                              backgroundColor: Colors.transparent,
                              builder: (context) => PlanditFilterSheet(
                                initialLocation: _selectedLocation,
                                initialVibe: _selectedVibe,
                                initialSocialContext: _selectedSocialContext,
                                initialTimeOfDay: _selectedTimeOfDay,
                                initialCuisines: _selectedCuisines,
                              ),
                            );

                            if (result != null) {
                              setState(() {
                                _selectedLocation = result['location'];
                                _selectedVibe = result['vibe'];
                                _selectedSocialContext =
                                    result['socialContext'];
                                _selectedTimeOfDay = result['timeOfDay'];
                                _selectedCuisines = result['cuisines'] ?? [];
                              });
                            }
                          },
                          child: Stack(
                            children: [
                              Container(
                                width: 36,
                                height: 36,
                                decoration: BoxDecoration(
                                  color:
                                      PlanditColors.secondary.withOpacity(0.5),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  Icons.tune_outlined,
                                  size: 16,
                                  color: (_selectedLocation != null ||
                                          _selectedVibe != null ||
                                          _selectedSocialContext != null ||
                                          _selectedTimeOfDay != null ||
                                          _selectedCuisines.isNotEmpty)
                                      ? PlanditColors.accent
                                      : PlanditColors.mutedForeground,
                                ),
                              ),
                              if (_selectedLocation != null ||
                                  _selectedVibe != null ||
                                  _selectedSocialContext != null ||
                                  _selectedTimeOfDay != null ||
                                  _selectedCuisines.isNotEmpty)
                                Positioned(
                                  right: 0,
                                  top: 0,
                                  child: Container(
                                    width: 8,
                                    height: 8,
                                    decoration: const BoxDecoration(
                                      color: PlanditColors.accent,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        GestureDetector(
                          onTap: _controller.text.trim().isNotEmpty
                              ? _handleSubmit
                              : null,
                          child: Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: _controller.text.trim().isNotEmpty
                                  ? const Color(0xFFF5DEB3).withOpacity(0.8)
                                  : PlanditColors.muted,
                              shape: BoxShape.circle,
                            ),
                            child: Center(
                              child: Text(
                                'Go',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: _controller.text.trim().isNotEmpty
                                      ? const Color(0xFF8B4513)
                                      : PlanditColors.mutedForeground,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Suggestions List
                if (showSuggestions) ...[
                  const Divider(height: 1, color: PlanditColors.border),
                  Container(
                    constraints: const BoxConstraints(maxHeight: 250),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                          child: Row(
                            children: [
                              const Icon(Icons.auto_awesome,
                                  size: 10, color: PlanditColors.accent),
                              const SizedBox(width: 6),
                              Text(
                                'TRY SEARCHING FOR',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: PlanditColors.mutedForeground
                                      .withOpacity(0.8),
                                  letterSpacing: 1.2,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Flexible(
                          child: ListView.builder(
                            shrinkWrap: true,
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            itemCount: filtered.length,
                            itemBuilder: (context, index) {
                              final suggestion = filtered[index];
                              return ListTile(
                                leading: Container(
                                  padding: const EdgeInsets.all(6),
                                  decoration: BoxDecoration(
                                    color:
                                        PlanditColors.accent.withOpacity(0.1),
                                    shape: BoxShape.circle,
                                  ),
                                  child: Icon(
                                    suggestion.icon,
                                    size: 14,
                                    color: PlanditColors.accent,
                                  ),
                                ),
                                title: Text(
                                  suggestion.text,
                                  style: const TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500,
                                    color: PlanditColors.foreground,
                                  ),
                                ),
                                subtitle: Text(
                                  suggestion.category,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: PlanditColors.mutedForeground
                                        .withOpacity(0.7),
                                  ),
                                ),
                                dense: true,
                                contentPadding:
                                    const EdgeInsets.symmetric(horizontal: 16),
                                onTap: () =>
                                    _handleSuggestionClick(suggestion.text),
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          // Quick Filters
          const SizedBox(height: 12),
          SizedBox(
            height: 36,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: quickFilters.length,
              separatorBuilder: (context, index) => const SizedBox(width: 8),
              itemBuilder: (context, index) {
                final filter = quickFilters[index];
                return GestureDetector(
                  onTap: () => _handleFilterClick(filter['label']!),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: PlanditColors.secondary.withOpacity(0.8),
                      borderRadius: BorderRadius.circular(100),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.08),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          filter['emoji']!,
                          style: const TextStyle(fontSize: 14),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          filter['label']!,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: PlanditColors.mutedForeground,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }
}
