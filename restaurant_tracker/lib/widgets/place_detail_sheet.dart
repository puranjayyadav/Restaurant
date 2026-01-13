import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

void showPlaceDetail(BuildContext context, Map<String, dynamic> place) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true, // Allows full height
    backgroundColor: Colors.transparent,
    builder: (context) => PlaceDetailSheet(place: place),
  );
}

class PlaceDetailSheet extends StatelessWidget {
  final Map<String, dynamic> place;

  const PlaceDetailSheet({super.key, required this.place});

  @override
  Widget build(BuildContext context) {
    // Extract real data with safe fallbacks
    final title = place['name'] ?? 'Unknown Place';
    final imageUrl = place['image_url'] ?? "https://images.unsplash.com/photo-1547592166-23acbe3a624b?q=80&w=800";
    final description = place['ai_insight'] ?? "A local favorite for discovery. We selected this because it perfectly matches the vibe of your current neighborhood exploration.";
    final tags = (place['categories'] as List?)?.take(3).map((e) => e.toString()).toList() ?? ["Trending", "Top Rated"];
    final rating = "${place['rating'] ?? '4.5'} ★ (Lemon8 Favorite)";
    final price = place['price_range'] ?? '\$\$';
    final walkTime = place['walk_time'] ?? '3 mins';

    return DraggableScrollableSheet(
      initialChildSize: 0.85, // Starts at 85% height
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (_, controller) {
        return Container(
          decoration: BoxDecoration(
            color: const Color(0xFF121212), // Deep Dark Background
            borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.5), blurRadius: 50, spreadRadius: 10),
            ],
          ),
          child: Stack(
            children: [
              // 1. SCROLLABLE CONTENT
              ListView(
                controller: controller,
                padding: EdgeInsets.zero,
                children: [
                  // A. HERO IMAGE
                  Stack(
                    children: [
                      Hero(
                        tag: 'place_image_$title', 
                        child: ClipRRect(
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
                          child: Image.network(
                            imageUrl,
                            height: 350,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) => Container(
                              height: 350,
                              color: Colors.grey[900],
                              child: const Icon(Icons.image_not_supported, color: Colors.white24, size: 50),
                            ),
                          ),
                        ),
                      ),
                      // Gradient Overlay for text protection
                      Positioned.fill(
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                Colors.black.withOpacity(0.3),
                                Colors.transparent,
                                Colors.black.withOpacity(0.8), // Darken bottom of image
                              ],
                              stops: const [0.0, 0.5, 1.0],
                            ),
                          ),
                        ),
                      ),
                      // Close Button
                      Positioned(
                        top: 16,
                        right: 16,
                        child: GestureDetector(
                          onTap: () => Navigator.pop(context),
                          child: Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.black.withOpacity(0.5),
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white.withOpacity(0.2)),
                            ),
                            child: const Icon(Icons.close, color: Colors.white, size: 20),
                          ),
                        ),
                      ),
                    ],
                  ),

                  // B. CONTENT BODY
                  Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Title & Tags
                        Text(
                          title,
                          style: GoogleFonts.playfairDisplay(
                            fontSize: 32,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            height: 1.1,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          children: tags.map((tag) => _buildTag(tag)).toList(),
                        ),
                        
                        const SizedBox(height: 32),

                        // "Why" Section (The AI Insight)
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.05),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white.withOpacity(0.1)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.auto_awesome, color: Colors.amber, size: 16),
                                  const SizedBox(width: 8),
                                  Text(
                                    "WHY WE PICKED THIS",
                                    style: GoogleFonts.dmSans(
                                      color: Colors.amber,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 10,
                                      letterSpacing: 1.0,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Text(
                                description,
                                style: GoogleFonts.dmSans(
                                  color: Colors.white.withOpacity(0.9),
                                  fontSize: 15,
                                  height: 1.5,
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 32),

                        // Stats Row
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            _buildInfoColumn("Price", price, Icons.payments, Colors.greenAccent),
                            _buildInfoColumn("Rating", rating, Icons.star, Colors.amber),
                            _buildInfoColumn("Walk", walkTime, Icons.directions_walk, Colors.blueAccent),
                          ],
                        ),
                        
                        const SizedBox(height: 32),
                        
                        // Time & Description (Rich Text)
                        Text(
                          "ABOUT THE SPOT",
                          style: GoogleFonts.dmSans(
                            color: Colors.white.withOpacity(0.4),
                            fontWeight: FontWeight.bold,
                            fontSize: 10,
                            letterSpacing: 1.2,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          place['description'] ?? "This spot is highly recommended by locals for its unique atmosphere and top-tier service. It's an essential stop in any itinerary focused on authentic neighborhood discovery.",
                          style: GoogleFonts.dmSans(
                            color: Colors.white70,
                            fontSize: 15,
                            height: 1.6,
                          ),
                        ),
                        
                        // Extra padding for the sticky bottom bar
                        const SizedBox(height: 140), 
                      ],
                    ),
                  ),
                ],
              ),

              // 2. STICKY BOTTOM ACTIONS
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                    child: Container(
                      padding: const EdgeInsets.fromLTRB(24, 20, 24, 40),
                      decoration: BoxDecoration(
                        color: const Color(0xFF121212).withOpacity(0.85),
                        border: Border(top: BorderSide(color: Colors.white.withOpacity(0.1))),
                      ),
                      child: Row(
                        children: [
                          // Swap Button
                          Expanded(
                            flex: 1,
                            child: OutlinedButton(
                              onPressed: () {
                                Navigator.pop(context);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    backgroundColor: Colors.grey[900],
                                    content: Text(
                                      "Finding alternatives for $title...",
                                      style: const TextStyle(color: Colors.white),
                                    ),
                                  )
                                );
                              },
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.white,
                                side: BorderSide(color: Colors.white.withOpacity(0.3)),
                                padding: const EdgeInsets.symmetric(vertical: 16),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              ),
                              child: const Text("Swap", style: TextStyle(fontWeight: FontWeight.w600)),
                            ),
                          ),
                          const SizedBox(width: 16),
                          // Navigate Button
                          Expanded(
                            flex: 2,
                            child: ElevatedButton.icon(
                              onPressed: () {},
                              icon: const Icon(Icons.near_me),
                              label: const Text("Navigate"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.white,
                                foregroundColor: Colors.black,
                                padding: const EdgeInsets.symmetric(vertical: 16),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // Helper Widgets
  Widget _buildTag(String text) {
    return Chip(
      label: Text(text, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
      backgroundColor: Colors.white.withOpacity(0.1),
      side: BorderSide.none,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
    );
  }

  Widget _buildInfoColumn(String label, String value, IconData icon, Color iconColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: iconColor),
            const SizedBox(width: 6),
            Text(label, style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
          ],
        ),
        const SizedBox(height: 6),
        Text(value, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
