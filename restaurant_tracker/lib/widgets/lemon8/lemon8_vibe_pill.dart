import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';

class Lemon8VibePill extends StatelessWidget {
  final String text;
  final bool isLarge;

  const Lemon8VibePill({
    super.key,
    required this.text,
    this.isLarge = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isLarge ? 12 : 8,
        vertical: isLarge ? 6 : 4,
      ),
      decoration: BoxDecoration(
        color: Colors.transparent,
        border: Border.all(
          color: PlanditColors.chicGold.withOpacity(0.6),
          width: 1,
        ),
        borderRadius: BorderRadius.zero, // Sharp corners as requested
      ),
      child: Text(
        text.toUpperCase(),
        style: TextStyle(
          color: PlanditColors.chicGold,
          fontSize: isLarge ? 11 : 10,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.5,
        ),
      ),
    );
  }
}
