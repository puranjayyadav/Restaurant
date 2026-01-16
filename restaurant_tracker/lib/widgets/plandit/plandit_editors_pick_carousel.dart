import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import '../../screens/collection_detail_screen.dart';

class EditorsPick {
  final String id;
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
      id: "00da0fe9-acb6-4d44-868d-199b04b8006c",
      image: "https://images.unsplash.com/photo-1473093226795-af9932fe5856?w=600&q=80",
      title: "Lower East Side Flavors",
      location: "Lower East Side",
      placeCount: 5,
    ),
    EditorsPick(
      id: "090dbe85-cef2-460a-8b64-6bc70433d7c3",
      image: "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=600&q=80",
      title: "Tribeca Treasures",
      location: "Tribeca",
      placeCount: 5,
    ),
    EditorsPick(
      id: "0e629fa7-2aff-4d0b-89a2-d22aaa3333e6",
      image: "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80",
      title: "Astoria Taste Quest",
      location: "Astoria",
      placeCount: 5,
    ),
    EditorsPick(
      id: "007d638a-f182-471e-8402-1ef9f8fd941d",
      image: "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=600&q=80",
      title: "Global Flavors in Queens",
      location: "Queens",
      placeCount: 7,
    ),
    EditorsPick(
      id: "1036891e-0297-4bf5-aaa9-7828fec8c318",
      image: "https://images.unsplash.com/photo-1543007630-9710e4a00a20?w=600&q=80",
      title: "NYC Entertainment Night",
      location: "Multiple Locations",
      placeCount: 7,
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
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => CollectionDetailScreen(
              collectionId: pick.id,
              collectionName: pick.title,
              neighborhood: pick.location,
              imageUrl: pick.image,
            ),
          ),
        );
      },
      child: Container(
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
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return Container(
                    color: PlanditColors.secondary,
                    child: const Center(
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: PlanditColors.primary,
                      ),
                    ),
                  );
                },
                errorBuilder: (context, error, stackTrace) => Container(
                  color: PlanditColors.secondary,
                  child: const Center(
                    child: Icon(
                      Icons.image_not_supported_outlined,
                      color: PlanditColors.mutedForeground,
                    ),
                  ),
                ),
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
      ),
    );
  }
}
