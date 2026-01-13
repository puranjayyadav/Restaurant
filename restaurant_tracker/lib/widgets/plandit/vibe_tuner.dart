import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

enum VibeMode { energy, budget }

class VibeTuner extends StatefulWidget {
  final double vibeLevel;
  final ValueChanged<double> onVibeChange;
  final VibeMode mode;
  final VoidCallback onModeToggle;

  const VibeTuner({
    super.key,
    required this.vibeLevel,
    required this.onVibeChange,
    required this.mode,
    required this.onModeToggle,
  });

  @override
  State<VibeTuner> createState() => _VibeTunerState();
}

class _VibeTunerState extends State<VibeTuner> {
  bool isDragging = false;

  @override
  Widget build(BuildContext context) {
    final labels = widget.mode == VibeMode.energy
        ? {'left': 'Chill', 'right': 'Hype'}
        : {'left': 'Thrifty', 'right': 'Boujee'};

    final leftIcon = widget.mode == VibeMode.energy
        ? Icons.coffee_outlined
        : Icons.auto_awesome_outlined;
    final rightIcon = widget.mode == VibeMode.energy
        ? Icons.local_fire_department_outlined
        : Icons.diamond_outlined;

    return Positioned(
      bottom: 24,
      left: 24,
      right: 24,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: PlanditColors.card.withOpacity(0.9),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: PlanditColors.border.withOpacity(0.4)),
          boxShadow: PlanditColors.shadowElevated,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Mode Toggle
            Center(
              child: GestureDetector(
                onTap: widget.onModeToggle,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: PlanditColors.secondary.withOpacity(0.6),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Energy',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: widget.mode == VibeMode.energy
                              ? PlanditColors.foreground
                              : PlanditColors.mutedForeground,
                        ),
                      ),
                      Container(
                        width: 1,
                        height: 12,
                        margin: const EdgeInsets.symmetric(horizontal: 8),
                        color: PlanditColors.border,
                      ),
                      Text(
                        'Budget',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: widget.mode == VibeMode.budget
                              ? PlanditColors.foreground
                              : PlanditColors.mutedForeground,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Slider
            Row(
              children: [
                // Left Label
                SizedBox(
                  width: 70,
                  child: Row(
                    children: [
                      Icon(
                        leftIcon,
                        size: 16,
                        color: widget.vibeLevel < 40
                            ? PlanditColors.accent
                            : PlanditColors.mutedForeground.withOpacity(0.5),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        labels['left']!,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: widget.vibeLevel < 40
                              ? PlanditColors.foreground
                              : PlanditColors.mutedForeground.withOpacity(0.5),
                        ),
                      ),
                    ],
                  ),
                ),

                // Slider Track
                Expanded(
                  child: SizedBox(
                    height: 40,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        // Background Track
                        Container(
                          height: 6,
                          decoration: BoxDecoration(
                            color: PlanditColors.secondary,
                            borderRadius: BorderRadius.circular(100),
                          ),
                        ),

                        // Gradient Fill
                        Positioned.fill(
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: FractionallySizedBox(
                              widthFactor: widget.vibeLevel / 100,
                              child: Container(
                                height: 6,
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: widget.mode == VibeMode.energy
                                        ? [
                                            const Color(0xFF5DADE2),
                                            const Color(0xFFE67E50),
                                          ]
                                        : [
                                            const Color(0xFF52C77A),
                                            const Color(0xFFE6AC1A),
                                          ],
                                  ),
                                  borderRadius: BorderRadius.circular(100),
                                ),
                              ),
                            ),
                          ),
                        ),

                        // Slider
                        SliderTheme(
                          data: SliderThemeData(
                            trackHeight: 0,
                            thumbShape: CustomThumbShape(isDragging: isDragging),
                            overlayShape: const RoundSliderOverlayShape(overlayRadius: 0),
                            activeTrackColor: Colors.transparent,
                            inactiveTrackColor: Colors.transparent,
                          ),
                          child: Slider(
                            value: widget.vibeLevel,
                            min: 0,
                            max: 100,
                            onChanged: widget.onVibeChange,
                            onChangeStart: (_) => setState(() => isDragging = true),
                            onChangeEnd: (_) => setState(() => isDragging = false),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Right Label
                SizedBox(
                  width: 70,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Text(
                        labels['right']!,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: widget.vibeLevel > 60
                              ? PlanditColors.foreground
                              : PlanditColors.mutedForeground.withOpacity(0.5),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Icon(
                        rightIcon,
                        size: 16,
                        color: widget.vibeLevel > 60
                            ? PlanditColors.accent
                            : PlanditColors.mutedForeground.withOpacity(0.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Current Vibe Label
            const SizedBox(height: 8),
            Text(
              _getVibeLabel(widget.vibeLevel, labels),
              style: const TextStyle(
                fontSize: 10,
                letterSpacing: 1.2,
                color: PlanditColors.mutedForeground,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getVibeLabel(double level, Map<String, String> labels) {
    if (level < 30) return 'Very ${labels['left']}';
    if (level < 45) return labels['left']!;
    if (level < 55) return 'Balanced';
    if (level < 70) return labels['right']!;
    return 'Very ${labels['right']}';
  }
}

class CustomThumbShape extends SliderComponentShape {
  final bool isDragging;

  const CustomThumbShape({required this.isDragging});

  @override
  Size getPreferredSize(bool isEnabled, bool isDiscrete) {
    return const Size(24, 24);
  }

  @override
  void paint(
    PaintingContext context,
    Offset center, {
    required Animation<double> activationAnimation,
    required Animation<double> enableAnimation,
    required bool isDiscrete,
    required TextPainter labelPainter,
    required RenderBox parentBox,
    required SliderThemeData sliderTheme,
    required TextDirection textDirection,
    required double value,
    required double textScaleFactor,
    required Size sizeWithOverflow,
  }) {
    final Canvas canvas = context.canvas;
    final scale = isDragging ? 1.25 : 1.0;

    // Outer circle
    final outerPaint = Paint()
      ..color = PlanditColors.foreground
      ..style = PaintingStyle.fill;

    canvas.drawCircle(center, 12 * scale, outerPaint);

    // Inner circle
    final innerPaint = Paint()
      ..color = PlanditColors.background
      ..style = PaintingStyle.fill;

    canvas.drawCircle(center, 8 * scale, innerPaint);
  }
}
