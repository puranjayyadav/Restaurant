import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:url_launcher/url_launcher.dart';
import '../theme/plandit_design_system.dart';
import '../api_service.dart';
import 'loved_places_map_screen.dart';

class LovedPlacesScreen extends StatefulWidget {
  const LovedPlacesScreen({super.key});

  @override
  State<LovedPlacesScreen> createState() => _LovedPlacesScreenState();
}

class _LovedPlacesScreenState extends State<LovedPlacesScreen> {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _lovedPlaces = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchLovedPlaces();
  }

  Future<void> _fetchLovedPlaces() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() => _isLoading = false);
      return;
    }

    final places = await _apiService.getLovedPlaces(user.uid);
    if (mounted) {
      setState(() {
        _lovedPlaces = places;
        _isLoading = false;
      });
    }
  }

  Future<void> _removePlace(String placeId) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final success = await _apiService.unlovePlace(user.uid, placeId);
    if (success && mounted) {
      setState(() {
        _lovedPlaces.removeWhere((p) => p['place_id'] == placeId);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Removed from Loved Places')),
      );
    }
  }

  Future<void> _launchMaps(double? lat, double? lng, String label) async {
    final contextualLabel = "$label, NYC, USA";
    final query = Uri.encodeComponent(contextualLabel);
    String googleMapsUrl =
        'https://www.google.com/maps/search/?api=1&query=$query';

    if (lat != null && lng != null) {
      googleMapsUrl = 'https://www.google.com/maps/search/?api=1&query=$query';
    }

    final appleMapsUrl = 'https://maps.apple.com/?q=$query';
    final geoUrl = 'geo:0,0?q=$query';

    try {
      await launchUrl(
        Uri.parse(googleMapsUrl),
        mode: LaunchMode.platformDefault,
      );
    } catch (e) {
      try {
        await launchUrl(
          Uri.parse(appleMapsUrl),
          mode: LaunchMode.platformDefault,
        );
      } catch (e2) {
        try {
          await launchUrl(Uri.parse(geoUrl));
        } catch (e3) {
          debugPrint("Could not launch maps: $e3");
        }
      }
    }
  }

  void _openMapView() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => LovedPlacesMapScreen(places: _lovedPlaces),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PlanditColors.background,
      appBar: AppBar(
        title: Text(
          'LOVED PLACES',
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.5,
          ),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: PlanditColors.accentGold),
            )
          : _lovedPlaces.isEmpty
          ? _buildEmptyState()
          : Column(
              children: [
                // View on Maps button
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(20, 20, 20, 0),
                  child: ElevatedButton.icon(
                    onPressed: _openMapView,
                    icon: const Icon(Icons.map, size: 20),
                    label: Text(
                      'VIEW ON MAPS',
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.2,
                      ),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: PlanditColors.accentGold,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 2,
                    ),
                  ),
                ),
                // Places list
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.all(20),
                    itemCount: _lovedPlaces.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 16),
                    itemBuilder: (context, index) {
                      final place = _lovedPlaces[index];
                      return _buildPlaceCard(place);
                    },
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.favorite_border,
            size: 64,
            color: PlanditColors.secondaryText.withOpacity(0.3),
          ),
          const SizedBox(height: 16),
          Text(
            'No loved places yet',
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: PlanditColors.secondaryText,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Save spots you love to see them here',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: PlanditColors.secondaryText.withOpacity(0.6),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceCard(Map<String, dynamic> place) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: PlanditColors.border.withOpacity(0.5)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    place['name'] ?? 'Unknown Place',
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: PlanditColors.primaryText,
                    ),
                  ),
                  const SizedBox(height: 4),
                  if (place['rating'] != null)
                    Row(
                      children: [
                        const Icon(
                          Icons.star,
                          size: 14,
                          color: PlanditColors.accentGold,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          place['rating'].toString(),
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: PlanditColors.primaryText,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(
                Icons.map_outlined,
                color: PlanditColors.primaryText,
              ),
              onPressed: () {
                final lat = double.tryParse(place['lat']?.toString() ?? '');
                final lng = double.tryParse(place['lng']?.toString() ?? '');
                final name = place['name'] ?? 'Unknown Place';
                _launchMaps(lat, lng, name);
              },
            ),
            IconButton(
              icon: const Icon(
                Icons.favorite,
                color: Colors.orange,
              ), // Match design system love color
              onPressed: () => _removePlace(place['place_id']),
            ),
          ],
        ),
      ),
    );
  }
}
