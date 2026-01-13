import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class Neighborhood {
  final String name;
  final String vibe;
  final String image;
  final int spots;

  Neighborhood({
    required this.name,
    required this.vibe,
    required this.image,
    required this.spots,
  });
}

class PlanditNeighborhoodSpotlight extends StatelessWidget {
  PlanditNeighborhoodSpotlight({super.key});

  final List<Neighborhood> neighborhoods = [
    Neighborhood(
      name: 'West Village',
      vibe: 'Jazz & Brownstones',
      image: 'https://images.unsplash.com/photo-1534430480872-3498386e7856?w=400&h=600&fit=crop',
      spots: 24,
    ),
    Neighborhood(
      name: 'Williamsburg',
      vibe: 'Vintage & Rooftops',
      image: 'https://images.unsplash.com/photo-1555992336-03a23c7b20ee?w=400&h=600&fit=crop',
      spots: 18,
    ),
    Neighborhood(
      name: 'DUMBO',
      vibe: 'Views & Cobblestones',
      image: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=400&h=600&fit=crop',
      spots: 12,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Section Header
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Neighborhoods',
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 24,
                      fontWeight: FontWeight.w300,
                      color: PlanditColors.foreground,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Curated guides by area',
                    style: TextStyle(
                      fontSize: 12,
                      color: PlanditColors.mutedForeground,
                    ),
                  ),
                ],
              ),
              Container(
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(
                      color: PlanditColors.foreground.withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                ),
                child: const Padding(
                  padding: EdgeInsets.only(bottom: 2),
                  child: Text(
                    'View Map',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: PlanditColors.foreground,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),

        // Neighborhood Cards
        SizedBox(
          height: 240,
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            scrollDirection: Axis.horizontal,
            itemCount: neighborhoods.length,
            separatorBuilder: (context, index) => const SizedBox(width: 16),
            itemBuilder: (context, index) {
              final hood = neighborhoods[index];
              return _NeighborhoodCard(neighborhood: hood);
            },
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}

class _NeighborhoodCard extends StatelessWidget {
  final Neighborhood neighborhood;

  const _NeighborhoodCard({required this.neighborhood});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        boxShadow: PlanditColors.shadowSoft,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Background Image
            Image.network(
              neighborhood.image,
              fit: BoxFit.cover,
            ),
            
            // Gradient Overlay
            Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [
                    Color(0xCC000000), // 80% opacity black
                    Color(0x33000000), // 20% opacity black
                    Colors.transparent,
                  ],
                  stops: [0.0, 0.5, 1.0],
                ),
              ),
            ),
            
            // Content
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${neighborhood.spots} SPOTS',
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.2,
                      color: Colors.white70,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    neighborhood.name,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 18,
                      fontWeight: FontWeight.w300,
                      color: Colors.white,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    neighborhood.vibe,
                    style: const TextStyle(
                      fontSize: 12,
                      color: Colors.white70,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
