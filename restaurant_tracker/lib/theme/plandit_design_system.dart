import 'package:flutter/material.dart';

class PlanditColors {
  // premium Modern Classic Palette
  static const canvas = Color(0xFFFFFFFF);
  static const background = Color(0xFFF9F7F2); // Warm off-white
  static const primaryText = Color(0xFF1A1A1A); // Dark Charcoal
  static const secondaryText = Color(0xFF6E6E73); // Cool Slate Gray
  static const accentGold = Color(0xFFD4AF37); // Muted Gold/Bronze
  static const curatorBackground = Color(0xFFF7F4F0); // Subtle warm beige
  static const tagFill = Color(0xFFF2F2F7); // Soft gray fill
  
  static const foreground = Color(0xFF1A1A1A);
  static const card = Colors.white;
  static const border = Color(0xFFE5E5EA);
  static const accent = Color(0xFFD4AF37);
  static const mutedForeground = Color(0xFF6E6E73);

  // Modern Classic Palette (for Editorial sections)
  static const chicCream = Color(0xFFF9F7F2);
  static const chicCharcoal = Color(0xFF1A1A1A);
  static const chicGold = Color(0xFFD4AF37);
  
  static const shadowChic = [
    BoxShadow(
      color: Color(0x0F000000),
      blurRadius: 40,
      offset: Offset(0, 16),
      spreadRadius: -8,
    )
  ];

  // Backward Compatibility / Legacy Aliases
  static const primary = Color(0xFF1A1A1A);
  static const primaryForeground = Color(0xFFFFFFFF);
  static const secondary = Color(0xFFF2F2F7);
  static const secondaryForeground = Color(0xFF6E6E73);
  static const muted = Color(0xFFF2F2F7);
  
  static const rankGold = Color(0xFFE6AC1A);
  static const rankSilver = Color(0xFFB3B3B3);
  static const rankBronze = Color(0xFFBF6F40);
  
  static final glass = Colors.white.withOpacity(0.7);
  static final glassBorder = Colors.white.withOpacity(0.3);

  static const shadowSoft = [
    BoxShadow(
      color: Color(0x0A000000), // Very light diffusion
      blurRadius: 32,
      offset: Offset(0, 8),
      spreadRadius: 0,
    )
  ];

  static const shadowElevated = [
    BoxShadow(
      color: Color(0x14000000),
      blurRadius: 60,
      offset: Offset(0, 20),
      spreadRadius: -10,
    )
  ];

  static const overlayGradient = LinearGradient(
    begin: Alignment.bottomCenter,
    end: Alignment.topCenter,
    colors: [
      Color(0x99000000),
      Color(0x33000000),
      Colors.transparent,
    ],
    stops: [0.0, 0.5, 1.0],
  );
}
