import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../theme/plandit_design_system.dart';
import '../widgets/lemon8/lemon8_timeline_stop.dart';
import '../services/lemon8_image_service.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_auth/firebase_auth.dart';

class Lemon8DetailScreen extends StatefulWidget {
  final Map<String, dynamic> result;

  const Lemon8DetailScreen({super.key, required this.result});

  @override
  State<Lemon8DetailScreen> createState() => _Lemon8DetailScreenState();
}

class _Lemon8DetailScreenState extends State<Lemon8DetailScreen> {
  final Set<String> _lovedPlaceIds = {};
  late final List<dynamic> _stopsData;

  @override
  void initState() {
    super.initState();
    // Parse stops and fetch loved status
    _stopsData = _parseStops();
    _fetchLovedPlaces();
  }

  List<dynamic> _parseStops() {
    final rawEnriched = widget.result['enriched_itinerary_data'];
    Map<String, dynamic> enrichedData = {};

    if (rawEnriched is Map) {
      enrichedData = Map<String, dynamic>.from(rawEnriched);
    } else if (rawEnriched is String) {
      try {
        enrichedData = json.decode(rawEnriched) as Map<String, dynamic>;
      } catch (e) {
        print('ERROR: Failed to parse enriched_itinerary_data: $e');
      }
    }
    return enrichedData['stops'] is List ? (enrichedData['stops'] as List) : [];
  }

