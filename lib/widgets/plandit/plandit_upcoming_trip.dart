import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class PlanditUpcomingTrip extends StatelessWidget {
  const PlanditUpcomingTrip({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'UP NEXT',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.5,
              color: PlanditColors.mutedForeground,
            ),
          ),
          const SizedBox(height: 12),
          
          AspectRatio(
            aspectRatio: 4 / 3,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                boxShadow: PlanditColors.shadowSoft,
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    // Background Image
                    Image.network(
                      'https://images.unsplash.com/photo-1485871981521-5b1fd3805eee?w=800&q=80',
                      fit: BoxFit.cover,
                    ),
                    
                    // Gradient Overlay
                    Container(
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [
                            Color(0x66000000),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                    
                    // Content Card
                    Positioned(
                      bottom: 0,
                      left: 0,
                      right: 0,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.85),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Weekend in DUMBO',
                                style: GoogleFonts.playfairDisplay(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w300,
                                  color: PlanditColors.foreground,
                                ),
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                '4 Stops • 2.5 Hours',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: PlanditColors.mutedForeground,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Row(
                                children: const [
                                  Text(
                                    'View Itinerary',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w500,
                                      color: PlanditColors.foreground,
                                    ),
                                  ),
                                  SizedBox(width: 4),
                                  Icon(
                                    Icons.arrow_forward,
                                    size: 16,
                                    color: PlanditColors.foreground,
                                  ),
                                ],
                              ),
                            ],
                          ),
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
