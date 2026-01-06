import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import '../../api_service.dart';

class Collection {
  final String id;
  final String title;
  final String image;
  final int plans;

  Collection({
    required this.id,
    required this.title,
    required this.image,
    required this.plans,
  });

  factory Collection.fromJson(Map<String, dynamic> json) {
    // Handle stops - it's a List of stop objects in Supabase
    int stopsCount = 0;
    final stopsData = json['stops'];
    if (stopsData is List) {
      stopsCount = stopsData.length;
    } else if (stopsData is num) {
      stopsCount = stopsData.toInt();
    }
    
    return Collection(
      id: json['source_id']?.toString() ?? '',
      title: json['new_title']?.toString() ?? json['title']?.toString() ?? 'Untitled',
      image: json['header_image_url']?.toString() ?? 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=400&h=600&fit=crop',
      plans: stopsCount,
    );
  }
}

class PlanditCuratedCategories extends StatefulWidget {
  const PlanditCuratedCategories({super.key});

  @override
  State<PlanditCuratedCategories> createState() => _PlanditCuratedCategoriesState();
}

class _PlanditCuratedCategoriesState extends State<PlanditCuratedCategories> {
  final ApiService _apiService = ApiService();
  List<Collection> collections = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCollections();
  }

  Future<void> _loadCollections() async {
    try {
      final adventures = await _apiService.getCloneableAdventures(limit: 10);
      setState(() {
        collections = adventures.map((json) => Collection.fromJson(json)).toList();
        isLoading = false;
      });
    } catch (e) {
      print('Error loading collections: $e');
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  'The NYC Edit',
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 20,
                    fontWeight: FontWeight.w300,
                    color: PlanditColors.foreground,
                  ),
                ),
                const Text(
                  'View All',
                  style: TextStyle(
                    fontSize: 12,
                    color: PlanditColors.mutedForeground,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          
          // Horizontal Carousel
          SizedBox(
            height: 210,
            child: isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: PlanditColors.accent,
                    ),
                  )
                : collections.isEmpty
                    ? Center(
                        child: Text(
                          'No collections available',
                          style: TextStyle(
                            fontSize: 14,
                            color: PlanditColors.mutedForeground,
                          ),
                        ),
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        scrollDirection: Axis.horizontal,
                        itemCount: collections.length,
                        separatorBuilder: (context, index) => const SizedBox(width: 16),
                        itemBuilder: (context, index) {
                          return _CollectionCard(collection: collections[index]);
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _CollectionCard extends StatelessWidget {
  final Collection collection;

  const _CollectionCard({required this.collection});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
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
              collection.image,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) {
                return Container(
                  color: PlanditColors.secondary,
                  child: const Icon(
                    Icons.image_not_supported,
                    color: PlanditColors.mutedForeground,
                    size: 48,
                  ),
                );
              },
            ),
            
            // Gradient Overlay
            Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [
                    Color(0xB3000000), // 70% opacity
                    Color(0x33000000), // 20% opacity
                    Colors.transparent,
                  ],
                ),
              ),
            ),
            
            // Plans Badge - Top Right
            if (collection.plans > 0)
              Positioned(
                top: 12,
                right: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.7),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: Text(
                    '${collection.plans} Stops',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            
            // Title - Bottom
            Positioned(
              bottom: 16,
              left: 16,
              right: 16,
              child: Text(
                collection.title,
                style: GoogleFonts.playfairDisplay(
                  fontSize: 18,
                  fontWeight: FontWeight.w300,
                  color: Colors.white,
                  height: 1.2,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
