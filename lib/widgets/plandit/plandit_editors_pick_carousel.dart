import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';

class EditorsPick {
  final int id;
  final String image;
  final String title;
  final String location;

  EditorsPick({
    required this.id,
    required this.image,
    required this.title,
    required this.location,
  });
}

class PlanditEditorsPickCarousel extends StatelessWidget {
  PlanditEditorsPickCarousel({super.key});

  final List<EditorsPick> editorsPicks = [
    EditorsPick(
      id: 1,
      image: "https://images.unsplash.com/photo-1534430480872-3498386e7856?w=400&h=500&fit=crop",
      title: "Hidden Speakeasies",
      location: "East Village",
    ),
    EditorsPick(
      id: 2,
      image: "https://images.unsplash.com/photo-1555992336-03a23c7b20ee?w=400&h=500&fit=crop",
      title: "Rooftop Gardens",
      location: "Midtown",
    ),
    EditorsPick(
      id: 3,
      image: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=400&h=500&fit=crop",
      title: "Jazz After Dark",
      location: "Harlem",
    ),
    EditorsPick(
      id: 4,
      image: "https://images.unsplash.com/photo-1485871981521-5b1fd3805eee?w=400&h=500&fit=crop",
      title: "Brooklyn Bridges",
      location: "DUMBO",
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
                    PlanditColors.foreground.withOpacity(0.7),
                    PlanditColors.foreground.withOpacity(0.2),
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
