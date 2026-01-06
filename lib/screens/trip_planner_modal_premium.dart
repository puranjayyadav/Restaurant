import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../api_service.dart';

// ---------------------------------------------------------
// THE PREMIUM THEME CONSTANTS ("Stone & Forest" Theme)
// ---------------------------------------------------------
class PremiumAppColors {
  static const Color background = Color(0xFFFDFCF8); // Warm Stone White
  static const Color primaryGreen = Color(0xFF2D6A4F); // Deep Forest Green
  static const Color textPrimary = Color(0xFF1B1B1B); // Soft black
  static const Color textSecondary = Color(0xFF8D8D8D); // Warm grey
  static const Color inputFill = Color(0xFFF4F4F4); // Light grey
  static const Color borderOutline = Color(0xFFE0E0E0); // Border color
}

// ---------------------------------------------------------
// THE MAIN PREMIUM WIZARD MODAL WIDGET
// ---------------------------------------------------------
class TripPlannerModalPremium extends StatefulWidget {
  const TripPlannerModalPremium({super.key});

  @override
  State<TripPlannerModalPremium> createState() => _TripPlannerModalPremiumState();
}

class _TripPlannerModalPremiumState extends State<TripPlannerModalPremium> {
  // State for the inputs
  String selectedWho = 'Couple';
  final List<String> selectedVibes = ['Hidden Gems', 'Foodie'];
  String _destination = '';
  DateTime? _startDate;
  DateTime? _endDate;
  bool _isLoading = false;
  String? _errorMessage;

  final TextEditingController _destinationController = TextEditingController();

  // Data Options
  final List<String> whoOptions = ['Solo', 'Couple', 'Group'];
  final List<Map<String, String>> vibeOptions = [
    {'label': 'Hidden Gems', 'emoji': '💎'},
    {'label': 'Foodie', 'emoji': '🍽'},
    {'label': 'Architecture', 'emoji': '🏛'},
    {'label': 'Relaxed', 'emoji': '🍃'},
    {'label': 'Adventure', 'emoji': '🧗'},
    {'label': 'Nightlife', 'emoji': '🍸'},
  ];

  @override
  void dispose() {
    _destinationController.dispose();
    super.dispose();
  }

