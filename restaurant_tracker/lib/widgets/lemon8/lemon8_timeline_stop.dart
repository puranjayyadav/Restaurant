import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class Lemon8TimelineStop extends StatelessWidget {
  final String category;
  final String duration;
  final String priceRange;
  final String placeName;
  final String notes;
  final bool isFirst;
  final bool isLast;
  final IconData icon;
  final bool isLoved;

  final VoidCallback? onMapTap;
  final VoidCallback? onLoveTap;

  const Lemon8TimelineStop({
    super.key,
    required this.category,
    required this.duration,
    required this.priceRange,
    required this.placeName,
    required this.notes,
    this.isFirst = false,
    this.isLast = false,
    this.isLoved = false,
    required this.icon,
    this.onMapTap,
    this.onLoveTap,
  });

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline Column
          SizedBox(
            width: 48,
            child: Column(
              children: [
                if (!isFirst)
                  Expanded(
                    child: Container(
                      width: 1,
                      color: PlanditColors.chicGold.withOpacity(0.3),
                    ),
                  ),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: PlanditColors.chicCream,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: PlanditColors.chicGold,
                      width: 1,
                    ),
                  ),
                  child: Icon(
                    icon,
                    size: 16,
                    color: PlanditColors.chicGold,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 1,
                      color: PlanditColors.chicGold.withOpacity(0.3),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          // Content Column
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 32.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Metadata Row
                  Text(
                    '${category.toUpperCase()} • $duration • $priceRange',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: PlanditColors.mutedForeground,
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 8),
                  // Place Name
                  Text(
                    placeName,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 22,
                      fontWeight: FontWeight.w500,
                      color: PlanditColors.chicCharcoal,
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Editorial Notes
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border(
                        left: BorderSide(
                          color: PlanditColors.chicGold.withOpacity(0.2),
                          width: 2,
                        ),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: notes.split('\n').map((para) {
                        final trimmed = para.trim();
                        if (trimmed.isEmpty) return const SizedBox(height: 8);
                        
                        final isBullet = trimmed.startsWith('•') || 
                                         trimmed.startsWith('-') || 
                                         trimmed.startsWith('*');
                        
                        return Padding(
                          padding: EdgeInsets.only(
                            bottom: 8.0,
                            left: isBullet ? 12.0 : 0.0,
                          ),
                          child: Text(
                            trimmed,
                            style: const TextStyle(
                              fontStyle: FontStyle.italic,
                              fontSize: 14,
                              color: PlanditColors.mutedForeground,
                              height: 1.6,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  // Actions
                  Row(
                    children: [
                      _buildActionBtn('View on Map', Icons.map_outlined, onMapTap),
                      const SizedBox(width: 12),
                      _buildActionBtn('Love', isLoved ? Icons.favorite : Icons.favorite_border, onLoveTap),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionBtn(String label, IconData icon, VoidCallback? onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          border: Border.all(
            color: PlanditColors.border.withOpacity(0.5),
          ),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: PlanditColors.mutedForeground),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: PlanditColors.mutedForeground,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
