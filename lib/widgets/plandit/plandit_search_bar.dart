import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';

class PlanditSearchBar extends StatelessWidget {
  const PlanditSearchBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
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
          const Expanded(
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search destinations, itineraries...',
                hintStyle: TextStyle(
                  color: PlanditColors.mutedForeground,
                  fontSize: 14,
                ),
                border: InputBorder.none,
                isDense: true,
                contentPadding: EdgeInsets.zero,
              ),
              style: TextStyle(
                color: PlanditColors.foreground,
                fontSize: 14,
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
    );
  }
}
