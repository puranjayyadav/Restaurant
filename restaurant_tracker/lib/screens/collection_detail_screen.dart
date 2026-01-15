import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/plandit_design_system.dart';
import '../api_service.dart';

class CollectionDetailScreen extends StatefulWidget {
  final String collectionId;
  final String collectionName;
  final String? neighborhood;

  const CollectionDetailScreen({
    super.key,
    required this.collectionId,
    required this.collectionName,
    this.neighborhood,
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
              'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80', // Replace with dynamic image if available
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
          ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            child: SizedBox(
              height: 180,
              width: double.infinity,
              child: Image.network(
                'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80', // Placeholder
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Container(
                  color: PlanditColors.secondary,
                  child: const Center(
                    child: Icon(Icons.restaurant, size: 48, color: PlanditColors.mutedForeground),
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        item['name'] ?? 'Unknown Restaurant',
                        style: GoogleFonts.playfairDisplay(
                          fontSize: 22,
                          fontWeight: FontWeight.w400,
                          color: PlanditColors.foreground,
                        ),
                      ),
                    ),
                    const Icon(Icons.bookmark_border, color: PlanditColors.primary),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.restaurant, size: 14, color: PlanditColors.mutedForeground),
                    const SizedBox(width: 4),
                    Text(
                      item['cuisine'] ?? 'Cuisine',
                      style: const TextStyle(
                        fontSize: 13,
                        color: PlanditColors.mutedForeground,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  item['summary'] ?? 'No summary available.',
                  style: const TextStyle(
                    fontSize: 14,
                    color: PlanditColors.mutedForeground,
                    height: 1.5,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: PlanditColors.primary,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    child: const Text('View Details'),
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
