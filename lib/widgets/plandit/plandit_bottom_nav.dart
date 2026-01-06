import 'package:flutter/material.dart';
import '../../theme/plandit_design_system.dart';

class PlanditBottomNav extends StatelessWidget {
  final int currentIndex;
  final Function(int) onTap;

  const PlanditBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 12,
        bottom: 12 + MediaQuery.of(context).padding.bottom,
      ),
      decoration: BoxDecoration(
        color: PlanditColors.glass,
        border: const Border(
          top: BorderSide(color: PlanditColors.border, width: 0.5),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _NavItem(
            icon: Icons.home_outlined,
            activeIcon: Icons.home,
            label: 'Home',
            isActive: currentIndex == 0,
            onTap: () => onTap(0),
          ),
          _NavItem(
            icon: Icons.search,
            activeIcon: Icons.search,
            label: 'Search',
            isActive: currentIndex == 1,
            onTap: () => onTap(1),
          ),
          // Create Button (The big one in the middle)
          GestureDetector(
            onTap: () => onTap(2),
            child: Container(
              width: 56,
              height: 56,
              decoration: const BoxDecoration(
                color: PlanditColors.primary,
                shape: BoxShape.circle,
                boxShadow: PlanditColors.shadowElevated,
              ),
              child: const Icon(
                Icons.add,
                color: PlanditColors.primaryForeground,
                size: 28,
              ),
            ),
          ),
          _NavItem(
            icon: Icons.favorite_outline,
            activeIcon: Icons.favorite,
            label: 'Saved',
            isActive: currentIndex == 3,
            onTap: () => onTap(3),
          ),
          _NavItem(
            icon: Icons.person_outline,
            activeIcon: Icons.person,
            label: 'Profile',
            isActive: currentIndex == 4,
            onTap: () => onTap(4),
          ),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isActive ? activeIcon : icon,
            color: isActive ? PlanditColors.accent : PlanditColors.mutedForeground,
            size: 24,
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: isActive ? PlanditColors.accent : PlanditColors.mutedForeground,
            ),
          ),
        ],
      ),
    );
  }
}
