import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:restaurant_tracker/api_service.dart';
import 'package:restaurant_tracker/widgets/density_heatmap_widget.dart';

/// Standalone screen for density heatmap exploration
class DensityHeatmapScreen extends StatelessWidget {
  final String baseUrl;

  const DensityHeatmapScreen({
    Key? key,
    this.baseUrl = '', // Default to empty, will be handled in build
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Neighborhood Discovery'),
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.black87,
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => _showInfoDialog(context),
          ),
        ],
      ),
      body: DensityHeatmapWidget(
        center: const LatLng(40.7216, -74.0047), // SoHo, NYC
        baseUrl: baseUrl.isNotEmpty ? baseUrl : ApiService.baseUrl,
        onCellTap: (cellId, placeCount) {
          // Handle cell tap - could navigate to place list
          print('Tapped cell: $cellId with $placeCount places');
        },
      ),
    );
  }

  void _showInfoDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.lightbulb_outline, color: Colors.amber),
            SizedBox(width: 12),
            Text('How It Works'),
          ],
        ),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'The heatmap shows where places cluster in your city:',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 12),
              _InfoItem(
                color: Color(0xFFD32F2F),
                label: 'Red zones',
                description: 'High density - lots of spots to explore',
              ),
              _InfoItem(
                color: Color(0xFFFF9800),
                label: 'Orange zones',
                description: 'Medium density - good options',
              ),
              _InfoItem(
                color: Color(0xFF81C784),
                label: 'Green zones',
                description: 'Low density - fewer spots',
              ),
              SizedBox(height: 16),
              Text(
                'Tap a zone to see details and explore places!',
                style: TextStyle(fontStyle: FontStyle.italic),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Got it!'),
          ),
        ],
      ),
    );
  }
}

class _InfoItem extends StatelessWidget {
  final Color color;
  final String label;
  final String description;

  const _InfoItem({
    required this.color,
    required this.label,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 20,
            height: 20,
            margin: const EdgeInsets.only(top: 2),
            decoration: BoxDecoration(
              color: color.withOpacity(0.6),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: Colors.white.withOpacity(0.5)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                Text(
                  description,
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 13,
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
