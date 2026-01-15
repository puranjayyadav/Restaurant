import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class EditorsPick {
  final int id;
  final String image;
  final String title;
  final String location;
  final int placeCount;

  EditorsPick({
    required this.id,
    required this.image,
    required this.title,
    required this.location,
    required this.placeCount,
  });
}

class PlanditEditorsPickCarousel extends StatelessWidget {
  PlanditEditorsPickCarousel({super.key});

  final List<EditorsPick> editorsPicks = [
    EditorsPick(
      id: 1,
      image: "https://images.unsplash.com/photo-1565299585323-38d6b0865ef4?w=400&h=500&fit=crop",
      title: "Mexican Fiesta",
      location: "Lower East Side",
      placeCount: 7,
    ),
    EditorsPick(
      id: 2,
      image: "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=400&h=500&fit=crop",
      title: "Italian Grand Tour",
      location: "West Village",
      placeCount: 6,
    ),
    EditorsPick(
      id: 3,
      image: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&h=500&fit=crop",
      title: "Date Night Gems",
      location: "Brooklyn Heights",
      placeCount: 5,
    ),
    EditorsPick(
      id: 4,
      image: "https://images.unsplash.com/photo-1493606278519-11aa9f86e40a?w=400&h=500&fit=crop",
      title: "Late Night NYC",
      location: "Chelsea",
      placeCount: 7,
    ),
    EditorsPick(
      id: 5,
      image: "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=400&h=500&fit=crop",
      title: "Hidden Speakeasies",
      location: "East Village",
      placeCount: 6,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "NYC Editors' Pick",
                style: GoogleFonts.playfairDisplay(
                  fontSize: 20,
                  fontWeight: FontWeight.w400,
                  color: PlanditColors.foreground,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                "Curated by our local experts",
                style: TextStyle(
                  fontSize: 14,
                  color: PlanditColors.mutedForeground,
                ),
              ),
            ],
          ),
        ),
        SizedBox(
          height: 200,
          child: ListView.separated(
            clipBehavior: Clip.none,
            scrollDirection: Axis.horizontal,
            itemCount: editorsPicks.length,
            separatorBuilder: (context, index) => const SizedBox(width: 12),
            itemBuilder: (context, index) {
              final pick = editorsPicks[index];
              return _PickCard(pick: pick);
            },
          ),
        ),
      ],
    );
  }
}

class _PickCard extends StatelessWidget {
  final EditorsPick pick;

  const _PickCard({required this.pick});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      height: 200,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: PlanditColors.shadowSoft,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.network(
              pick.image,
              fit: BoxFit.cover,
            ),
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [
                    PlanditColors.foreground.withOpacity(0.8),
                    PlanditColors.foreground.withOpacity(0.3),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: PlanditColors.accent.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${pick.placeCount} PLACES',
                      style: GoogleFonts.mulish(
                        fontSize: 8,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    pick.title,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 14,
                      fontWeight: FontWeight.w400,
                      color: PlanditColors.primaryForeground,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(
                        Icons.location_on_outlined,
                        size: 12,
                        color: Colors.white70,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        pick.location,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.white70,
                        ),
                      ),
                    ],
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
