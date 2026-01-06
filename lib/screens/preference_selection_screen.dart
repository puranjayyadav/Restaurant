// lib/screens/preference_selection_screen.dart

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import '../services/user_preferences_service.dart';
import '../theme/design_system.dart';

class PreferenceSelectionScreen extends StatefulWidget {
  const PreferenceSelectionScreen({super.key});

  @override
  _PreferenceSelectionScreenState createState() =>
      _PreferenceSelectionScreenState();
}

class _PreferenceSelectionScreenState extends State<PreferenceSelectionScreen>
    with SingleTickerProviderStateMixin {
  final User? user = FirebaseAuth.instance.currentUser;
  final UserPreferencesService _prefsService = UserPreferencesService();

  // your existing fields
  Map<String, Map<String, dynamic>> allPlaces = {};
  Set<String> selectedPlaceIds = {};
  bool isLoading = true;

  // NEW: animation fields
  late AnimationController _introController;
  late Animation<double> _fadeAnimation;
  bool _showIntro = true;

  @override
  void initState() {
    super.initState();

    // load visited places as before
    _loadVisitedPlaces();

    // set up fade animation
    _introController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    _fadeAnimation =
        Tween<double>(begin: 0.0, end: 1.0).animate(_introController);

    // start it
    _introController.forward();

    // once the fade-in is done, hide intro and show the list
    _introController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        setState(() {
          _showIntro = false;
        });
      }
    });
  }

  @override
  void dispose() {
    _introController.dispose();
    super.dispose();
  }

  Future<void> _loadVisitedPlaces() async {
    if (user == null) return;
    try {
      final query = await FirebaseFirestore.instance
          .collectionGroup('establishments')
          .where('uid', isEqualTo: user!.uid)
          .get();
      final unique = <String, Map<String, dynamic>>{};
      for (var doc in query.docs) {
        unique[doc.id] = doc.data();
      }
      setState(() {
        allPlaces = unique;
        isLoading = false;
      });
    } catch (e) {
      print("Error loading visited places: $e");
      setState(() => isLoading = false);
    }
  }

  void _toggleSelection(String placeId) {
    setState(() {
      if (selectedPlaceIds.contains(placeId)) {
        selectedPlaceIds.remove(placeId);
      } else {
        selectedPlaceIds.add(placeId);
      }
    });
  }

  Future<void> _savePreferences() async {
    if (user == null) return;
    await _prefsService.saveUserPreferences(
      userId: user!.uid,
      placeIds: selectedPlaceIds.toList(),
    );
    Navigator.pushReplacementNamed(context, '/main');
  }

  @override
  Widget build(BuildContext context) {
    // 1) While intro is playing, show a full-screen fade-in message
    if (_showIntro) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: EdgeInsets.all(AppSpacing.xl),
              child: FadeTransition(
                opacity: _fadeAnimation,
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
                        Icons.restaurant_menu_outlined,
                        size: 64,
                        color: AppColors.primary,
                      ),
                    ),
                    SizedBox(height: AppSpacing.xxl),
                    Text(
                      'Welcome',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: AppTypography.displayMedium,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                        letterSpacing: -0.5,
                      ),
                    ),
                    SizedBox(height: AppSpacing.md),
                    Text(
                      'Let\'s personalize your experience\nby selecting your favorite places',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: AppTypography.bodyLarge,
                        color: AppColors.textSecondary,
                        height: 1.6,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    // 2) Once that's done, fall back to your original loading / list UI
    if (isLoading) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          'Select Your Favorites',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: AppTypography.titleLarge,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      body: Column(
        children: [
          // Header info
          Padding(
            padding: EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.sm,
              AppSpacing.md,
              AppSpacing.md,
            ),
            child: Text(
              allPlaces.isEmpty
                  ? 'No places found. Start exploring to build your favorites!'
                  : 'Select places you\'ve enjoyed. This helps us personalize your recommendations.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: AppTypography.bodyMedium,
                color: AppColors.textSecondary,
                height: 1.5,
              ),
            ),
          ),
          Expanded(
            child: allPlaces.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.explore_outlined,
                          size: 64,
                          color: AppColors.textSecondary,
                        ),
                        SizedBox(height: AppSpacing.lg),
                        Text(
                          'Start exploring to find places',
                          style: TextStyle(
                            fontSize: AppTypography.bodyMedium,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView(
                    padding: EdgeInsets.symmetric(horizontal: AppSpacing.md),
                    children: allPlaces.entries.map((entry) {
                      final placeId = entry.key;
                      final place = entry.value;
                      final isSelected = selectedPlaceIds.contains(placeId);

                      return Padding(
                        padding: EdgeInsets.only(bottom: AppSpacing.sm),
                        child: InkWell(
                          onTap: () => _toggleSelection(placeId),
                          borderRadius:
                              BorderRadius.circular(AppBorderRadius.medium),
                          child: Container(
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? AppColors.primary.withOpacity(0.08)
                                  : AppColors.surfaceElevated,
                              borderRadius:
                                  BorderRadius.circular(AppBorderRadius.medium),
                              border: Border.all(
                                color: isSelected
                                    ? AppColors.primary
                                    : AppColors.border,
                                width: isSelected ? 2 : 1,
                              ),
                            ),
                            child: Padding(
                              padding: EdgeInsets.all(AppSpacing.md),
                              child: Row(
                                children: [
                                  Container(
                                    width: 48,
                                    height: 48,
                                    decoration: BoxDecoration(
                                      color: isSelected
                                          ? AppColors.primary.withOpacity(0.1)
                                          : AppColors.surface,
                                      borderRadius: BorderRadius.circular(
                                          AppBorderRadius.small),
                                    ),
                                    child: Icon(
                                      Icons.restaurant_outlined,
                                      color: isSelected
                                          ? AppColors.primary
                                          : AppColors.textSecondary,
                                      size: 24,
                                    ),
                                  ),
                                  SizedBox(width: AppSpacing.md),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          place['name'] ?? 'Unnamed',
                                          style: TextStyle(
                                            fontSize: AppTypography.bodyLarge,
                                            fontWeight: isSelected
                                                ? FontWeight.w600
                                                : FontWeight.w500,
                                            color: AppColors.textPrimary,
                                          ),
                                        ),
                                        if (place['vicinity'] != null) ...[
                                          SizedBox(height: 2),
                                          Text(
                                            place['vicinity'],
                                            style: TextStyle(
                                              fontSize: AppTypography.bodySmall,
                                              color: AppColors.textSecondary,
                                            ),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                  if (isSelected)
                                    Icon(
                                      Icons.check_circle,
                                      color: AppColors.primary,
                                      size: 24,
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
          ),
          Container(
            padding: EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.surfaceElevated,
              border: Border(
                top: BorderSide(color: AppColors.border, width: 1),
              ),
            ),
            child: SafeArea(
              child: SizedBox(
                width: double.infinity,
                child: ShadButton(
                  size: ShadButtonSize.lg,
                  backgroundColor: selectedPlaceIds.isEmpty || allPlaces.isEmpty
                      ? AppColors.border
                      : AppColors.primary,
                  onPressed: selectedPlaceIds.isEmpty && allPlaces.isNotEmpty
                      ? null
                      : _savePreferences,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        selectedPlaceIds.isEmpty && allPlaces.isNotEmpty
                            ? 'Select at least one place'
                            : allPlaces.isEmpty
                                ? 'Skip for Now'
                                : 'Continue (${selectedPlaceIds.length})',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (selectedPlaceIds.isNotEmpty || allPlaces.isEmpty) ...[
                        SizedBox(width: AppSpacing.sm),
                        const Icon(Icons.arrow_forward,
                            size: 20, color: Colors.white),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
