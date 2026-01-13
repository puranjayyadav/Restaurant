import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'itinerary_detail_screen.dart';
import '../api_service.dart';
import '../widgets/beautiful_snackbar.dart';

/// Premium "Begin the Journey" preview screen with timeline
class CuratedJourneyPreviewScreen extends StatefulWidget {
  final Map<String, dynamic> itinerary;
  final VoidCallback? onClose;

  const CuratedJourneyPreviewScreen({
    super.key,
    required this.itinerary,
    this.onClose,
  });

  @override
  State<CuratedJourneyPreviewScreen> createState() => _CuratedJourneyPreviewScreenState();
}

class _CuratedJourneyPreviewScreenState extends State<CuratedJourneyPreviewScreen> {
  final ApiService _apiService = ApiService();
  bool _isSaved = false;
  bool _isSaving = false;
  bool _isCheckingSaved = true;

  @override
  void initState() {
    super.initState();
    _checkIfSaved();
  }

  Future<void> _checkIfSaved() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _isCheckingSaved = false;
        _isSaved = false;
      });
      return;
    }

    final itineraryId = widget.itinerary['itinerary_id']?.toString();
    if (itineraryId == null || itineraryId.isEmpty) {
      setState(() {
        _isCheckingSaved = false;
        _isSaved = false;
      });
      return;
    }

    try {
      final isSaved = await _apiService.isItinerarySaved(user.uid, itineraryId);
      if (mounted) {
        setState(() {
          _isSaved = isSaved;
          _isCheckingSaved = false;
        });
      }
    } catch (e) {
      print('Error checking if itinerary is saved: $e');
      if (mounted) {
        setState(() {
          _isCheckingSaved = false;
          _isSaved = false;
        });
      }
    }
  }

  List<Map<String, dynamic>> get _stops {
    final data = widget.itinerary['itinerary_data'];
    if (data is Map) {
      final list = data['itinerary'];
      if (list is List) {
        return list
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
            .toList();
      }
    }
    // Fallback to stops key if itinerary_data is missing
    final stops = widget.itinerary['stops'];
    if (stops is List) {
      return stops
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
          .toList();
    }
    // Also check if itinerary is directly a list
    if (widget.itinerary['itinerary'] is List) {
      return (widget.itinerary['itinerary'] as List)
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e.cast<String, dynamic>()))
          .toList();
    }
    return const <Map<String, dynamic>>[];
  }

  String _title() =>
      widget.itinerary['new_title']?.toString() ??
      widget.itinerary['title']?.toString() ??
      'Your Curated Journey';

  String _subtitle() {
    final subtitle = widget.itinerary['subtitle']?.toString().trim();
    if (subtitle != null && subtitle.isNotEmpty) {
      return subtitle;
    }
    // Try to extract neighborhood or area from title
    final title = _title().toLowerCase();
    if (title.contains('west village')) return 'A Morning in the West Village';
    if (title.contains('brooklyn')) return 'A Day in Brooklyn';
    if (title.contains('soho')) return 'Exploring SoHo';
    return 'Your Personalized Experience';
  }

  String _description() {
    final desc = widget.itinerary['description']?.toString().trim();
    if (desc != null && desc.isNotEmpty) {
      return desc;
    }
    return 'An experience curated just for you, designed to unfold like the best stories do...';
  }

  String _getStopName(Map<String, dynamic> stop) {
    return stop['name']?.toString() ??
        stop['stop_name']?.toString() ??
        stop['title']?.toString() ??
        'Unnamed Stop';
  }

  String _getStopCategory(Map<String, dynamic> stop) {
    return stop['category']?.toString() ?? 'Place';
  }

  String _getEstimatedTime(int index) {
    // Start at 9:00 AM and add 1.5 hours per stop
    final baseHour = 9;
    final baseMinute = 0;
    final hoursToAdd = (index * 1.5).round();
    final totalMinutes = baseMinute + (hoursToAdd * 60);
    final hour = (baseHour + (totalMinutes ~/ 60)) % 12;
    final minute = totalMinutes % 60;
    final period = (baseHour + (totalMinutes ~/ 60)) >= 12 ? 'PM' : 'AM';
    final displayHour = hour == 0 ? 12 : hour;
    return '$displayHour:${minute.toString().padLeft(2, '0')} $period';
  }

  void _beginJourney(BuildContext context) {
    // Navigate directly to ItineraryDetailScreen
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (context) => ItineraryDetailScreen(itinerary: widget.itinerary),
      ),
    );
  }

  String _getFormattedDateTime() {
    try {
      final now = DateTime.now();
      return DateFormat('EEEE, MMM d').format(now);
    } catch (e) {
      return 'Today';
    }
  }

  Future<void> _saveItinerary() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to save itineraries')),
      );
      return;
    }

    if (_isSaving) return;

    final wasSaved = _isSaved;
    setState(() {
      _isSaving = true;
    });

    final itineraryId = widget.itinerary['itinerary_id']?.toString();
    bool success = false;

    if (!wasSaved) {
      // Save the itinerary
      // Save to user list (existing functionality)
      final result = await _apiService.saveItineraryToUserList(
        userId: user.uid,
        title: _title(),
        subtitle: _subtitle(),
        description: _description(),
        itineraryData: widget.itinerary,
      );

      // Also save to user_saved_itineraries for tracking popular itineraries
      if (itineraryId != null && itineraryId.isNotEmpty) {
        final stops = _stops;
        final narrative = widget.itinerary['narrative']?.toString() ?? 
                         widget.itinerary['itinerary_data']?['narrative']?.toString();
        final totalWalkTimeMins = widget.itinerary['total_walk_time_mins'] as int? ??
                                 widget.itinerary['itinerary_data']?['total_walk_time_mins'] as int?;
        final filters = widget.itinerary['filters'] as Map<String, dynamic>? ??
                        widget.itinerary['itinerary_data']?['filters'] as Map<String, dynamic>?;

        // Convert stops to the format expected by saveItineraryToUserSaved
        final places = stops.map((stop) {
          return {
            'place_id': stop['place_id']?.toString(),
            'name': stop['name']?.toString() ?? stop['place_name']?.toString(),
            'address': stop['address']?.toString(),
            'latitude': stop['latitude'],
            'longitude': stop['longitude'],
            'rating': stop['rating'],
            'slot': stop['slot']?.toString() ?? stop['slot_name']?.toString(),
            'time': stop['time']?.toString() ?? stop['start_time']?.toString(),
          };
        }).toList();

        try {
          final savedSuccess = await _apiService.saveItineraryToUserSaved(
            userId: user.uid,
            itineraryId: itineraryId,
            places: places,
            narrative: narrative,
            totalWalkTimeMins: totalWalkTimeMins,
            filters: filters,
          );
          success = result != null && savedSuccess;
          print('DEBUG: Saved itinerary to user_saved_itineraries with ID: $itineraryId');
        } catch (e) {
          print('WARNING: Failed to save to user_saved_itineraries: $e');
          success = result != null; // Still consider it success if user list save worked
        }
      } else {
        print('WARNING: No itinerary_id found in itinerary data, skipping user_saved_itineraries save');
        success = result != null;
      }
    } else {
      // Unsave the itinerary
      if (itineraryId != null && itineraryId.isNotEmpty) {
        success = await _apiService.unsaveItinerary(user.uid, itineraryId);
      } else {
        success = false;
      }
    }

    if (mounted) {
      setState(() {
        _isSaving = false;
        if (success) {
          _isSaved = !wasSaved; // Toggle the state
        }
      });

      if (success) {
        if (!wasSaved) {
          BeautifulSnackbar.showSuccess(context, 'Itinerary saved successfully! 💚');
        } else {
          BeautifulSnackbar.showError(context, 'Itinerary removed from favorites');
        }
      } else {
        BeautifulSnackbar.showError(context, 
            !wasSaved ? 'Failed to save itinerary' : 'Failed to remove itinerary');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final stops = _stops;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 400),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.08),
                    blurRadius: 30,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header section
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'CURATED FOR YOU',
                              style: GoogleFonts.mulish(
                                fontSize: 10,
                                letterSpacing: 2,
                                fontWeight: FontWeight.w800,
                                color: const Color(0xFF666666),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _getFormattedDateTime(),
                              style: GoogleFonts.mulish(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: const Color(0xFF1A1A1A),
                              ),
                            ),
                          ],
                        ),
                        Row(
                          children: [
                            // Save button
                            GestureDetector(
                              onTap: (_isSaving || _isCheckingSaved) ? null : _saveItinerary,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 16, vertical: 8),
                                decoration: BoxDecoration(
                                  color: _isCheckingSaved
                                      ? Colors.grey[300]
                                      : _isSaved 
                                          ? const Color(0xFF2D5016) 
                                          : const Color(0xFFFFD700),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    (_isSaving || _isCheckingSaved)
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white,
                                            ),
                                          )
                                        : Icon(
                                            _isSaved 
                                                ? Icons.bookmark 
                                                : Icons.bookmark_border,
                                            color: Colors.white,
                                            size: 18,
                                          ),
                                    const SizedBox(width: 6),
                                    Text(
                                      _isCheckingSaved
                                          ? '...'
                                          : _isSaved 
                                              ? 'Saved' 
                                              : 'Save',
                                      style: GoogleFonts.mulish(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            // Close button
                            GestureDetector(
                              onTap: widget.onClose ?? () => Navigator.pop(context),
                              child: const Icon(
                                Icons.close,
                                color: Color(0xFF1A1A1A),
                                size: 24,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  // Content
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Title
                        Text(
                          _title(),
                          style: GoogleFonts.playfairDisplay(
                            fontSize: 32,
                            fontWeight: FontWeight.w600,
                            color: const Color(0xFF1A1A1A),
                            height: 1.2,
                          ),
                        ),
                        const SizedBox(height: 8),
                        // Subtitle
                        Text(
                          _subtitle(),
                          style: GoogleFonts.mulish(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                            color: const Color(0xFF666666),
                          ),
                        ),
                        const SizedBox(height: 16),
                        // Description
                        Text(
                          _description(),
                          style: GoogleFonts.mulish(
                            fontSize: 16,
                            color: const Color(0xFF444444),
                            height: 1.6,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                        const SizedBox(height: 32),
                        // Timeline Header
                        Text(
                          'Your Journey',
                          style: GoogleFonts.mulish(
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: const Color(0xFF1A1A1A),
                          ),
                        ),
                        const SizedBox(height: 20),
                        // Timeline List
                        if (stops.isEmpty)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: Text(
                              'No stops available',
                              style: TextStyle(
                                color: Colors.grey[600],
                                fontSize: 14,
                              ),
                            ),
                          )
                        else
                          ...stops.asMap().entries.map((entry) {
                            final index = entry.key;
                            final stop = entry.value;
                            final isLast = index == stops.length - 1;

                            return IntrinsicHeight(
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  // Left column: Time and Timeline
                                  SizedBox(
                                    width: 70,
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          _getEstimatedTime(index),
                                          style: GoogleFonts.mulish(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w600,
                                            color: const Color(0xFF666666),
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        // Timeline dot and line
                                        Stack(
                                          alignment: Alignment.center,
                                          children: [
                                            Container(
                                              width: 2,
                                              height: 20,
                                              color: isLast
                                                  ? Colors.transparent
                                                  : Colors.grey[300],
                                            ),
                                            Container(
                                              width: 10,
                                              height: 10,
                                              decoration: const BoxDecoration(
                                                shape: BoxShape.circle,
                                                color: Color(0xFF1A1A1A),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  // Right column: Stop info
                                  Expanded(
                                    child: Padding(
                                      padding: const EdgeInsets.only(bottom: 20),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            _getStopName(stop),
                                            style: GoogleFonts.mulish(
                                              fontSize: 16,
                                              fontWeight: FontWeight.w700,
                                              color: const Color(0xFF1A1A1A),
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            _getStopCategory(stop),
                                            style: GoogleFonts.mulish(
                                              fontSize: 14,
                                              color: const Color(0xFF666666),
                                              fontWeight: FontWeight.w400,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }).toList(),
                        const SizedBox(height: 32),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      // Floating Action Button
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Container(
          width: double.infinity,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(30),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF2D5016).withOpacity(0.4),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: ElevatedButton(
            onPressed: () => _beginJourney(context),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF2D5016),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 20),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(30),
              ),
              elevation: 0,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'BEGIN THE JOURNEY',
                  style: GoogleFonts.mulish(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(width: 10),
                const Icon(Icons.arrow_forward_rounded, size: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
