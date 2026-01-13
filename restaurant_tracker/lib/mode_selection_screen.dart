import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'screens/itinerary_category_selection_screen.dart';
import 'theme/design_system.dart';

/// ----- MODE SELECTION SCREEN -----
/// This page is shown after logging in. It contains a "Scout Mode" button.
class ModeSelectionScreen extends StatelessWidget {
  const ModeSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(AppSpacing.xl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Title
                Text(
                  "Plan Your Day",
                  textAlign: TextAlign.center,
                  style: textTheme.displayMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                    letterSpacing: -0.5,
                  ),
                ),
                SizedBox(height: AppSpacing.md),

                // Description
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: Text(
                    "Create a personalized itinerary from morning to evening. Discover amazing places near you, all within walking distance.",
                    textAlign: TextAlign.center,
                    style: textTheme.bodyLarge?.copyWith(
                      color: AppColors.textSecondary,
                      height: 1.6,
                    ),
                  ),
                ),
                SizedBox(height: AppSpacing.xxl),

                // Action Card
                ShadCard(
                  backgroundColor: AppColors.surfaceElevated,
                  padding: EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Features list
                      _buildFeature(
                        icon: Icons.location_on_outlined,
                        text: 'Nearby recommendations',
                      ),
                      SizedBox(height: AppSpacing.md),
                      _buildFeature(
                        icon: Icons.watch_later_outlined,
                        text: 'Full day planning',
                      ),
                      SizedBox(height: AppSpacing.md),
                      _buildFeature(
                        icon: Icons.directions_walk_outlined,
                        text: 'Walking distance only',
                      ),
                      SizedBox(height: AppSpacing.xl),

                      // CTA Button
                      SizedBox(
                        width: double.infinity,
                        child: ShadButton(
                          size: ShadButtonSize.lg,
                          backgroundColor: AppColors.primary,
                          onPressed: () {
                            Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(
                                builder: (context) =>
                                    const ItineraryCategorySelectionScreen(),
                              ),
                            );
                          },
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text(
                                "Get Started",
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              SizedBox(width: AppSpacing.sm),
                              const Icon(Icons.arrow_forward,
                                  size: 20, color: Colors.white),
                            ],
                          ),
                        ),
                      ),
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

  Widget _buildFeature({required IconData icon, required String text}) {
    return Row(
      children: [
        Icon(icon, size: 20, color: AppColors.primary),
        SizedBox(width: AppSpacing.sm),
        Text(
          text,
          style: TextStyle(
            fontSize: AppTypography.bodyMedium,
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}
