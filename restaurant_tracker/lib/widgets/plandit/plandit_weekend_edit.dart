import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class PlanditWeekendEdit extends StatelessWidget {
  const PlanditWeekendEdit({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Column(
        children: [
          // Divider with title
          Row(
            children: [
              Expanded(
                child: Container(
                  height: 1,
                  color: PlanditColors.border.withOpacity(0.6),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  'The Weekend Edit',
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 12,
                    fontStyle: FontStyle.italic,
                    color: PlanditColors.mutedForeground,
                  ),
                ),
              ),
              Expanded(
                child: Container(
                  height: 1,
                  color: PlanditColors.border.withOpacity(0.6),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Card
          AspectRatio(
            aspectRatio: 4 / 5,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    // Background Image
                    Image.network(
                      'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80',
                      fit: BoxFit.cover,
                    ),
                    
                    // Content Card at bottom
                    Positioned(
                      bottom: 16,
                      left: 16,
                      right: 16,
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: PlanditColors.background.withOpacity(0.95),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: PlanditColors.border.withOpacity(0.2),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.1),
                              blurRadius: 16,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Badges
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: PlanditColors.foreground,
                                    borderRadius: BorderRadius.circular(100),
                                  ),
                                  child: const Text(
                                    'TRENDING',
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: PlanditColors.background,
                                      letterSpacing: 0.8,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Row(
                                  children: const [
                                    Icon(
                                      Icons.access_time,
                                      size: 12,
                                      color: PlanditColors.mutedForeground,
                                    ),
                                    SizedBox(width: 4),
                                    Text(
                                      '5h 30m',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: PlanditColors.mutedForeground,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            
                            // Title
                            Text(
                              'Art & Wine in Chelsea',
                              style: GoogleFonts.playfairDisplay(
                                fontSize: 20,
                                fontWeight: FontWeight.w300,
                                color: PlanditColors.foreground,
                                height: 1.2,
                              ),
                            ),
                            const SizedBox(height: 8),
                            
                            // Description
                            const Text(
                              'Start at high-end galleries, end at a hidden speakeasy. The perfect Saturday afternoon loop.',
                              style: TextStyle(
                                fontSize: 14,
                                color: PlanditColors.mutedForeground,
                                height: 1.4,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 12),
                            
                            // Footer
                            Container(
                              padding: const EdgeInsets.only(top: 12),
                              decoration: BoxDecoration(
                                border: Border(
                                  top: BorderSide(
                                    color: PlanditColors.border.withOpacity(0.4),
                                  ),
                                ),
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  // Avatar stack
                                  SizedBox(
                                    width: 60,
                                    height: 24,
                                    child: Stack(
                                      children: [
                                        Positioned(
                                          left: 0,
                                          child: Container(
                                            width: 24,
                                            height: 24,
                                            decoration: BoxDecoration(
                                              color: PlanditColors.muted,
                                              shape: BoxShape.circle,
                                              border: Border.all(
                                                color: PlanditColors.background,
                                                width: 2,
                                              ),
                                            ),
                                          ),
                                        ),
                                        Positioned(
                                          left: 16,
                                          child: Container(
                                            width: 24,
                                            height: 24,
                                            decoration: BoxDecoration(
                                              color: PlanditColors.mutedForeground.withOpacity(0.3),
                                              shape: BoxShape.circle,
                                              border: Border.all(
                                                color: PlanditColors.background,
                                                width: 2,
                                              ),
                                            ),
                                          ),
                                        ),
                                        Positioned(
                                          left: 32,
                                          child: Container(
                                            width: 24,
                                            height: 24,
                                            decoration: BoxDecoration(
                                              color: PlanditColors.mutedForeground.withOpacity(0.5),
                                              shape: BoxShape.circle,
                                              border: Border.all(
                                                color: PlanditColors.background,
                                                width: 2,
                                              ),
                                            ),
                                            child: const Center(
                                              child: Text(
                                                '+12',
                                                style: TextStyle(
                                                  fontSize: 8,
                                                  color: PlanditColors.background,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const Text(
                                    'View Itinerary →',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                      color: PlanditColors.foreground,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