  Future<void> _selectDateRange(BuildContext context) async {
    final initialDateRange = _startDate != null && _endDate != null
        ? DateTimeRange(start: _startDate!, end: _endDate!)
        : null;

    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime.now(),
      lastDate: DateTime(2101),
      initialDateRange: initialDateRange,
      builder: (context, child) {
        return Theme(
          data: ThemeData.light().copyWith(
            colorScheme: const ColorScheme.light(
              primary: PremiumAppColors.primaryGreen,
              onPrimary: Colors.white,
              surface: PremiumAppColors.background,
              onSurface: PremiumAppColors.textPrimary,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null && picked != initialDateRange) {
      setState(() {
        _startDate = picked.start;
        _endDate = picked.end;
      });
    }
  }

  void _toggleVibe(String vibe) {
    setState(() {
      if (selectedVibes.contains(vibe)) {
        selectedVibes.remove(vibe);
      } else {
        selectedVibes.add(vibe);
      }
    });
  }

  String _formatDateRange() {
    if (_startDate == null || _endDate == null) {
      return 'Select dates';
    }
    final months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    return '${months[_startDate!.month - 1]} ${_startDate!.day} - ${_endDate!.day}';
  }

  Future<void> _generateItinerary() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    _destination = _destinationController.text.trim();

    if (_destination.isEmpty || _startDate == null || _endDate == null || selectedVibes.isEmpty) {
      setState(() {
        _errorMessage = 'Please fill all required fields.';
        _isLoading = false;
      });
      return;
    }

    try {
      final apiService = ApiService();
      final newTripData = await apiService.createItinerarySkeleton(
        destination: _destination,
        startDate: _startDate!,
        endDate: _endDate!,
        groupSize: selectedWho,
        vibes: selectedVibes,
      );

      debugPrint('New Trip Created with ID: ${newTripData['itinerary_id']}');

      if (!mounted) return;
      Navigator.of(context).pop();
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to create trip: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.85, // Takes up 85% height
      decoration: const BoxDecoration(
        color: PremiumAppColors.background,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(32),
          topRight: Radius.circular(32),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 40,
            spreadRadius: 5,
          )
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // --- DRAG HANDLE ---
            Center(
              child: Container(
                width: 40,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
            const SizedBox(height: 24),
            
            // --- HEADER ---
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Plan Your Trip",
                  style: GoogleFonts.playfairDisplay( // Editorial Font
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: PremiumAppColors.textPrimary,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: PremiumAppColors.textSecondary),
                  onPressed: () => Navigator.pop(context),
                )
              ],
            ),
            const SizedBox(height: 32),

            // --- STEP 1: DESTINATION ---
            _buildSectionLabel("1) Where to?"),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: PremiumAppColors.inputFill,
                borderRadius: BorderRadius.circular(16),
              ),
              child: TextField(
                controller: _destinationController,
                style: GoogleFonts.dmSans(
                    fontSize: 16, color: PremiumAppColors.textPrimary, fontWeight: FontWeight.w500),
                decoration: InputDecoration(
                  prefixIcon: const Icon(Icons.search, color: PremiumAppColors.textSecondary),
                  hintText: "City, e.g. Chicago",
                  hintStyle: GoogleFonts.dmSans(color: PremiumAppColors.textSecondary),
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ),
            const SizedBox(height: 28),

            // --- STEP 2: CONTEXT ---
            _buildSectionLabel("2) When & Who?"),
            const SizedBox(height: 12),
            
            // Date Picker
            GestureDetector(
              onTap: () => _selectDateRange(context),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                decoration: BoxDecoration(
                  color: PremiumAppColors.inputFill,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.calendar_today_outlined,
                        size: 20, color: PremiumAppColors.textPrimary),
                    const SizedBox(width: 12),
                    Text(
                      _formatDateRange(),
                      style: GoogleFonts.dmSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: _startDate != null 
                            ? PremiumAppColors.textPrimary 
                            : PremiumAppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Who Selectors (Radio Pills)
            Row(
              children: whoOptions.map((option) {
                final isSelected = selectedWho == option;
                return GestureDetector(
                  onTap: () => setState(() => selectedWho = option),
                  child: Container(
                    margin: const EdgeInsets.only(right: 12),
                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                    child: Row(
                      children: [
                        // Custom Radio Circle
                        Container(
                          width: 20,
                          height: 20,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: isSelected ? PremiumAppColors.primaryGreen : PremiumAppColors.borderOutline,
                              width: 2,
                            ),
                            color: Colors.transparent,
                          ),
                          child: isSelected
                              ? Center(
                                  child: Container(
                                    width: 10,
                                    height: 10,
                                    decoration: const BoxDecoration(
                                      color: PremiumAppColors.primaryGreen,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                )
                              : null,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          option,
                          style: GoogleFonts.dmSans(
                            fontSize: 15,
                            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                            color: isSelected ? PremiumAppColors.textPrimary : PremiumAppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 28),

            // --- STEP 3: VIBES ---
            _buildSectionLabel("3) What's the Vibe?"),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: vibeOptions.map((vibe) {
                final isSelected = selectedVibes.contains(vibe['label']);
                return GestureDetector(
                  onTap: () => _toggleVibe(vibe['label']!),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: isSelected ? const Color.fromRGBO(45, 106, 79, 0.1) : Colors.white,
                      border: Border.all(
                        color: isSelected ? PremiumAppColors.primaryGreen : PremiumAppColors.borderOutline,
                        width: 1,
                      ),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: isSelected
                          ? []
                          : [
                              BoxShadow(
                                color: const Color.fromRGBO(0, 0, 0, 0.03),
                                blurRadius: 4,
                                offset: const Offset(0, 2),
                              )
                            ],
                    ),
                    child: Text(
                      "${vibe['emoji']} ${vibe['label']}",
                      style: GoogleFonts.dmSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: isSelected ? PremiumAppColors.primaryGreen : PremiumAppColors.textPrimary,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),

            const Spacer(),

            // --- ERROR MESSAGE ---
            if (_errorMessage != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _errorMessage!,
                  style: GoogleFonts.dmSans(
                    fontSize: 14,
                    color: const Color(0xFFE53935),
                  ),
                ),
              ),

            // --- GENERATE BUTTON ---
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _generateItinerary,
                style: ElevatedButton.styleFrom(
                  backgroundColor: PremiumAppColors.primaryGreen,
                  disabledBackgroundColor: const Color.fromRGBO(45, 106, 79, 0.5),
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(30),
                  ),
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : Text(
                        "Generate Itinerary",
                        style: GoogleFonts.dmSans(
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionLabel(String text) {
    return Text(
      text,
      style: GoogleFonts.dmSans(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: PremiumAppColors.textPrimary,
      ),
    );
  }
}

// ---------------------------------------------------------
// HELPER FUNCTION TO SHOW THE MODAL
// ---------------------------------------------------------
void showTripPlannerModalPremium(BuildContext context) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => const TripPlannerModalPremium(),
  );
}
