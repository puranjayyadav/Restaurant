import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';
import '../../screens/restaurant_search_screen.dart';

class PlanditSearchBar extends StatelessWidget {
  final Function(String)? onSubmitted;
  
  const PlanditSearchBar({super.key, this.onSubmitted});

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
        margin: const EdgeInsets.symmetric(vertical: 20),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          color: PlanditColors.glass,
          borderRadius: BorderRadius.circular(100),
          border: Border.all(color: PlanditColors.glassBorder),
          boxShadow: PlanditColors.shadowElevated,
        ),
        child: Row(
          children: [
            const Icon(
              Icons.search,
              color: PlanditColors.mutedForeground,
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: IgnorePointer(
                child: TextField(
                  onSubmitted: onSubmitted,
                  decoration: const InputDecoration(
                    hintText: 'Search curated guides, cuisines...',
                    hintStyle: TextStyle(
                      color: PlanditColors.mutedForeground,
                      fontSize: 14,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.zero,
                  ),
                  style: const TextStyle(
                    color: PlanditColors.foreground,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(
                color: PlanditColors.primary,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.tune_outlined,
                color: PlanditColors.primaryForeground,
                size: 16,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
