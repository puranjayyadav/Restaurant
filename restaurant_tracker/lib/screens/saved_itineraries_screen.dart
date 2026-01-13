import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:share_plus/share_plus.dart';
import 'package:add_2_calendar/add_2_calendar.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../theme/design_system.dart';
import 'package:intl/intl.dart';
import '../scout_mode_screen.dart';
import 'loved_places_screen.dart';
import 'submit_itinerary_screen.dart';

class SavedItinerariesScreen extends StatelessWidget {
  const SavedItinerariesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;

    if (user == null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: Text(
            'SAVED',
            style: GoogleFonts.inter(
              color: PlanditColors.primaryText,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
        ),
        body: Center(
          child: Text('Please sign in to view saved items'),
        ),
      );
    }

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: PlanditColors.background,
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 0,
          title: Text(
            'SAVED',
            style: GoogleFonts.inter(
              color: PlanditColors.primaryText,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
          centerTitle: true,
          bottom: TabBar(
            indicatorColor: PlanditColors.accentGold,
            labelColor: PlanditColors.primaryText,
            unselectedLabelColor: PlanditColors.secondaryText,
            labelStyle: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 1),
            tabs: const [
              Tab(text: "DAY PLANS"),
              Tab(text: "LOVED SPOTS"),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _buildItinerariesList(user),
            const LovedPlacesScreen(),
          ],
        ),
      ),
    );
  }

  Widget _buildItinerariesList(User user) {
    return StreamBuilder<QuerySnapshot>(
      stream: FirebaseFirestore.instance
          .collection('saved_itineraries')
          .where('user_id', isEqualTo: user.uid)
          .orderBy('created_at', descending: true)
          .snapshots(),
        builder: (context, snapshot) {
          // Debug logging
          print(
              'DEBUG SavedItineraries: ConnectionState = ${snapshot.connectionState}');
          print('DEBUG SavedItineraries: HasError = ${snapshot.hasError}');
          if (snapshot.hasError) {
            print('DEBUG SavedItineraries: Error = ${snapshot.error}');
          }
          print('DEBUG SavedItineraries: HasData = ${snapshot.hasData}');
          if (snapshot.hasData) {
            print(
                'DEBUG SavedItineraries: Docs count = ${snapshot.data!.docs.length}');
          }

          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
              ),
            );
          }

          // Show error message if there's an error
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.xl),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.error_outline,
                      size: 64,
                      color: AppColors.error,
                    ),
                    SizedBox(height: AppSpacing.lg),
                    Text(
                      'Error loading itineraries',
                      style: TextStyle(
                        fontSize: AppTypography.titleMedium,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    SizedBox(height: AppSpacing.sm),
                    Text(
                      '${snapshot.error}',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: AppTypography.bodySmall,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }

          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    padding: EdgeInsets.all(AppSpacing.xl),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.bookmark_outline,
                      size: 64,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  SizedBox(height: AppSpacing.lg),
                  Text(
                    'No saved itineraries yet',
                    style: TextStyle(
                      fontSize: AppTypography.titleMedium,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  SizedBox(height: AppSpacing.sm),
                  Text(
                    'Save your favorite day plans to revisit them later',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: AppTypography.bodyMedium,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: EdgeInsets.all(AppSpacing.md),
            itemCount: snapshot.data!.docs.length,
            itemBuilder: (context, index) {
              final doc = snapshot.data!.docs[index];
              final data = doc.data() as Map<String, dynamic>;
              return _ExpandableItineraryCard(
                data: data,
                docId: doc.id,
              );
            },
          );
        },
      );
  }
}

class _ExpandableItineraryCard extends StatefulWidget {
  final Map<String, dynamic> data;
  final String docId;

  const _ExpandableItineraryCard({
    required this.data,
    required this.docId,
  });

  @override
  State<_ExpandableItineraryCard> createState() =>
      _ExpandableItineraryCardState();
}

class _ExpandableItineraryCardState extends State<_ExpandableItineraryCard> {
  bool isExpanded = false;

  // Color scheme for time slots
  static const slotColors = {
    'morning': Color(0xFFFDB462), // Warm yellow
    'mid_day': Color(0xFFE07A5F), // Coral
    'afternoon': Color(0xFF81B29A), // Sage green
    'evening': Color(0xFF7B68A6), // Purple
    'custom': AppColors.accent, // Gold
  };

  Color _getSlotColor(String slotName) {
    return slotColors[slotName.toLowerCase()] ?? AppColors.primary;
  }

