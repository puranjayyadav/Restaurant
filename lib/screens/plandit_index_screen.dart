import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../widgets/plandit/plandit_header.dart';
import '../widgets/plandit/plandit_search_bar.dart';
import '../widgets/plandit/plandit_category_pills.dart';
import '../widgets/plandit/plandit_creator_leaderboard.dart';
import '../widgets/plandit/plandit_editors_pick_carousel.dart';
import '../widgets/plandit/plandit_itinerary_card.dart';

class PlanditIndexScreen extends StatelessWidget {
  const PlanditIndexScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 120),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const PlanditHeader(),
            const SizedBox(height: 16),
            const PlanditSearchBar(),
            const PlanditCategoryPills(),
            PlanditCreatorLeaderboard(),
            PlanditEditorsPickCarousel(),
            
            Padding(
              padding: const EdgeInsets.only(top: 32, bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Trending Itineraries',
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 20,
                      fontWeight: FontWeight.w400,
                      color: PlanditColors.foreground,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Curated journeys from our community',
                    style: TextStyle(
                      fontSize: 14,
                      color: PlanditColors.mutedForeground,
                    ),
                  ),
                ],
              ),
            ),
            
            // Itinerary Feed
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: 3,
              separatorBuilder: (context, index) => const SizedBox(height: 24),
              itemBuilder: (context, index) {
                return _buildMockItineraryCard(index);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMockItineraryCard(int index) {
    final mocks = [
      {
        'id': 1,
        'image': 'https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=800&q=80',
        'title': 'Brooklyn Brownstones & Beyond',
        'location': 'Brooklyn, NYC',
        'duration': '3 days',
        'authorName': 'Chloe K.',
        'authorAvatar': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face',
        'saves': 4521,
        'tags': ['Urban', 'Architecture'],
      },
      {
        'id': 2,
        'image': 'https://images.unsplash.com/photo-1533727937480-da3a97967e95?w=800&q=80',
        'title': 'Tokyo After Dark: Shinjuku & Beyond',
        'location': 'Tokyo, Japan',
        'duration': '5 Days',
        'authorName': 'Marcus T.',
        'authorAvatar': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face',
        'saves': 850,
        'tags': ['Nightlife', 'City Walk'],
      },
      {
        'id': 3,
        'image': 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&q=80',
        'title': 'Parisian Summer: Cafes & Culture',
        'location': 'Paris, France',
        'duration': '4 Days',
        'authorName': 'Sofia L.',
        'authorAvatar': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=face',
        'saves': 2100,
        'tags': ['Romantic', 'Culture'],
      },
    ];

    final data = mocks[index % mocks.length];

    return PlanditItineraryCard(
      id: data['id'] as int,
      image: data['image'] as String,
      title: data['title'] as String,
      location: data['location'] as String,
      duration: data['duration'] as String,
      authorName: data['authorName'] as String,
      authorAvatar: data['authorAvatar'] as String,
      saves: data['saves'] as int,
      tags: List<String>.from(data['tags'] as Iterable),
    );
  }
}
