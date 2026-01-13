import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../widgets/plandit/plandit_header.dart';
import '../widgets/plandit/plandit_search_bar.dart';
import '../widgets/plandit/plandit_category_pills.dart';
import '../widgets/plandit/plandit_creator_leaderboard.dart';
import '../widgets/plandit/plandit_editors_pick_carousel.dart';
import '../widgets/plandit/plandit_itinerary_card.dart';
import '../widgets/plandit/plandit_bottom_nav.dart';
import '../widgets/plandit/plandit_dashboard_header.dart';
import '../widgets/plandit/plandit_ask_ai_section.dart';
import '../widgets/plandit/plandit_neighborhood_spotlight.dart';
import '../widgets/plandit/plandit_weekend_edit.dart';
import '../widgets/plandit/plandit_upcoming_trip.dart';
import '../widgets/plandit/plandit_curated_categories.dart';
import 'saved_itineraries_screen.dart';
import 'public_itineraries_screen.dart';
import 'settings_screen.dart';
import 'plandit_dashboard_screen.dart';
import 'plandit_index_screen.dart';

class PlanditExploreScreen extends StatefulWidget {
  const PlanditExploreScreen({super.key});

  @override
  State<PlanditExploreScreen> createState() => _PlanditExploreScreenState();
}

class _PlanditExploreScreenState extends State<PlanditExploreScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final List<Widget> pages = [
      _buildDashboardBody(), // Home tab - Dashboard
      const PlanditIndexScreen(), // Search tab - Index/Explore
      const Center(child: Text("Create - Coming Soon")),
      SavedItinerariesScreen(),
      SettingsScreen(),
    ];

    return Scaffold(
      backgroundColor: PlanditColors.background,
      body: Stack(
        children: [
          IndexedStack(
            index: _currentIndex,
            children: pages,
          ),
          
          // Bottom Nav
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: PlanditBottomNav(
              currentIndex: _currentIndex,
              onTap: (index) {
                setState(() {
                  _currentIndex = index;
                });
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardBody() {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PlanditDashboardHeader(),
          const PlanditAskAISection(),
          PlanditNeighborhoodSpotlight(),
          const PlanditWeekendEdit(),
          const PlanditUpcomingTrip(),
          const PlanditCuratedCategories(),
        ],
      ),
    );
  }

  Widget _buildMockItineraryCard(int index) {
    final mocks = [
      {
        'id': 1,
        'image': 'https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=800&q=80',
        'title': 'The Ultimate Foodies Guide to West Village',
        'location': 'New York, USA',
        'duration': '3 Days',
        'authorName': 'Chloe K.',
        'authorAvatar': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face',
        'saves': 1240,
        'tags': ['Foodie', 'Hidden Gem'],
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
