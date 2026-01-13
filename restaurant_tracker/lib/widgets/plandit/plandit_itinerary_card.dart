import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class PlanditItineraryCard extends StatelessWidget {
  final int id;
  final String image;
  final String title;
  final String location;
  final String duration;
  final String authorName;
  final String authorAvatar;
  final int saves;
  final List<String> tags;

  const PlanditItineraryCard({
    super.key,
    required this.id,
    required this.image,
    required this.title,
    required this.location,
    required this.duration,
    required this.authorName,
    required this.authorAvatar,
    required this.saves,
    required this.tags,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        // boxShadow: PlanditColors.shadowElevated, // Card itself has shadow in React app? No, the content card does.
      ),
      child: Column(
        children: [
          Stack(
            clipBehavior: Clip.none,
            children: [
              // Main Image
              AspectRatio(
                aspectRatio: 3 / 4,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(32),
                  child: Image.network(
                    image,
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              // Gradient Overlay
              Positioned.fill(
                child: Container(
                  decoration: const BoxDecoration(
                    gradient: PlanditColors.overlayGradient,
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(32),
                      topRight: Radius.circular(32),
                    ),
                  ),
                ),
              ),
              // Glass Badges & Heart at top
              Positioned(
                top: 16,
                left: 16,
                right: 16,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: tags.map((tag) => _GlassBadge(text: tag)).toList(),
                      ),
                    ),
                    _GlassBadge(
                      icon: Icons.favorite_outline,
                      text: saves.toString(),
                    ),
                  ],
                ),
              ),
              // Content Card (Overlays bottom of image)
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: const BoxDecoration(
                    color: PlanditColors.card,
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(32),
                      topRight: Radius.circular(32),
                    ),
                    boxShadow: PlanditColors.shadowElevated,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Location & Duration
                      Row(
                        children: [
                          const Icon(Icons.location_on_outlined, size: 16, color: PlanditColors.mutedForeground),
                          const SizedBox(width: 6),
                          Text(
                            location,
                            style: const TextStyle(
                              fontSize: 14,
                              color: PlanditColors.mutedForeground,
                            ),
                          ),
                          const SizedBox(width: 16),
                          const Icon(Icons.access_time, size: 16, color: PlanditColors.mutedForeground),
                          const SizedBox(width: 6),
                          Text(
                            duration,
                            style: const TextStyle(
                              fontSize: 14,
                              color: PlanditColors.mutedForeground,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      // Title
                      Text(
                        title,
                        style: GoogleFonts.playfairDisplay(
                          fontSize: 24,
                          fontWeight: FontWeight.w400,
                          color: PlanditColors.foreground,
                          height: 1.2,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Author
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 20,
                            backgroundImage: NetworkImage(authorAvatar),
                          ),
                          const SizedBox(width: 12),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                authorName,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: PlanditColors.foreground,
                                ),
                              ),
                              const Text(
                                'Travel Creator',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: PlanditColors.mutedForeground,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10), // Space between cards in list
        ],
      ),
    );
  }
}

class _GlassBadge extends StatelessWidget {
  final String text;
  final IconData? icon;

  const _GlassBadge({required this.text, this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.85),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: Colors.white.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: PlanditColors.foreground.withOpacity(0.8)),
            const SizedBox(width: 6),
          ],
          Text(
            text,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: PlanditColors.foreground.withOpacity(0.8),
            ),
          ),
        ],
      ),
    );
  }
}