  Future<void> _navigateToItinerary(BuildContext context) async {
    final items = widget.data['items'] as List<dynamic>? ?? [];
    final categories =
        (widget.data['categories'] as List<dynamic>?)?.cast<String>() ?? [];

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ScoutModeScreen(
          selectedCategories: categories,
          initialItinerary: items,
          isLoadingSavedItinerary: true,
        ),
      ),
    );
  }

  Future<void> _editItinerary(BuildContext context) async {
    final items = widget.data['items'] as List<dynamic>? ?? [];
    final categories =
        (widget.data['categories'] as List<dynamic>?)?.cast<String>() ?? [];

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ScoutModeScreen(
          selectedCategories: categories,
          initialItinerary: items,
          isEditMode: true,
          editDocId: widget.docId,
          isLoadingSavedItinerary: true,
        ),
      ),
    );
  }

  Future<void> _duplicateItinerary(BuildContext context) async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return;

      await FirebaseFirestore.instance.collection('saved_itineraries').add({
        ...widget.data,
        'user_id': user.uid,
        'created_at': FieldValue.serverTimestamp(),
      });

      if (!context.mounted) return;
      ShadToaster.of(context).show(
        const ShadToast(
          title: Text('Itinerary duplicated'),
          description: Text('A copy has been created'),
        ),
      );
    } catch (e) {
      if (!context.mounted) return;
      ShadToaster.of(context).show(
        ShadToast.destructive(
          title: const Text('Failed to duplicate'),
          description: Text(e.toString()),
        ),
      );
    }
  }

  Future<void> _shareItinerary(BuildContext context) async {
    final items = widget.data['items'] as List<dynamic>? ?? [];
    final location = widget.data['location'] as String? ?? 'Unknown location';

    final StringBuffer text = StringBuffer();
    text.writeln('My Day Plan - $location');
    text.writeln('');

    for (var item in items) {
      text.writeln('${item['start_time']}: ${item['place_name']}');
      if (item['address'] != null && item['address'] != '') {
        text.writeln('  📍 ${item['address']}');
      }
      text.writeln('');
    }

    await Share.share(text.toString(), subject: 'My Day Plan');
  }

  Future<void> _exportToCalendar(BuildContext context) async {
    try {
      final items = widget.data['items'] as List<dynamic>? ?? [];
      final baseDate = DateTime.now();

      for (var item in items) {
        final startTime = _parseTimeSlot(item['start_time'] ?? '', baseDate);
        final event = Event(
          title: item['place_name'] ?? 'Place',
          description: item['address'] ?? '',
          location: item['address'] ?? '',
          startDate: startTime,
          endDate: startTime.add(const Duration(hours: 1)),
        );

        await Add2Calendar.addEvent2Cal(event);
      }

      if (!context.mounted) return;
      ShadToaster.of(context).show(
        const ShadToast(
          title: Text('Added to calendar'),
          description: Text('Events have been created'),
        ),
      );
    } catch (e) {
      if (!context.mounted) return;
      ShadToaster.of(context).show(
        ShadToast.destructive(
          title: const Text('Failed to export'),
          description: Text(e.toString()),
        ),
      );
    }
  }

  DateTime _parseTimeSlot(String timeStr, DateTime baseDate) {
    // Extract hour if present (e.g., "09:00 Morning" -> 9)
    final timeRegex = RegExp(r'(\d{1,2}):(\d{2})');
    final match = timeRegex.firstMatch(timeStr);

    if (match != null) {
      final hour = int.parse(match.group(1)!);
      final minute = int.parse(match.group(2)!);
      return DateTime(
          baseDate.year, baseDate.month, baseDate.day, hour, minute);
    }

    // Default times based on slot name
    if (timeStr.toLowerCase().contains('morning')) {
      return DateTime(baseDate.year, baseDate.month, baseDate.day, 9, 0);
    } else if (timeStr.toLowerCase().contains('mid')) {
      return DateTime(baseDate.year, baseDate.month, baseDate.day, 12, 0);
    } else if (timeStr.toLowerCase().contains('afternoon')) {
      return DateTime(baseDate.year, baseDate.month, baseDate.day, 15, 0);
    } else if (timeStr.toLowerCase().contains('evening')) {
      return DateTime(baseDate.year, baseDate.month, baseDate.day, 18, 0);
    }

    return baseDate;
  }

  Future<void> _submitToPublic(BuildContext context) async {
    final items = widget.data['items'] as List<dynamic>? ?? [];
    final location = widget.data['location'] as String? ?? 'Unknown location';
    final neighborhood = widget.data['neighborhood'] as String? ?? 'Local area';
    final categories =
        (widget.data['categories'] as List<dynamic>?)?.cast<String>() ?? [];

    // Get coordinates from first item if available
    double latitude = 0.0;
    double longitude = 0.0;
    if (items.isNotEmpty) {
      latitude = (items[0]['latitude'] as num?)?.toDouble() ?? 0.0;
      longitude = (items[0]['longitude'] as num?)?.toDouble() ?? 0.0;
    }

    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => SubmitItineraryScreen(
          itinerary: items,
          location: location,
          neighborhood: neighborhood,
          latitude: latitude,
          longitude: longitude,
          categories: categories,
        ),
      ),
    );

    if (result == true && context.mounted) {
      ShadToaster.of(context).show(
        const ShadToast(
          title: Text('Success!'),
          description: Text('Your itinerary has been submitted for approval'),
        ),
      );
    }
  }

  Future<void> _deleteItinerary(BuildContext context) async {
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Itinerary'),
        content: const Text('Are you sure you want to delete this itinerary?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (shouldDelete == true) {
      try {
        await FirebaseFirestore.instance
            .collection('saved_itineraries')
            .doc(widget.docId)
            .delete();

        if (!context.mounted) return;
        ShadToaster.of(context).show(
          const ShadToast(
            title: Text('Itinerary deleted'),
            description: Text('Your itinerary has been removed'),
          ),
        );
      } catch (e) {
        if (!context.mounted) return;
        ShadToaster.of(context).show(
          ShadToast.destructive(
            title: const Text('Failed to delete'),
            description: Text(e.toString()),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = widget.data['items'] as List<dynamic>? ?? [];
    final createdAt = (widget.data['created_at'] as Timestamp?)?.toDate();
    final location = widget.data['location'] as String? ?? 'Unknown location';

    return Padding(
      padding: EdgeInsets.only(bottom: AppSpacing.md),
      child: ShadCard(
        backgroundColor: AppColors.surfaceElevated,
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            InkWell(
              onTap: () => setState(() => isExpanded = !isExpanded),
              borderRadius: BorderRadius.vertical(
                top: Radius.circular(AppBorderRadius.medium),
                bottom: isExpanded
                    ? Radius.zero
                    : Radius.circular(AppBorderRadius.medium),
              ),
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.bookmark,
                          color: AppColors.primary,
                          size: 20,
                        ),
                        SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: Text(
                            createdAt != null
                                ? DateFormat('MMM d, yyyy').format(createdAt)
                                : 'Saved Plan',
                            style: TextStyle(
                              fontSize: AppTypography.titleMedium,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        Icon(
                          isExpanded
                              ? Icons.keyboard_arrow_up
                              : Icons.keyboard_arrow_down,
                          color: AppColors.textSecondary,
                        ),
                      ],
                    ),
                    SizedBox(height: AppSpacing.xs),
                    Text(
                      location,
                      style: TextStyle(
                        fontSize: AppTypography.bodyMedium,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    SizedBox(height: AppSpacing.sm),
                    // Mini timeline
                    _MiniTimelinePreview(items: items),
                    SizedBox(height: AppSpacing.sm),
                    Text(
                      '${items.length} places${_calculateTotalDistance(items)}',
                      style: TextStyle(
                        fontSize: AppTypography.bodySmall,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Expanded content
            if (isExpanded) ...[
              Divider(height: 1, color: AppColors.border),
              Padding(
                padding: EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Full timeline
                    ...items.map((item) => _buildTimelineItem(item)).toList(),

                    SizedBox(height: AppSpacing.md),
                    Divider(height: 1, color: AppColors.border),
                    SizedBox(height: AppSpacing.md),

                    // Action buttons
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: [
                        _ActionButton(
                          icon: Icons.navigation_outlined,
                          label: 'Navigate',
                          onPressed: () => _navigateToItinerary(context),
                        ),
                        _ActionButton(
                          icon: Icons.edit_outlined,
                          label: 'Edit',
                          onPressed: () => _editItinerary(context),
                        ),
                        _ActionButton(
                          icon: Icons.content_copy_outlined,
                          label: 'Duplicate',
                          onPressed: () => _duplicateItinerary(context),
                        ),
                        _ActionButton(
                          icon: Icons.share_outlined,
                          label: 'Share',
                          onPressed: () => _shareItinerary(context),
                        ),
                        _ActionButton(
                          icon: Icons.public,
                          label: 'Submit to Public',
                          onPressed: () => _submitToPublic(context),
                        ),
                        _ActionButton(
                          icon: Icons.calendar_today_outlined,
                          label: 'Export',
                          onPressed: () => _exportToCalendar(context),
                        ),
                        _ActionButton(
                          icon: Icons.delete_outline,
                          label: 'Delete',
                          onPressed: () => _deleteItinerary(context),
                          isDestructive: true,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineItem(Map<String, dynamic> item) {
    final slotName = item['slot_name'] ?? 'custom';
    final color = _getSlotColor(slotName);
    final photos = item['photos'] as List<dynamic>? ?? [];

    return Padding(
      padding: EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline dot
          Column(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                ),
              ),
              Container(
                width: 2,
                height: 40,
                color: color.withOpacity(0.3),
              ),
            ],
          ),
          SizedBox(width: AppSpacing.md),
          // Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item['start_time'] ?? '',
                  style: TextStyle(
                    fontSize: AppTypography.labelMedium,
                    color: color,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: AppSpacing.xs),
                Text(
                  item['place_name'] ?? '',
                  style: TextStyle(
                    fontSize: AppTypography.bodyLarge,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                if (item['address'] != null && item['address'] != '')
                  Padding(
                    padding: EdgeInsets.only(top: AppSpacing.xs),
                    child: Text(
                      item['address'],
                      style: TextStyle(
                        fontSize: AppTypography.bodySmall,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                if (photos.isNotEmpty) ...[
                  SizedBox(height: AppSpacing.sm),
                  SizedBox(
                    height: 80,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      itemCount: photos.length,
                      itemBuilder: (context, photoIndex) {
                        final photo = photos[photoIndex];
                        // Wikimedia Commons provides direct photo URLs
                        final photoUrl = photo['url'] as String?;
                        if (photoUrl == null || photoUrl.isEmpty)
                          return const SizedBox();

                        return Padding(
                          padding: EdgeInsets.only(right: AppSpacing.sm),
                          child: ClipRRect(
                            borderRadius:
                                BorderRadius.circular(AppBorderRadius.small),
                            child: Image.network(
                              photoUrl,
                              width: 80,
                              height: 80,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) =>
                                  Container(
                                width: 80,
                                height: 80,
                                color: AppColors.surface,
                                child: Icon(
                                  Icons.image_not_supported,
                                  color: AppColors.textSecondary,
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
    );
  }

  String _calculateTotalDistance(List<dynamic> items) {
    double totalKm = 0;
    for (var item in items) {
      final distance = item['distance_from_previous'];
      if (distance != null && distance is num) {
        totalKm += distance / 1000; // Convert meters to km
      }
    }
    return totalKm > 0 ? ' • ${totalKm.toStringAsFixed(1)} km walk' : '';
  }
}

class _MiniTimelinePreview extends StatelessWidget {
  final List<dynamic> items;

  const _MiniTimelinePreview({required this.items});

  // Color scheme for time slots
  static const slotColors = {
    'morning': Color(0xFFFDB462), // Warm yellow
    'mid_day': Color(0xFFE07A5F), // Coral
    'afternoon': Color(0xFF81B29A), // Sage green
    'evening': Color(0xFF7B68A6), // Purple
    'custom': AppColors.accent, // Gold
  };

  Color _getSlotColor(String slotName) {
    return slotColors[slotName.toLowerCase()] ?? AppColors.primary;
  }

  @override
  Widget build(BuildContext context) {
    final displayItems = items.take(4).toList();
    final hasMore = items.length > 4;

    return Row(
      children: [
        ...displayItems.asMap().entries.map((entry) {
          final index = entry.key;
          final item = entry.value;
          final slotName = item['slot_name'] ?? 'custom';
          final color = _getSlotColor(slotName);

          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 16,
                height: 16,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                  border:
                      Border.all(color: AppColors.surfaceElevated, width: 2),
                ),
              ),
              if (index < displayItems.length - 1)
                Container(
                  width: 24,
                  height: 2,
                  color: color.withOpacity(0.3),
                ),
            ],
          );
        }).toList(),
        if (hasMore) ...[
          SizedBox(width: AppSpacing.sm),
          Text(
            '+${items.length - 4} more',
            style: TextStyle(
              fontSize: AppTypography.labelSmall,
              color: AppColors.textSecondary,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final bool isDestructive;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.isDestructive = false,
  });

  @override
  Widget build(BuildContext context) {
    return ShadButton(
      size: ShadButtonSize.sm,
      backgroundColor: isDestructive ? AppColors.error : AppColors.surface,
      onPressed: onPressed,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 16,
            color: isDestructive ? Colors.white : AppColors.textPrimary,
          ),
          SizedBox(width: AppSpacing.xs),
          Text(
            label,
            style: TextStyle(
              color: isDestructive ? Colors.white : AppColors.textPrimary,
              fontSize: AppTypography.labelSmall,
            ),
          ),
        ],
      ),
    );
  }
}
