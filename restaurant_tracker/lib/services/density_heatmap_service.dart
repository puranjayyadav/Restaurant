import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:flutter/material.dart';

/// Service for fetching density heatmap data from the backend
class DensityHeatmapService {
  final String baseUrl;

  DensityHeatmapService({required this.baseUrl});

  /// Fetch heatmap GeoJSON for a given location and filters
  Future<Map<String, dynamic>> fetchHeatmap({
    required double lat,
    required double lng,
    String? vibe,
    String? category,
    double? minRating,
    double gridSize = 0.008,
    int gridCount = 11,
  }) async {
    final queryParams = {
      'lat': lat.toString(),
      'lng': lng.toString(),
      if (vibe != null) 'vibe': vibe,
      if (category != null) 'category': category,
      if (minRating != null) 'min_rating': minRating.toString(),
      'grid_size': gridSize.toString(),
      'grid_count': gridCount.toString(),
    };

    final uri = Uri.parse('$baseUrl/api/neighborhoods/density/')
        .replace(queryParameters: queryParams);

    try {
      final response = await http.get(uri, headers: {
        'Accept': 'application/json',
      }).timeout(
        const Duration(seconds: 15),
      );

      if (response.statusCode == 200) {
        return json.decode(utf8.decode(response.bodyBytes));
      } else {
        throw Exception('Failed to load heatmap: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Fetch a structured itinerary for a specific hotspot (Just-in-Time)
  Future<Map<String, dynamic>> fetchHotspotItinerary({
    required double lat,
    required double lng,
    String vibe = 'Trendy',
    double radiusKm = 1.5,
  }) async {
    final queryParams = {
      'lat': lat.toString(),
      'lng': lng.toString(),
      'vibe': vibe,
      'radius_km': radiusKm.toString(),
    };

    final uri = Uri.parse('$baseUrl/api/neighborhoods/itinerary/')
        .replace(queryParameters: queryParams);

    try {
      final response = await http.get(uri, headers: {
        'Accept': 'application/json',
      }).timeout(
        const Duration(seconds: 20),
      );

      if (response.statusCode == 200) {
        return json.decode(utf8.decode(response.bodyBytes));
      } else {
        final error = json.decode(utf8.decode(response.bodyBytes));
        throw Exception(error['error'] ?? 'Failed to load itinerary');
      }
    } catch (e) {
      throw Exception('Vibe Check failed: $e');
    }
  }

  /// Convert GeoJSON feature to PolygonData for flutter_map
  static HeatmapPolygon geojsonToPolygon(Map<String, dynamic> feature) {
    final coords = feature['geometry']['coordinates'][0] as List;
    final props = feature['properties'];

    // Convert [lng, lat] to LatLng(lat, lng)
    // Convert [lng, lat] to LatLng(lat, lng)
    final points = coords.map((coord) {
      return LatLng(
        double.tryParse(coord[1].toString()) ?? 0.0,
        double.tryParse(coord[0].toString()) ?? 0.0,
      );
    }).toList();

    // Parse hex color
    final colorHex = props['color'].substring(1); // Remove '#'
    final color = Color(int.parse('FF$colorHex', radix: 16));
    
    // Safely parse properties which might be strings from backend
    final opacity = double.tryParse(props['opacity'].toString()) ?? 0.6;
    final densityScore = double.tryParse(props['density_score'].toString()) ?? 0.0;
    final avgRating = double.tryParse(props['avg_rating'].toString()) ?? 0.0;
    final placeCount = int.tryParse(props['place_count'].toString()) ?? 0;

    return HeatmapPolygon(
      points: points,
      color: color.withOpacity(opacity),
      borderColor: Colors.white.withOpacity(0.3),
      borderWidth: 1.0,
      densityScore: densityScore,
      placeCount: placeCount,
      avgRating: avgRating,
      cellId: props['id'] as String,
      vibe: props['vibe'] as String?,
      notes: (props['notes'] as List?)?.map((n) => n.toString()).toList() ?? [],
    );
  }

  /// Convert entire GeoJSON FeatureCollection to list of polygons
  static List<HeatmapPolygon> geojsonToPolygons(Map<String, dynamic> geojson) {
    final features = geojson['features'] as List;
    return features.map((feature) => geojsonToPolygon(feature)).toList();
  }
}

/// Data class representing a heatmap polygon with metadata
class HeatmapPolygon {
  final List<LatLng> points;
  final Color color;
  final Color borderColor;
  final double borderWidth;
  final double densityScore;
  final int placeCount;
  final double avgRating;
  final String cellId;
  final String? vibe;
  final List<String> notes; // Crowd-sourced notes for this cell

  HeatmapPolygon({
    required this.points,
    required this.color,
    required this.borderColor,
    required this.borderWidth,
    required this.densityScore,
    required this.placeCount,
    required this.avgRating,
    required this.cellId,
    this.vibe,
    this.notes = const [],
  });
}
