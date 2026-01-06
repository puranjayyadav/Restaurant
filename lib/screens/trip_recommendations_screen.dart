import 'package:flutter/material.dart';
import '../api_service.dart';
import 'package:url_launcher/url_launcher.dart';

class TripRecommendationsScreen extends StatefulWidget {
  final String tripId;
  final String tripName;

  const TripRecommendationsScreen({
    super.key,
    required this.tripId,
    required this.tripName,
  });

  @override
  State<TripRecommendationsScreen> createState() =>
      _TripRecommendationsScreenState();
}

class _TripRecommendationsScreenState extends State<TripRecommendationsScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> _recommendations = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadRecommendations();
  }

  Future<void> _loadRecommendations() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });

      final recommendations =
          await _apiService.fetchTripRecommendations(widget.tripId);

      setState(() {
        _recommendations = recommendations;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Failed to load recommendations: $e';
        _isLoading = false;
      });
    }
  }

  void _openMaps(String placeName, String address) async {
    final query = Uri.encodeComponent('$placeName, $address');
    final url = Uri.parse('https://www.openstreetmap.org/search?query=$query');

    try {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open maps for $placeName')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Recommendations for ${widget.tripName}'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: _loadRecommendations,
                        child: const Text('Try Again'),
                      ),
                    ],
                  ),
                )
              : _recommendations.isEmpty
                  ? const Center(
                      child:
                          Text('No recommendations available for this trip.'),
                    )
                  : ListView.builder(
                      itemCount: _recommendations.length,
                      itemBuilder: (context, index) {
                        final recommendation = _recommendations[index];
                        return _buildRecommendationCard(recommendation);
                      },
                    ),
    );
  }

  Widget _buildRecommendationCard(dynamic recommendation) {
    final name = recommendation['name'] as String;
    final address = recommendation['address'] as String;
    final priceRange = recommendation['price_range'] as String;
    final diningStyle = recommendation['dining_style'] as String;

    // Convert dining style from backend format (FINE_DINING) to display format (Fine Dining)
    final displayDiningStyle = diningStyle
        .split('_')
        .map((word) =>
            word.substring(0, 1).toUpperCase() +
            word.substring(1).toLowerCase())
        .join(' ');

    // Get features if available
    List<dynamic> features = [];
    if (recommendation.containsKey('features')) {
      features = recommendation['features'] as List<dynamic>;
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: 3,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    name,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Text(
                  priceRange,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              address,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 8),
            Text(
              'Dining Style: $displayDiningStyle',
              style: const TextStyle(fontSize: 14),
            ),
            if (features.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Features:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: features
                    .map((feature) => Chip(
                          label: Text(
                            feature['feature_type']
                                .toString()
                                .split('_')
                                .map((word) =>
                                    word.substring(0, 1).toUpperCase() +
                                    word.substring(1).toLowerCase())
                                .join(' '),
                            style: const TextStyle(fontSize: 12),
                          ),
                          backgroundColor: Colors.blue.shade100,
                        ))
                    .toList(),
              ),
            ],
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                ElevatedButton(
                  onPressed: () => _openMaps(name, address),
                  child: const Text('View on Map'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
