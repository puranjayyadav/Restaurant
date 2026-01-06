import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import '../../api_service.dart';
import 'dart:async';

class PlanditFilterSheet extends StatefulWidget {
  final String? initialLocation;
  final String? initialVibe;
  final String? initialSocialContext;
  final String? initialTimeOfDay;
  final List<String> initialCuisines;

  const PlanditFilterSheet({
    super.key,
    this.initialLocation,
    this.initialVibe,
    this.initialSocialContext,
    this.initialTimeOfDay,
    this.initialCuisines = const [],
  });

  @override
  State<PlanditFilterSheet> createState() => _PlanditFilterSheetState();
}

class _PlanditFilterSheetState extends State<PlanditFilterSheet> {
  late TextEditingController _locationController;
  String? _selectedVibe;
  String? _selectedSocialContext;
  String? _selectedTimeOfDay;
  late List<String> _selectedCuisines;

  // Suggestion state
  List<Map<String, dynamic>> _suggestions = [];
  bool _isLoadingSuggestions = false;
  Timer? _debounceTimer;
  final ApiService _apiService = ApiService();

  final List<String> vibes = ['Chill', 'Trendy', 'Romantic', 'Lively', 'Cozy'];
  final List<String> socialContexts = ['Solo', 'Couple', 'Group'];
  final List<String> timesOfDay = ['Morning', 'Afternoon', 'Evening', 'Late Night'];
  final List<String> cuisines = [
    'Italian', 'Japanese', 'Mexican', 'French', 'Chinese', 
    'Indian', 'Mediterranean', 'Thai', 'Korean', 'American'
  ];

  @override
  void initState() {
    super.initState();
    _locationController = TextEditingController(text: widget.initialLocation);
    _selectedVibe = widget.initialVibe;
    _selectedSocialContext = widget.initialSocialContext;
    _selectedTimeOfDay = widget.initialTimeOfDay;
    _selectedCuisines = List.from(widget.initialCuisines);
  }

  @override
  void dispose() {
    _locationController.dispose();
    super.dispose();
  }

  void _clearAll() {
    setState(() {
      _locationController.clear();
      _selectedVibe = null;
      _selectedSocialContext = null;
      _selectedTimeOfDay = null;
      _selectedCuisines.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Filters',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                  color: PlanditColors.foreground,
                ),
              ),
              TextButton(
                onPressed: _clearAll,
                child: Text(
                  'Clear All',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: PlanditColors.accent,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          
          Flexible(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle('Location'),
                  const SizedBox(height: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: _locationController,
                        decoration: InputDecoration(
                          hintText: 'e.g. West Village, Brooklyn...',
                          hintStyle: GoogleFonts.inter(
                            fontSize: 14,
                            color: PlanditColors.mutedForeground.withOpacity(0.5),
                          ),
                          prefixIcon: const Icon(Icons.location_on_outlined, size: 18),
                          suffixIcon: _isLoadingSuggestions
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: Padding(
                                    padding: EdgeInsets.all(10.0),
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(PlanditColors.accent),
                                    ),
                                  ),
                                )
                              : null,
                          filled: true,
                          fillColor: PlanditColors.secondary.withOpacity(0.3),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide.none,
                          ),
                          isDense: true,
                        ),
                        onChanged: (value) {
                          if (_debounceTimer?.isActive ?? false) _debounceTimer!.cancel();
                          _debounceTimer = Timer(const Duration(milliseconds: 300), () async {
                            if (value.length >= 2) {
                              setState(() => _isLoadingSuggestions = true);
                              final results = await _apiService.getAddressSuggestions(value);
                              if (mounted) {
                                setState(() {
                                  _suggestions = results;
                                  _isLoadingSuggestions = false;
                                });
                              }
                            } else {
                              setState(() {
                                _suggestions = [];
                                _isLoadingSuggestions = false;
                              });
                            }
                          });
                        },
                      ),
                      if (_suggestions.isNotEmpty)
                        Container(
                          margin: const EdgeInsets.only(top: 4),
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
                            itemCount: _suggestions.length,
                            separatorBuilder: (context, index) => const Divider(height: 1),
                            itemBuilder: (context, index) {
                              final suggestion = _suggestions[index];
                              return ListTile(
                                dense: true,
                                title: Text(
                                  suggestion['display'],
                                  style: const TextStyle(fontSize: 13),
                                ),
                                onTap: () {
                                  setState(() {
                                    _locationController.text = suggestion['display'];
                                    _suggestions = [];
                                  });
                                },
                              );
                            },
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  
                  _buildSectionTitle('Vibe'),
                  _buildChips(vibes, _selectedVibe, (val) => setState(() => _selectedVibe = val)),
                  const SizedBox(height: 24),
                  
                  _buildSectionTitle('Social Context'),
                  _buildChips(socialContexts, _selectedSocialContext, (val) => setState(() => _selectedSocialContext = val)),
                  const SizedBox(height: 24),
                  
                  _buildSectionTitle('Time of Day'),
                  _buildChips(timesOfDay, _selectedTimeOfDay, (val) => setState(() => _selectedTimeOfDay = val)),
                  const SizedBox(height: 24),
                  
                  _buildSectionTitle('Cuisine Preferences'),
                  _buildMultiSelectChips(cuisines, _selectedCuisines),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
          
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: () {
                Navigator.pop(context, {
                  'location': _locationController.text.trim().isEmpty ? null : _locationController.text.trim(),
                  'vibe': _selectedVibe,
                  'socialContext': _selectedSocialContext,
                  'timeOfDay': _selectedTimeOfDay,
                  'cuisines': _selectedCuisines,
                });
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: PlanditColors.foreground,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 0,
              ),
              child: Text(
                'Apply Filters',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          SizedBox(height: MediaQuery.of(context).padding.bottom),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title.toUpperCase(),
      style: GoogleFonts.inter(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 1.2,
        color: PlanditColors.mutedForeground.withOpacity(0.8),
      ),
    );
  }

  Widget _buildChips(List<String> options, String? selected, Function(String?) onSelected) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: options.map((option) {
          final isSelected = selected == option;
          return GestureDetector(
            onTap: () => onSelected(isSelected ? null : option),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isSelected ? PlanditColors.accent : PlanditColors.secondary.withOpacity(0.5),
                borderRadius: BorderRadius.circular(100),
                border: Border.all(
                  color: isSelected ? PlanditColors.accent : PlanditColors.border.withOpacity(0.5),
                ),
              ),
              child: Text(
                option,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected ? Colors.white : PlanditColors.foreground,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildMultiSelectChips(List<String> options, List<String> selected) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: options.map((option) {
          final isSelected = selected.contains(option);
          return GestureDetector(
            onTap: () {
              setState(() {
                if (isSelected) {
                  selected.remove(option);
                } else {
                  selected.add(option);
                }
              });
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isSelected ? PlanditColors.accent : PlanditColors.secondary.withOpacity(0.5),
                borderRadius: BorderRadius.circular(100),
                border: Border.all(
                  color: isSelected ? PlanditColors.accent : PlanditColors.border.withOpacity(0.5),
                ),
              ),
              child: Text(
                option,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected ? Colors.white : PlanditColors.foreground,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
