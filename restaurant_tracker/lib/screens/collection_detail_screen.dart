import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../api_service.dart';

class CollectionDetailScreen extends StatefulWidget {
  final String collectionId;
  final String collectionName;
  final String? neighborhood;
  final String? imageUrl;

  const CollectionDetailScreen({
    super.key,
    required this.collectionId,
    required this.collectionName,
    this.neighborhood,
    this.imageUrl,
  });

  @override
  State<CollectionDetailScreen> createState() => _CollectionDetailScreenState();
}

class _CollectionDetailScreenState extends State<CollectionDetailScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  Map<String, dynamic>? _collectionData;
  List<dynamic> _items = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchCollectionDetails();
  }

  Future<void> _fetchCollectionDetails() async {
    try {
      final data = await _apiService.getCollectionById(widget.collectionId);
      if (data != null) {
        setState(() {
          _collectionData = data['collection'];
          _items = data['items'] ?? [];
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = 'Failed to load collection details';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PlanditColors.background,
      body: CustomScrollView(
        slivers: [
          _buildAppBar(),
          if (_isLoading)
            const SliverFillRemaining(
              child: Center(
                child: CircularProgressIndicator(color: PlanditColors.primary),
              ),
            )
          else if (_error != null)
            SliverFillRemaining(
              child: Center(
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            )
          else
            _buildContent(),
        ],
      ),
    );
  }

  Widget _buildAppBar() {
    return SliverAppBar(
      expandedHeight: 300,
      pinned: true,
      backgroundColor: PlanditColors.background,
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.all(8.0),
        child: CircleAvatar(
          backgroundColor: Colors.black.withOpacity(0.3),
          child: IconButton(
            icon: const Icon(Icons.arrow_back, color: Colors.white),
            onPressed: () => Navigator.pop(context),
          ),
        ),
      ),
      flexibleSpace: FlexibleSpaceBar(
        background: Stack(
          fit: StackFit.expand,
          children: [
            Image.network(
              widget.imageUrl ?? 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80',
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) => Container(
                color: PlanditColors.secondary,
                child: const Center(
                  child: Icon(Icons.image, size: 48, color: PlanditColors.mutedForeground),
                ),
              ),
            ),
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.black.withOpacity(0.4),
                    Colors.transparent,
                    PlanditColors.background,
                  ],
                  stops: const [0.0, 0.4, 1.0],
                ),
              ),
            ),
            Positioned(
              bottom: 40,
              left: 24,
              right: 24,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: PlanditColors.primary.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      widget.neighborhood?.toUpperCase() ?? 'NEW YORK',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    widget.collectionName,
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 32,
                      fontWeight: FontWeight.w400,
                      color: PlanditColors.foreground,
                      height: 1.1,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    return SliverPadding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) {
            if (index == 0) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 32),
                child: Text(
                  _collectionData?['description'] ?? '',
                  style: const TextStyle(
                    fontSize: 16,
                    color: PlanditColors.mutedForeground,
                    height: 1.6,
                  ),
                ),
              );
            }

            final item = _items[index - 1];
            return _buildRestaurantCard(item);
          },
          childCount: _items.length + 1,
        ),
      ),
    );
  }

  Widget _buildRestaurantCard(Map<String, dynamic> item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: PlanditColors.shadowSoft,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Image Header
          ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            child: SizedBox(
              height: 200,
              width: double.infinity,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image.network(
                    'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80', // Replace with dynamic if available
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Container(
                      color: PlanditColors.secondary,
                      child: const Center(
                        child: Icon(Icons.restaurant, size: 48, color: PlanditColors.mutedForeground),
                      ),
                    ),
                  ),
                  Positioned(
                    top: 16,
                    right: 16,
                    child: CircleAvatar(
                      backgroundColor: Colors.white.withOpacity(0.9),
                      child: const Icon(Icons.bookmark_border, color: PlanditColors.primary),
                    ),
                  ),
                  if (item['neighborhood'] != null)
                    Positioned(
                      bottom: 16,
                      left: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.6),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          item['neighborhood'].toString().toUpperCase(),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.1,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Title and Cuisine
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        item['name'] ?? 'Unknown Restaurant',
                        style: GoogleFonts.playfairDisplay(
                          fontSize: 24,
                          fontWeight: FontWeight.w400,
                          color: PlanditColors.foreground,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: PlanditColors.secondary,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        item['cuisine'] ?? 'Eatery',
                        style: const TextStyle(
                          fontSize: 11,
                          color: PlanditColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 16),
                
                // Primary Draw
                if (item['primary_draw'] != null) ...[
                  Row(
                    children: [
                      const Icon(Icons.star_outline, size: 16, color: Colors.orange),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          item['primary_draw'].toString(),
                          style: const TextStyle(
                            fontSize: 13,
                            color: PlanditColors.foreground,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                ],
                
                // Vibe
                if (item['vibe'] != null) ...[
                  Row(
                    children: [
                      const Icon(Icons.auto_awesome_outlined, size: 16, color: PlanditColors.primary),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          item['vibe'].toString(),
                          style: const TextStyle(
                            fontSize: 13,
                            color: PlanditColors.mutedForeground,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
                
                const SizedBox(height: 20),
                
                // Community Perception (Featured Quote style)
                if (item['community_perception'] != null)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: PlanditColors.secondary.withOpacity(0.5),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: PlanditColors.primary.withOpacity(0.1)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.format_quote, color: PlanditColors.primary, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            item['community_perception'],
                            style: GoogleFonts.mulish(
                              fontSize: 14,
                              fontStyle: FontStyle.italic,
                              color: PlanditColors.foreground,
                              height: 1.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                const SizedBox(height: 20),
                
                // Summary Description
                Text(
                  item['summary'] ?? 'Discover this unique local gem.',
                  style: const TextStyle(
                    fontSize: 14,
                    color: PlanditColors.mutedForeground,
                    height: 1.6,
                  ),
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                ),
                
                const SizedBox(height: 24),
                
                // CTA
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: PlanditColors.foreground,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: Text(
                      'Explore Details',
                      style: GoogleFonts.mulish(
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
