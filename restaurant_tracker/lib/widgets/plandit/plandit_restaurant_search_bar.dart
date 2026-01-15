import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';
import '../../screens/restaurant_search_screen.dart';
import 'package:google_fonts/google_fonts.dart';

class PlanditRestaurantSearchBar extends StatelessWidget {
  const PlanditRestaurantSearchBar({super.key});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (context) => const RestaurantSearchScreen(),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(top: 8, bottom: 20),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          color: PlanditColors.chicCream,
          borderRadius: BorderRadius.circular(2), // Sharp architectural feel
          border: Border.all(color: PlanditColors.border.withOpacity(0.5)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.03),
              blurRadius: 10,
              offset: const Offset(0, 4),
            )
          ],
        ),
        child: Row(
          children: [
            const Icon(
              Icons.restaurant_menu,
              color: PlanditColors.accentGold,
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Search Curated Restaurant Guides...',
                style: GoogleFonts.mulish(
                  color: PlanditColors.mutedForeground,
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: PlanditColors.accentGold.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'CURATED',
                style: GoogleFonts.mulish(
                  color: PlanditColors.accentGold,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
