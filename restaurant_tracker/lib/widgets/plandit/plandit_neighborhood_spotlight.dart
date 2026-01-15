import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/plandit_design_system.dart';
import '../../api_service.dart';
import '../../screens/collection_detail_screen.dart';

class Neighborhood {
  final String id;
  final String name;
  final String vibe;
  final String image;
  final int spots;
  final String? neighborhood;

  Neighborhood({
    required this.id,
    required this.name,
    required this.vibe,
    required this.image,
    required this.spots,
    this.neighborhood,
  });
}

class PlanditNeighborhoodSpotlight extends StatefulWidget {
  const PlanditNeighborhoodSpotlight({super.key});

  @override
  State<PlanditNeighborhoodSpotlight> createState() => _PlanditNeighborhoodSpotlightState();
}

class _PlanditNeighborhoodSpotlightState extends State<PlanditNeighborhoodSpotlight> {
  final ApiService _apiService = ApiService();
  List<Neighborhood> _neighborhoods = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchRealCollections();
  }

  Future<void> _fetchRealCollections() async {
    try {
      final collections = await _apiService.getCollections(limit: 5, minItems: 3);
      setState(() {
        _neighborhoods = collections.map((c) {
          // Map backend fields to Neighborhood model
          // Using random Unsplash images for now as backend doesn't provide them yet
          final List<String> images = [
            'https://images.unsplash.com/photo-1534430480872-3498386e7856?w=400&h=600&fit=crop',
            'https://images.unsplash.com/photo-1555992336-03a23c7b20ee?w=400&h=600&fit=crop',
            'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=400&h=600&fit=crop',
            'https://images.unsplash.com/photo-1513635269975-59663e001ad7?w=400&h=600&fit=crop',
            'https://images.unsplash.com/photo-1449034446853-66c86144b0ad?w=400&h=600&fit=crop',
          ];
          
          return Neighborhood(
            id: c['id'],
            name: c['name'],
            vibe: c['neighborhood'] ?? 'Local Favorites',
            image: images[collections.indexOf(c) % images.length],
            spots: c['item_count'] ?? 8, 
            neighborhood: c['neighborhood'],
          );
        }).toList();
        _isLoading = false;
      });
    } catch (e) {
      print('Error loading neighborhoods: $e');
      setState(() => _isLoading = false);
    }
  }

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
          child: _isLoading 
            ? const Center(child: CircularProgressIndicator(color: PlanditColors.primary))
            : ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                scrollDirection: Axis.horizontal,
                itemCount: _neighborhoods.length,
                separatorBuilder: (context, index) => const SizedBox(width: 16),
                itemBuilder: (context, index) {
                  final hood = _neighborhoods[index];
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
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => CollectionDetailScreen(
              collectionId: neighborhood.id,
              collectionName: neighborhood.name,
              neighborhood: neighborhood.neighborhood,
            ),
          ),
        );
      },
      child: Container(
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
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
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
      ),
    );
  }
}
