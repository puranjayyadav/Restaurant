import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import '../theme/design_system.dart';
import 'enrichment_badge.dart';

/// Enhanced restaurant card showing Google Places data + Postgres enrichment
class RestaurantCard extends StatelessWidget {
  final Map<String, dynamic> restaurant;
  final VoidCallback? onTap;

  const RestaurantCard({
    super.key,
    required this.restaurant,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final name = restaurant['place_name'] as String? ??
        restaurant['name'] as String? ??
        'Unknown Restaurant';
    final address = restaurant['address'] as String? ?? '';
    final rating = restaurant['rating'] as double? ?? 0.0;
    final isEnriched = restaurant['is_enriched'] as bool? ?? false;
    final postgresData =
        restaurant['postgres_data'] as Map<String, dynamic>? ?? {};
    final enrichmentMetadata =
        restaurant['enrichment_metadata'] as Map<String, dynamic>? ?? {};

    // Get enrichment flags
    final hasMenu = enrichmentMetadata['has_menu'] as bool? ?? false;
    final hasReviews = enrichmentMetadata['has_reviews'] as bool? ?? false;
    final hasTags = enrichmentMetadata['has_tags'] as bool? ?? false;

    // Get cuisine/type info
    final types = restaurant['types'] as List<dynamic>? ?? [];
    final cuisine =
        types.isNotEmpty ? types[0].toString().replaceAll('_', ' ') : '';

    // Get price info
    final priceRange = postgresData['price_range'] as String? ??
        _getPriceFromLevel(restaurant['price_level'] as int?);

    return ShadCard(
      backgroundColor: AppColors.surfaceElevated,
      padding: EdgeInsets.all(AppSpacing.md),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppBorderRadius.medium),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Name
                      Text(
                        name,
                        style: textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      SizedBox(height: AppSpacing.xs),
                      // Cuisine/Type
                      if (cuisine.isNotEmpty)
                        Text(
                          cuisine,
                          style: textTheme.bodySmall?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                    ],
                  ),
                ),
                // Rating
                if (rating > 0)
                  Container(
                    padding: EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.xs,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.1),
                      borderRadius:
                          BorderRadius.circular(AppBorderRadius.small),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.star,
                          size: 14,
                          color: AppColors.warning,
                        ),
                        SizedBox(width: AppSpacing.xs),
                        Text(
                          rating.toStringAsFixed(1),
                          style: TextStyle(
                            fontSize: AppTypography.labelSmall,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            SizedBox(height: AppSpacing.sm),
            // Address
            if (address.isNotEmpty)
              Row(
                children: [
                  Icon(
                    Icons.location_on_outlined,
                    size: 14,
                    color: AppColors.textSecondary,
                  ),
                  SizedBox(width: AppSpacing.xs),
                  Expanded(
                    child: Text(
                      address,
                      style: textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            SizedBox(height: AppSpacing.sm),
            // Enrichment badges
            if (isEnriched)
              EnrichmentBadge(
                hasMenu: hasMenu,
                hasReviews: hasReviews,
                hasTags: hasTags,
              ),
            // Price range
            if (priceRange != null && priceRange.isNotEmpty)
              Padding(
                padding: EdgeInsets.only(top: AppSpacing.xs),
                child: Text(
                  priceRange,
                  style: textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  String? _getPriceFromLevel(int? level) {
    if (level == null) return null;
    switch (level) {
      case 0:
        return '\$';
      case 1:
        return '\$\$';
      case 2:
        return '\$\$\$';
      case 3:
        return '\$\$\$\$';
      case 4:
        return '\$\$\$\$\$';
      default:
        return null;
    }
  }
}
