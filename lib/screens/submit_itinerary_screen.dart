import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../api_service.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

class SubmitItineraryScreen extends StatefulWidget {
  final List<dynamic> itinerary;
  final String location;
  final String neighborhood;
  final double latitude;
  final double longitude;
  final List<String> categories;

  const SubmitItineraryScreen({
    Key? key,
    required this.itinerary,
    required this.location,
    required this.neighborhood,
    required this.latitude,
    required this.longitude,
    required this.categories,
  }) : super(key: key);

  @override
  State<SubmitItineraryScreen> createState() => _SubmitItineraryScreenState();
}

class _SubmitItineraryScreenState extends State<SubmitItineraryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  bool _isSubmitting = false;
  final ApiService _apiService = ApiService();

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submitItinerary() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      ShadToaster.of(context).show(
        const ShadToast.destructive(
          title: Text('Authentication required'),
          description: Text('Please sign in to submit itineraries'),
        ),
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      // Convert itinerary to serializable format
      final itineraryData = widget.itinerary.map((item) {
        // Limit photos to first 2 to reduce payload size
        final photos = (item['photos'] as List<dynamic>?)
                ?.take(2)
                .map((photo) {
                  if (photo is Map) {
                    // Handle both formats: photo_reference or url
                    // Only include essential fields to reduce payload size
                    final photoMap = <String, dynamic>{};
                    if (photo['photo_reference'] != null) {
                      photoMap['photo_reference'] = photo['photo_reference'];
                    }
                    if (photo['url'] != null) {
                      photoMap['url'] = photo['url'];
                    }
                    // Skip height/width to reduce size
                    return photoMap;
                  }
                  return <String, dynamic>{};
                })
                .where((p) => p.isNotEmpty)
                .toList() ??
            [];

        return {
          'slot_name': item['slot_name']?.toString() ?? '',
          'start_time': item['start_time']?.toString() ?? '',
          'place_name': item['place_name']?.toString() ?? '',
          'place_id': item['place_id']?.toString() ?? '',
          'address': item['address']?.toString() ?? '',
          'latitude': (item['latitude'] is num) ? item['latitude'] : 0.0,
          'longitude': (item['longitude'] is num) ? item['longitude'] : 0.0,
          'types': item['types'] ?? [],
          'photos': photos,
          'distance_from_previous': item['distance_from_previous'],
          'estimated_walk_time': item['estimated_walk_time'],
          'is_custom': item['is_custom'] ?? false,
        };
      }).toList();

      final result = await _apiService.submitPublicItinerary(
        userId: user.uid,
        userName: user.displayName ?? 'Anonymous',
        userPhotoUrl: user.photoURL,
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
        location: widget.location,
        latitude: widget.latitude,
        longitude: widget.longitude,
        neighborhood: widget.neighborhood,
        categories: widget.categories,
        items: itineraryData,
      );

      if (!mounted) return;

      if (result != null) {
        ShadToaster.of(context).show(
          const ShadToast(
            title: Text('Success!'),
            description: Text(
                'Your itinerary has been submitted and is pending approval.'),
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      print('ERROR submitting itinerary: $e');
      if (!mounted) return;
      final errorMessage = e.toString().replaceFirst('Exception: ', '');
      ShadToaster.of(context).show(
        ShadToast.destructive(
          title: const Text('Error'),
          description: Text(errorMessage),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Submit to Public Feed'),
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Preview Section
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Itinerary Preview',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text('Location: ${widget.location}'),
                      Text('Places: ${widget.itinerary.length}'),
                      Text('Categories: ${widget.categories.join(", ")}'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              // Title Field
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Title *',
                  hintText: 'e.g., "Perfect Day in Manhattan"',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter a title';
                  }
                  if (value.trim().length < 5) {
                    return 'Title must be at least 5 characters';
                  }
                  return null;
                },
                maxLength: 100,
              ),
              const SizedBox(height: 16),
              // Description Field
              TextFormField(
                controller: _descriptionController,
                decoration: const InputDecoration(
                  labelText: 'Description *',
                  hintText: 'Describe what makes this itinerary special...',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter a description';
                  }
                  if (value.trim().length < 20) {
                    return 'Description must be at least 20 characters';
                  }
                  return null;
                },
                maxLines: 5,
                maxLength: 500,
              ),
              const SizedBox(height: 24),
              // Submit Button
              ElevatedButton(
                onPressed: _isSubmitting ? null : _submitItinerary,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isSubmitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Submit for Approval'),
              ),
              const SizedBox(height: 8),
              Text(
                'Your itinerary will be reviewed before going public.',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