  Future<void> _fetchLovedPlaces() async {
    try {
      final supabase = Supabase.instance.client;
      final firebaseUser = FirebaseAuth.instance.currentUser;

      if (firebaseUser == null) return;
      final userId = firebaseUser.uid;

      final placeIds = _stopsData.map((stop) {
        Map<String, dynamic> stopMap = {};
        if (stop is Map) {
          stopMap = Map<String, dynamic>.from(stop);
        } else if (stop is String) {
          stopMap = {'place_name': stop};
        }
        return 'lemon8_${stopMap['place_name']?.toString().toLowerCase().replaceAll(' ', '_') ?? 'unknown'}';
      }).toList();

      if (placeIds.isEmpty) return;

      final response = await supabase
          .from('loved_places')
          .select('place_id')
          .eq('user_id', userId)
          .filter('place_id', 'in', '(${placeIds.join(',')})');

      if (mounted) {
        final lovedIds =
            (response as List).map((item) => item['place_id'] as String).toSet();
        setState(() {
          _lovedPlaceIds.addAll(lovedIds);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not load liked places: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      } else {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
    } catch (e) {
      debugPrint("Could not launch $url: $e");
    }
  }

  Future<void> _launchMaps(double? lat, double? lng, String label) async {
    final contextualLabel = "$label, NYC, USA";
    final query = Uri.encodeComponent(contextualLabel);
    String googleMapsUrl =
        'https://www.google.com/maps/search/?api=1&query=$query';

    if (lat != null && lng != null) {
      googleMapsUrl =
          'https://www.google.com/maps/search/?api=1&query=$query';
    }

    final appleMapsUrl = 'https://maps.apple.com/?q=$query';
    final geoUrl = 'geo:0,0?q=$query';

    try {
      await launchUrl(Uri.parse(googleMapsUrl),
          mode: LaunchMode.platformDefault);
    } catch (e) {
      try {
        await launchUrl(Uri.parse(appleMapsUrl),
            mode: LaunchMode.platformDefault);
      } catch (e2) {
        try {
          await launchUrl(Uri.parse(geoUrl));
        } catch (e3) {
          debugPrint("Could not launch maps: $e3");
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.result['title'] ?? 'Untitled';
    final description = widget.result['description'] ?? '';
    final url = widget.result['url'] ?? '';
    final imageUrl = Lemon8ImageService.getItineraryImage(widget.result);
    final city = widget.result['city'] ?? 'NYC / SOHO';
    
    // Data is now parsed in initState, so we can get price from there.
    final rawEnriched = widget.result['enriched_itinerary_data'];
     Map<String, dynamic> enrichedData = {};
    if (rawEnriched is Map) {
      enrichedData = Map<String, dynamic>.from(rawEnriched);
    } else if (rawEnriched is String) {
      try {
        enrichedData = json.decode(rawEnriched) as Map<String, dynamic>;
      } catch (e) {
        print('ERROR: Failed to parse enriched_itinerary_data: $e');
      }
    }
    final priceTier = enrichedData['price'] ?? '\$\$';


    return Scaffold(
      backgroundColor: PlanditColors.chicCream,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 400,
            pinned: true,
            leading: IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white),
              onPressed: () => Navigator.pop(context),
              style: IconButton.styleFrom(
                backgroundColor: Colors.black26,
              ),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(
                fit: StackFit.expand,
                children: [
                  Image.network(imageUrl, fit: BoxFit.cover),
                  Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          PlanditColors.chicCharcoal.withOpacity(0.8),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.4],
                      ),
                    ),
                  ),
                  Positioned(
                    bottom: 32,
                    left: 24,
                    right: 24,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          city.toUpperCase(),
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: 2,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          title,
                          style: GoogleFonts.playfairDisplay(
                            fontSize: 32,
                            fontWeight: FontWeight.w500,
                            color: Colors.white,
                            height: 1.1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildHeaderTag('THE EXPERIENCE'),
                      Text(
                        'PRICE: $priceTier',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: PlanditColors.mutedForeground,
                          letterSpacing: 1,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  if (description.isNotEmpty)
                    ...description.split('\n').map((para) {
                      final trimmedPara = para.trim();
                      if (trimmedPara.isEmpty) return const SizedBox(height: 8);
                      final isBullet = trimmedPara.startsWith('•') ||
                          trimmedPara.startsWith('-') ||
                          trimmedPara.startsWith('*');
                      return Padding(
                        padding: EdgeInsets.only(
                          bottom: 12.0,
                          left: isBullet ? 12.0 : 0.0,
                        ),
                        child: Text(
                          trimmedPara,
                          style: const TextStyle(
                            fontSize: 16,
                            color: PlanditColors.chicCharcoal,
                            height: 1.6,
                          ),
                        ),
                      );
                    }).toList(),
                  const SizedBox(height: 48),
                  _buildHeaderTag('THE TIMELINE'),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final rawStop = _stopsData[index];
                  Map<String, dynamic> stop = {};
                  if (rawStop is Map) {
                    stop = Map<String, dynamic>.from(rawStop);
                  } else if (rawStop is String) {
                    stop = {
                      'place_name': rawStop,
                      'category': 'Activity',
                      'notes':
                          'Visit this location as part of the itinerary.'
                    };
                  }

                  final placeId =
                      'lemon8_${stop['place_name']?.toString().toLowerCase().replaceAll(' ', '_') ?? 'unknown'}';
                  final isLoved = _lovedPlaceIds.contains(placeId);

                  return Lemon8TimelineStop(
                    category: stop['category'] ?? 'Activity',
                    duration: '${stop['duration_minutes'] ?? 60} MINS',
                    priceRange: stop['price_tier'] ?? '\$\$',
                    placeName: stop['place_name'] ?? 'Unknown Stop',
                    notes: stop['notes'] ?? 'No notes provided.',
                    isFirst: index == 0,
                    isLast: index == _stopsData.length - 1,
                    icon: _getIconForCategory(stop['category']),
                    isLoved: isLoved,
                    onMapTap: () => _launchMaps(
                      (stop['lat'] as num?)?.toDouble(),
                      (stop['lng'] as num?)?.toDouble(),
                      stop['place_name'] ?? 'NYC',
                    ),
                    onLoveTap: () async {
                      final isCurrentlyLoved = _lovedPlaceIds.contains(placeId);
                      
                      setState(() {
                        if (isCurrentlyLoved) {
                          _lovedPlaceIds.remove(placeId);
                        } else {
                          _lovedPlaceIds.add(placeId);
                        }
                      });

                      try {
                        final supabase = Supabase.instance.client;
                        final firebaseUser = FirebaseAuth.instance.currentUser;

                        if (firebaseUser == null) {
                          setState(() {
                             if (isCurrentlyLoved) {
                              _lovedPlaceIds.add(placeId);
                            } else {
                              _lovedPlaceIds.remove(placeId);
                            }
                          });
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Please sign in to save places'),
                                backgroundColor: Colors.orange,
                              ),
                            );
                          }
                          return;
                        }

                        final userId = firebaseUser.uid;

                        if (isCurrentlyLoved) {
                          await supabase
                              .from('loved_places')
                              .delete()
                              .match({'user_id': userId, 'place_id': placeId});
                        } else {
                          await supabase.from('loved_places').insert({
                            'user_id': userId,
                            'place_id': placeId,
                            'name': stop['place_name'] ?? 'Unknown',
                            'rating': '4.5',
                            'lat': stop['lat']?.toString() ?? '0',
                            'lng': stop['lng']?.toString() ?? '0',
                          });
                        }
                        
                      } catch (e) {
                         setState(() {
                             if (isCurrentlyLoved) {
                              _lovedPlaceIds.add(placeId);
                            } else {
                              _lovedPlaceIds.remove(placeId);
                            }
                          });
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('Failed to save: $e'),
                              backgroundColor: Colors.red,
                              duration: const Duration(seconds: 3),
                            ),
                          );
                        }
                      }
                    },
                  );
                },
                childCount: _stopsData.length,
              ),
            ),
          ),
          const SliverToBoxAdapter(
            child: SizedBox(height: 48),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderTag(String text) {
    return Text(
      text,
      style: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w800,
        color: PlanditColors.chicCharcoal.withOpacity(0.8),
        letterSpacing: 2,
      ),
    );
  }

  IconData _getIconForCategory(String? category) {
    final cat = category?.toLowerCase() ?? '';
    if (cat.contains('food') ||
        cat.contains('dinner') ||
        cat.contains('lunch')) {
      return Icons.restaurant;
    }
    if (cat.contains('wine') ||
        cat.contains('cocktail') ||
        cat.contains('drink') ||
        cat.contains('bar')) {
      return Icons.local_bar;
    }
    if (cat.contains('coffee') ||
        cat.contains('cafe') ||
        cat.contains('tea')) {
      return Icons.coffee;
    }
    return Icons.directions_walk;
  }
}
