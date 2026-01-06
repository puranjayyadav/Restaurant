import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class PlanditDashboardHeader extends StatelessWidget {
  const PlanditDashboardHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 48, bottom: 16, left: 24, right: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Good Morning, Alex',
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 32,
                    fontWeight: FontWeight.w300,
                    color: PlanditColors.foreground,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '⛅ 68°F • Clear skies in Brooklyn',
                  style: TextStyle(
                    fontSize: 14,
                    color: PlanditColors.mutedForeground,
                    fontWeight: FontWeight.w200,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: () {},
            icon: const Icon(
              Icons.notifications_none_outlined,
              color: PlanditColors.foreground,
              size: 24,
            ),
          ),
        ],
      ),
    );
  }
}
