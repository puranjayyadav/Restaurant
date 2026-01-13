import 'package:flutter/material.dart';

/// Design system constants for the minimalist, warm-neutral theme

class AppColors {
  // Off-white, airy base

  static const background = Color(0xFFF9F9F9); // Bone / Off-White

  static const surface = Colors.white;

  static const surfaceElevated = Colors.white;

  // Primary & accents

  static const primary = Color(0xFF007AFF); // Electric blue

  static const secondary = Color(0xFF8B5CF6); // Lavender accent

  static const accent = Color(0xFFFF6B35); // Warm accent for CTAs

  static const teal = Color(0xFF4ECDC4); // Keep for brand contrast

  static const orange = Color(0xFFFF6B35);

  // Text

  static const textPrimary = Color(0xFF1C1C1E); // Deep slate

  static const textSecondary = Color(0xFF8E8E93); // Mid-grey

  static const textLight = Colors.white; // For text on dark backgrounds

  // Borders

  static const border = Color(0xFFE5E5EA);

  // Semantic colors

  static const success = Color(0xFF34C759);

  static const error = Color(0xFFFF3B30);

  static const warning = Color(0xFFFFCC00);

  // Additional shades

  static const primaryLight = Color(0xFF5AA8FF);

  static const primaryDark = Color(0xFF004EA1);

  // Gradients

  static const buttonGradient = LinearGradient(
    colors: [AppColors.orange, AppColors.teal],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );
}

class AppSpacing {
  static const xs = 4.0;

  static const sm = 8.0;

  static const md = 16.0;

  static const lg = 24.0;

  static const xl = 32.0;

  static const xxl = 48.0;
}

class AppTypography {
  static const double displayLarge = 48.0;

  static const double displayMedium = 36.0;

  static const double headlineLarge = 32.0;

  static const double headlineMedium = 28.0;

  static const double headlineSmall = 24.0;

  static const double titleLarge = 22.0;

  static const double titleMedium = 18.0;

  static const double titleSmall = 16.0;

  static const double bodyLarge = 16.0;

  static const double bodyMedium = 14.0;

  static const double bodySmall = 12.0;

  static const double labelLarge = 14.0;

  static const double labelMedium = 12.0;

  static const double labelSmall = 10.0;
}

class AppBorderRadius {
  static const small = 8.0;

  static const medium = 12.0;

  static const large = 16.0;

  static const xLarge = 24.0;
}

class AppElevation {
  static const none = 0.0;

  static const low = 2.0;

  static const medium = 4.0;

  static const high = 8.0;
}

class AppShadows {
  static List<BoxShadow> soft = [
    BoxShadow(
      color: const Color(0xFF000000).withOpacity(0.05),
      blurRadius: 20,
      offset: const Offset(0, 10),
      spreadRadius: 0,
    ),
    BoxShadow(
      color: const Color(0xFF000000).withOpacity(0.02),
      blurRadius: 40,
      offset: const Offset(0, 5),
    ),
  ];

  static List<BoxShadow> button = [
    BoxShadow(
      color: AppColors.orange.withOpacity(0.4),
      blurRadius: 10,
      offset: const Offset(0, 5),
    ),
  ];
}
