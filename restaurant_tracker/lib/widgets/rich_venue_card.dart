import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../api_service.dart';
import 'beautiful_snackbar.dart';

/// Helper function to render text with proper emoji support.
/// Splits text into emoji and non-emoji parts, rendering emojis with system font.
Widget _buildRichText(String text, TextStyle baseStyle) {
  if (text.isEmpty) return const SizedBox.shrink();

  // Repair potential double-encoding (mojibake) before processing
  final repairedText = _repairDoubleEncoding(text);

  // Regex to match emoji characters (simplified but covers most common emojis)
  final emojiRegex = RegExp(
    r'[\u{1F300}-\u{1F9FF}]|'  // Misc Symbols, Pictographs, Emoticons, etc.
    r'[\u{2600}-\u{26FF}]|'    // Misc Symbols
    r'[\u{2700}-\u{27BF}]|'    // Dingbats
    r'[\u{1F600}-\u{1F64F}]|'  // Emoticons
    r'[\u{1F680}-\u{1F6FF}]|'  // Transport & Map
    r'[\u{1F1E0}-\u{1F1FF}]',  // Flags
    unicode: true,
  );

  // Build list of TextSpans
  final List<InlineSpan> spans = [];
  int lastEnd = 0;

  for (final match in emojiRegex.allMatches(repairedText)) {
    // Add text before emoji (if any)
    if (match.start > lastEnd) {
      spans.add(TextSpan(
        text: repairedText.substring(lastEnd, match.start),
        style: baseStyle,
      ));
    }
    // Add emoji with system font (no fontFamily specified means system default)
    spans.add(TextSpan(
      text: match.group(0),
      style: TextStyle(
        fontSize: baseStyle.fontSize,
        height: baseStyle.height,
        // No fontFamily = system default which has emoji support
      ),
    ));
    lastEnd = match.end;
  }

  // Add remaining text after last emoji
  if (lastEnd < repairedText.length) {
    spans.add(TextSpan(
      text: repairedText.substring(lastEnd),
      style: baseStyle,
    ));
  }

  // If no emojis found, return simple Text widget with repaired text
  if (spans.isEmpty) {
    return Text(repairedText, style: baseStyle);
  }

  return Text.rich(
    TextSpan(children: spans),
  );
}

String _repairDoubleEncoding(String input) {
  if (input.isEmpty) return input;
  try {
    // Check if the string contains characters that are actually UTF-8 start bytes
    // interpreted as Latin-1 (e.g. 0xC2, 0xC3, 0xE2, 0xF0)
    bool hasMojibake = false;
    for (int i = 0; i < input.length; i++) {
      int unit = input.codeUnitAt(i);
      if (unit > 127) {
        hasMojibake = true;
        break;
      }
    }

    if (hasMojibake) {
      // Re-encode code units (interpreted as Latin-1 bytes) and decode as UTF-8
      final List<int> bytes = input.codeUnits;
      return utf8.decode(bytes);
    }
  } catch (_) {
    // If decoding fails, it wasn't actually double-encoded
  }
  return input;
}

/// Premium editorial-style venue card that displays rich venue data
class RichVenueCard extends StatefulWidget {
  final Map<String, dynamic> venue;
  final int stopNumber;
  final String? badgeLabel;

  const RichVenueCard({
    super.key,
    required this.venue,
    required this.stopNumber,
    this.badgeLabel,
  });

  @override
  State<RichVenueCard> createState() => _RichVenueCardState();
}

class _RichVenueCardState extends State<RichVenueCard> {
  final ApiService _apiService = ApiService();
  bool _isLoved = false;
  bool _isCheckingLoved = true;
  bool _isSeen = false;
  bool _isCheckingSeen = true;

  @override
  void initState() {
    super.initState();
    _checkIfLoved();
    _checkIfSeen();
  }

