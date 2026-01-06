import 'package:flutter/material.dart';
import '../theme/design_system.dart';

/// Badge widget showing if restaurant has menu/reviews from Postgres
class EnrichmentBadge extends StatelessWidget {
  final bool hasMenu;
  final bool hasReviews;
  final bool hasTags;
  final double? dataQualityScore;

  const EnrichmentBadge({
    super.key,
    this.hasMenu = false,
    this.hasReviews = false,
    this.hasTags = false,
    this.dataQualityScore,
  });

  @override
  Widget build(BuildContext context) {
    final badges = <Widget>[];

    if (hasMenu) {
      badges.add(_buildBadge(
        icon: Icons.restaurant_menu,
        label: 'Menu',
        color: AppColors.success,
      ));
    }

    if (hasReviews) {
      badges.add(_buildBadge(
        icon: Icons.star,
        label: 'Reviews',
        color: AppColors.warning,
      ));
    }

    if (hasTags) {
      badges.add(_buildBadge(
        icon: Icons.label,
        label: 'Tags',
        color: AppColors.primary,
      ));
    }

    if (badges.isEmpty) {
      return const SizedBox.shrink();
    }

    return Wrap(
      spacing: AppSpacing.xs,
      runSpacing: AppSpacing.xs,
      children: badges,
    );
  }

  Widget _buildBadge({
    required IconData icon,
    required String label,
    required Color color,
  }) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(AppBorderRadius.small),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          SizedBox(width: AppSpacing.xs),
          Text(
            label,
            style: TextStyle(
              fontSize: AppTypography.labelSmall,
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