  Future<void> _checkIfLoved() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _isCheckingLoved = false;
        _isLoved = false;
      });
      return;
    }

    final placeId = widget.venue['place_id']?.toString();
    if (placeId == null || placeId.isEmpty) {
      setState(() {
        _isCheckingLoved = false;
        _isLoved = false;
      });
      return;
    }

    try {
      final isLoved = await _apiService.isPlaceLoved(user.uid, placeId);
      if (mounted) {
        setState(() {
          _isLoved = isLoved;
          _isCheckingLoved = false;
        });
      }
    } catch (e) {
      print('Error checking if place is loved: $e');
      if (mounted) {
        setState(() {
          _isCheckingLoved = false;
          _isLoved = false;
        });
      }
    }
  }

  Future<void> _checkIfSeen() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _isCheckingSeen = false;
        _isSeen = false;
      });
      return;
    }

    final placeId = widget.venue['place_id']?.toString();
    if (placeId == null || placeId.isEmpty) {
      setState(() {
        _isCheckingSeen = false;
        _isSeen = false;
      });
      return;
    }

    try {
      final isSeen = await _apiService.isPlaceSeen(user.uid, placeId);
      if (mounted) {
        setState(() {
          _isSeen = isSeen;
          _isCheckingSeen = false;
        });
      }
    } catch (e) {
      print('Error checking if place is seen: $e');
      if (mounted) {
        setState(() {
          _isCheckingSeen = false;
          _isSeen = false;
        });
      }
    }
  }

  Future<void> _toggleLove() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to save places')),
      );
      return;
    }

    final placeId = widget.venue['place_id']?.toString();
    if (placeId == null || placeId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Place ID not available')),
      );
      return;
    }

    final wasLoved = _isLoved;
    setState(() {
      _isLoved = !_isLoved; // Optimistic update
    });

    try {
      bool success;
      if (!wasLoved) {
        // Save to loved places
        success = await _apiService.lovePlace(
          userId: user.uid,
          placeId: placeId,
          name: widget.venue['name']?.toString() ?? 'Unknown',
          rating: (widget.venue['rating'] as num?)?.toDouble(),
          lat: (widget.venue['latitude'] as num?)?.toDouble(),
          lng: (widget.venue['longitude'] as num?)?.toDouble(),
        );
      } else {
        // Remove from loved places
        success = await _apiService.unlovePlace(user.uid, placeId);
      }

      if (mounted) {
        if (success) {
          // Show success message
          if (!wasLoved) {
            BeautifulSnackbar.showSuccess(
              context,
              'We saved your place! 💚',
            );
          } else {
            BeautifulSnackbar.showError(
              context,
              'Place removed from favorites',
            );
          }
        } else {
          // Revert on failure
          setState(() {
            _isLoved = wasLoved;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                  !wasLoved ? 'Failed to save place' : 'Failed to remove place'),
            ),
          );
        }
      }
    } catch (e) {
      print('Error toggling love: $e');
      if (mounted) {
        // Revert on error
        setState(() {
          _isLoved = wasLoved;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('An error occurred')),
        );
      }
    }
  }

  Future<void> _toggleSeen() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to mark places')),
      );
      return;
    }

    final placeId = widget.venue['place_id']?.toString();
    if (placeId == null || placeId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Place ID not available')),
      );
      return;
    }

    final wasSeen = _isSeen;
    setState(() {
      _isSeen = !_isSeen; // Optimistic update
    });

    try {
      bool success;
      if (!wasSeen) {
        // Mark as seen
        success = await _apiService.markPlaceAsSeen(
          userId: user.uid,
          placeId: placeId,
          name: widget.venue['name']?.toString() ?? 'Unknown',
          rating: (widget.venue['rating'] as num?)?.toDouble(),
          lat: (widget.venue['latitude'] as num?)?.toDouble(),
          lng: (widget.venue['longitude'] as num?)?.toDouble(),
        );
      } else {
        // Unmark as seen
        success = await _apiService.unmarkPlaceAsSeen(user.uid, placeId);
      }

      if (mounted) {
        if (success) {
          // Show success message
          if (!wasSeen) {
            BeautifulSnackbar.showSuccess(
              context,
              'Marked as seen! 👀',
            );
          } else {
            BeautifulSnackbar.showError(
              context,
              'Removed from seen places',
            );
          }
        } else {
          // Revert on failure
          setState(() {
            _isSeen = wasSeen;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                  !wasSeen ? 'Failed to mark as seen' : 'Failed to unmark as seen'),
            ),
          );
        }
      }
    } catch (e) {
      print('Error toggling seen: $e');
      if (mounted) {
        // Revert on error
        setState(() {
          _isSeen = wasSeen;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('An error occurred')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final richData = widget.venue['rich_data'] as Map<String, dynamic>?;

    // If no rich data, show basic card
    if (richData == null) {
      return _buildBasicCard();
    }

    final header = richData['display_header'] as Map<String, dynamic>?;
    final profile = richData['insider_profile'] as Map<String, dynamic>?;
    final benchmarks = richData['plandit_benchmarks'] as Map<String, dynamic>?;

    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 24,
            spreadRadius: 2,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
            // Stop number badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFFD4AF37).withOpacity(0.15),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                widget.badgeLabel ?? 'STOP ${widget.stopNumber}',
                style: GoogleFonts.mulish(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  color: const Color(0xFFD4AF37),
                ),
            ),
          ),

          const SizedBox(height: 16),

          // 1. HEADER: Title & Rating & Love Button
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _buildRichText(
                  header?['short_name']?.toString() ??
                      widget.venue['name']?.toString() ??
                      'Venue',
                  GoogleFonts.playfairDisplay(
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF1A1A1A),
                    height: 1.2,
                  ),
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Love button
                  IconButton(
                    icon: _isCheckingLoved
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Color(0xFF2D5016),
                            ),
                          )
                        : Icon(
                            _isLoved ? Icons.favorite : Icons.favorite_border,
                            color: _isLoved ? Colors.red : Colors.grey[600],
                            size: 24,
                          ),
                    onPressed: _toggleLove,
                    tooltip: _isLoved
                        ? 'Remove from loved places'
                        : 'Save to loved places',
                  ),
                  // Seen button
                  IconButton(
                    icon: _isCheckingSeen
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Color(0xFF2D5016),
                            ),
                          )
                        : Icon(
                            _isSeen ? Icons.visibility : Icons.visibility_outlined,
                            color: _isSeen ? Colors.blue : Colors.grey[600],
                            size: 24,
                          ),
                    onPressed: _toggleSeen,
                    tooltip: _isSeen ? 'Mark as unseen' : 'Mark as seen',
                  ),
                  // Rating
                  if (widget.venue['rating'] != null)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.amber.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(12),
                        border:
                            Border.all(color: Colors.amber.withOpacity(0.3)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.star, size: 14, color: Colors.amber),
                          const SizedBox(width: 4),
                          Text(
                            widget.venue['rating'].toString(),
                            style: GoogleFonts.mulish(
                              fontWeight: FontWeight.w700,
                              fontSize: 13,
                              color: const Color(0xFF1A1A1A),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ],
          ),

          const SizedBox(height: 12),

          // 2. VIBE TAGS (Horizontal Scroll or Wrap)
          if (profile != null && profile['vibe_tags'] != null)
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children:
                  (profile['vibe_tags'] as List).take(3).map<Widget>((tag) {
                return Text(
                  tag.toString().toUpperCase(),
                  style: GoogleFonts.mulish(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1,
                    color: Colors.grey[600],
                  ),
                );
              }).toList(),
            ),

          if (profile != null && profile['vibe_tags'] != null)
            const SizedBox(height: 16),

          // 3. THE HOOK (Editorial Touch)
          if (header?['hook'] != null && header!['hook'].toString().isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 20),
              child: Builder(
                builder: (context) {
                  final hookText = header['hook'].toString();
                  return _buildRichText(
                    hookText,
                    GoogleFonts.mulish(
                      fontSize: 18,
                      fontStyle: FontStyle.italic,
                      color: const Color(0xFF2D5016),
                      height: 1.4,
                    ),
                  );
                },
              ),
            ),

          // 4. INSIDER INTEL BOX (The "Meat")
          if (profile != null)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFFFAF9F6), // Warm off-white/cream
                border: Border.all(color: Colors.grey.withOpacity(0.15)),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Tidbit
                  if (profile['insider_tidbit'] != null)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: Colors.amber.withOpacity(0.2),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.lightbulb_outline,
                            size: 16,
                            color: Colors.amber,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _buildRichText(
                            profile['insider_tidbit'].toString(),
                            GoogleFonts.mulish(
                              fontSize: 14,
                              height: 1.6,
                              color: const Color(0xFF1A1A1A),
                            ),
                          ),
                        ),
                      ],
                    ),

                  if (profile['insider_tidbit'] != null &&
                      profile['must_order'] != null)
                    const SizedBox(height: 16),

                  if (profile['insider_tidbit'] != null &&
                      profile['must_order'] != null)
                    Divider(height: 1, color: Colors.grey[300]),

                  if (profile['must_order'] != null) const SizedBox(height: 16),

                  // Must Orders
                  if (profile['must_order'] != null)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'MUST ORDER',
                          style: GoogleFonts.mulish(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.2,
                            color: Colors.grey[600],
                          ),
                        ),
                        const SizedBox(height: 10),
                        ...(profile['must_order'] as List)
                            .take(3)
                            .map((item) => Padding(
                                  padding: const EdgeInsets.only(bottom: 6.0),
                                  child: Row(
                                    children: [
                                      Container(
                                        width: 4,
                                        height: 4,
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFD4AF37),
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: _buildRichText(
                                          item.toString(),
                                          GoogleFonts.mulish(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w500,
                                            color: const Color(0xFF1A1A1A),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                )),
                      ],
                    ),
                ],
              ),
            ),

          if (benchmarks != null || profile?['ideal_occasion'] != null)
            const SizedBox(height: 20),

          // 5. BENCHMARKS ROW (Quick Scan)
          if (benchmarks != null || profile?['ideal_occasion'] != null)
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  if (benchmarks?['noise_level'] != null)
                    _buildBenchmarkChip(
                      Icons.volume_up,
                      benchmarks!['noise_level'].toString(),
                    ),
                  if (benchmarks?['work_friendly'] == true)
                    _buildBenchmarkChip(Icons.laptop, 'Laptop Friendly'),
                  if (benchmarks?['date_night_score'] == true)
                    _buildBenchmarkChip(Icons.favorite, 'Date Spot'),
                  if (benchmarks?['grandma_approval'] == true)
                    _buildBenchmarkChip(
                        Icons.family_restroom, 'Family Friendly'),
                  if (profile?['ideal_occasion'] != null)
                    _buildBenchmarkChip(
                      Icons.event,
                      profile!['ideal_occasion'].toString(),
                      isHighlight: true,
                    ),
                ],
              ),
            ),

          // Warning label if trap
          if (benchmarks?['is_trap'] == true)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.orange.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber,
                        size: 16, color: Colors.orange),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Tourist Trap Alert',
                        style: GoogleFonts.mulish(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: Colors.orange[800],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // Action buttons: Phone, Website, Maps
          if (widget.venue['phone'] != null ||
              widget.venue['website'] != null ||
              (widget.venue['latitude'] != null &&
                  widget.venue['longitude'] != null))
            Padding(
              padding: const EdgeInsets.only(top: 20),
              child: Column(
                children: [
                  // Phone and Website in a row if both available
                  if (widget.venue['phone'] != null ||
                      widget.venue['website'] != null)
                    Row(
                      children: [
                        if (widget.venue['phone'] != null)
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _launchPhone(
                                widget.venue['phone']?.toString(),
                              ),
                              icon: const Icon(Icons.phone, size: 18),
                              label: Text(
                                'Call',
                                style: GoogleFonts.mulish(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF2D5016),
                                side: const BorderSide(
                                    color: Color(0xFF2D5016), width: 1.5),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                        if (widget.venue['phone'] != null &&
                            widget.venue['website'] != null)
                          const SizedBox(width: 12),
                        if (widget.venue['website'] != null)
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _launchWebsite(
                                widget.venue['website']?.toString(),
                              ),
                              icon: const Icon(Icons.language, size: 18),
                              label: Text(
                                'Website',
                                style: GoogleFonts.mulish(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF2D5016),
                                side: const BorderSide(
                                    color: Color(0xFF2D5016), width: 1.5),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  // Maps button (full width)
                  if (widget.venue['latitude'] != null &&
                      widget.venue['longitude'] != null)
                    Padding(
                      padding: EdgeInsets.only(
                        top: (widget.venue['phone'] != null ||
                                widget.venue['website'] != null)
                            ? 12
                            : 0,
                      ),
                      child: SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () => _openInGoogleMaps(
                            (widget.venue['latitude'] as num).toDouble(),
                            (widget.venue['longitude'] as num).toDouble(),
                            widget.venue['name']?.toString() ?? 'Location',
                          ),
                          icon: const Icon(Icons.map, size: 18),
                          label: Text(
                            'View on Maps',
                            style: GoogleFonts.mulish(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF2D5016),
                            side: const BorderSide(
                                color: Color(0xFF2D5016), width: 1.5),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _launchPhone(String? phoneNumber) async {
    if (phoneNumber == null || phoneNumber.isEmpty) {
      print('No phone number available');
      return;
    }

    // Clean phone number (remove spaces, dashes, etc.)
    final cleanPhone = phoneNumber.replaceAll(RegExp(r'[^\d+]'), '');
    final phoneUri = Uri.parse('tel:$cleanPhone');

    try {
      if (await canLaunchUrl(phoneUri)) {
        await launchUrl(phoneUri);
      } else {
        print('Cannot launch phone: $phoneUri');
      }
    } catch (e) {
      print('Error launching phone: $e');
    }
  }

  Future<void> _launchWebsite(String? website) async {
    if (website == null || website.isEmpty) {
      print('No website available');
      return;
    }

    // Ensure website has http:// or https://
    String url = website;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://$url';
    }

    final websiteUri = Uri.parse(url);

    try {
      if (await canLaunchUrl(websiteUri)) {
        await launchUrl(websiteUri, mode: LaunchMode.externalApplication);
      } else {
        print('Cannot launch website: $websiteUri');
      }
    } catch (e) {
      print('Error launching website: $e');
    }
  }

  Future<void> _openInGoogleMaps(
      double latitude, double longitude, String name) async {
    try {
      final placeId = widget.venue['place_id']?.toString();

      // Build search query with name and address
      final venueName = widget.venue['name']?.toString() ?? name;
      final venueAddress = widget.venue['address']?.toString() ?? '';

      // Combine name and address for search query
      String searchQuery = venueName;
      if (venueAddress.isNotEmpty) {
        searchQuery = '$venueName, $venueAddress';
      }
      final encodedQuery = Uri.encodeComponent(searchQuery);

      // Try Google Maps search URL with name and address (best for user experience)
      try {
        final searchUrl = Uri.parse(
            'https://www.google.com/maps/search/?api=1&query=$encodedQuery');
        final canLaunchSearch = await canLaunchUrl(searchUrl);
        print('Can launch search URL: $canLaunchSearch');

        if (canLaunchSearch) {
          await launchUrl(searchUrl, mode: LaunchMode.externalApplication);
          return;
        }
      } catch (e) {
        print('Search URL failed: $e');
      }

      // Fallback to Google Maps URL with place_id if available
      if (placeId != null && placeId.isNotEmpty) {
        try {
          final placeUrl = Uri.parse(
              'https://www.google.com/maps/search/?api=1&query=$encodedQuery&query_place_id=$placeId');
          final canLaunchPlace = await canLaunchUrl(placeUrl);
          print('Can launch place URL: $canLaunchPlace');

          if (canLaunchPlace) {
            await launchUrl(placeUrl, mode: LaunchMode.externalApplication);
            return;
          }
        } catch (e) {
          print('Place URL failed: $e');
        }
      }

      // Fallback to geo: URI scheme with name
      try {
        final geoUri = Uri.parse(
            'geo:$latitude,$longitude?q=$latitude,$longitude(${Uri.encodeComponent(searchQuery)})');
        final canLaunchGeo = await canLaunchUrl(geoUri);
        print('Can launch geo URI: $canLaunchGeo');

        if (canLaunchGeo) {
          await launchUrl(geoUri, mode: LaunchMode.externalApplication);
          return;
        }
      } catch (e) {
        print('Geo URI failed: $e');
      }

      // Fallback to coordinates with search query
      try {
        final coordsUrl = Uri.parse(
            'https://www.google.com/maps/search/?api=1&query=$encodedQuery');
        final canLaunchCoords = await canLaunchUrl(coordsUrl);
        print('Can launch coords URL: $canLaunchCoords');

        if (canLaunchCoords) {
          await launchUrl(coordsUrl, mode: LaunchMode.externalApplication);
          return;
        }
      } catch (e) {
        print('Coords URL failed: $e');
      }

      // Last resort: open in browser with search query
      try {
        final webUrl =
            Uri.parse('https://www.google.com/maps/search/?q=$encodedQuery');
        await launchUrl(webUrl, mode: LaunchMode.platformDefault);
      } catch (e) {
        print('All URL attempts failed: $e');
      }
    } catch (e) {
      print('Error opening Google Maps: $e');
    }
  }

  Widget _buildBasicCard() {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 24,
            spreadRadius: 2,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFFD4AF37).withOpacity(0.15),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                widget.badgeLabel ?? 'STOP ${widget.stopNumber}',
                style: GoogleFonts.mulish(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  color: const Color(0xFFD4AF37),
                ),
            ),
          ),
          const SizedBox(height: 16),
          // Title with love button
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _buildRichText(
                  widget.venue['name']?.toString() ?? 'Venue',
                  GoogleFonts.playfairDisplay(
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF1A1A1A),
                    height: 1.2,
                  ),
                ),
              ),
              // Love button
              IconButton(
                icon: _isCheckingLoved
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Color(0xFF2D5016),
                        ),
                      )
                    : Icon(
                        _isLoved ? Icons.favorite : Icons.favorite_border,
                        color: _isLoved ? Colors.red : Colors.grey[600],
                        size: 24,
                      ),
                onPressed: _toggleLove,
                tooltip: _isLoved
                    ? 'Remove from loved places'
                    : 'Save to loved places',
              ),
              // Seen button
              IconButton(
                icon: _isCheckingSeen
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Color(0xFF2D5016),
                        ),
                      )
                    : Icon(
                        _isSeen ? Icons.visibility : Icons.visibility_outlined,
                        color: _isSeen ? Colors.blue : Colors.grey[600],
                        size: 24,
                      ),
                onPressed: _toggleSeen,
                tooltip: _isSeen ? 'Mark as unseen' : 'Mark as seen',
              ),
            ],
          ),
          if (widget.venue['address'] != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                widget.venue['address'].toString(),
                style: GoogleFonts.mulish(
                  fontSize: 13,
                  color: Colors.grey[600],
                ),
              ),
            ),

          // Action buttons: Phone, Website, Maps
          if (widget.venue['phone'] != null ||
              widget.venue['website'] != null ||
              (widget.venue['latitude'] != null &&
                  widget.venue['longitude'] != null))
            Padding(
              padding: const EdgeInsets.only(top: 20),
              child: Column(
                children: [
                  // Phone and Website in a row if both available
                  if (widget.venue['phone'] != null ||
                      widget.venue['website'] != null)
                    Row(
                      children: [
                        if (widget.venue['phone'] != null)
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _launchPhone(
                                widget.venue['phone']?.toString(),
                              ),
                              icon: const Icon(Icons.phone, size: 18),
                              label: Text(
                                'Call',
                                style: GoogleFonts.mulish(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF2D5016),
                                side: const BorderSide(
                                    color: Color(0xFF2D5016), width: 1.5),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                        if (widget.venue['phone'] != null &&
                            widget.venue['website'] != null)
                          const SizedBox(width: 12),
                        if (widget.venue['website'] != null)
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _launchWebsite(
                                widget.venue['website']?.toString(),
                              ),
                              icon: const Icon(Icons.language, size: 18),
                              label: Text(
                                'Website',
                                style: GoogleFonts.mulish(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF2D5016),
                                side: const BorderSide(
                                    color: Color(0xFF2D5016), width: 1.5),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  // Maps button (full width)
                  if (widget.venue['latitude'] != null &&
                      widget.venue['longitude'] != null)
                    Padding(
                      padding: EdgeInsets.only(
                        top: (widget.venue['phone'] != null ||
                                widget.venue['website'] != null)
                            ? 12
                            : 0,
                      ),
                      child: SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () => _openInGoogleMaps(
                            (widget.venue['latitude'] as num).toDouble(),
                            (widget.venue['longitude'] as num).toDouble(),
                            widget.venue['name']?.toString() ?? 'Location',
                          ),
                          icon: const Icon(Icons.map, size: 18),
                          label: Text(
                            'View on Maps',
                            style: GoogleFonts.mulish(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF2D5016),
                            side: const BorderSide(
                                color: Color(0xFF2D5016), width: 1.5),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildBenchmarkChip(IconData icon, String label,
      {bool isHighlight = false}) {
    return Container(
      margin: const EdgeInsets.only(right: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isHighlight ? const Color(0xFF1A1A1A) : Colors.grey[100],
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isHighlight
              ? const Color(0xFF1A1A1A)
              : Colors.grey.withOpacity(0.2),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: isHighlight ? Colors.white : Colors.grey[700],
          ),
          const SizedBox(width: 6),
          _buildRichText(
            label,
            GoogleFonts.mulish(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: isHighlight ? Colors.white : Colors.grey[800],
            ),
          ),
        ],
      ),
    );
  }
}
