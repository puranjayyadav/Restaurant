import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'dart:async';
import 'mode_selection_screen.dart';
import 'theme/design_system.dart';

class EstablishmentsScreen extends StatefulWidget {
  const EstablishmentsScreen({super.key});

  @override
  _EstablishmentsScreenState createState() => _EstablishmentsScreenState();
}

class _EstablishmentsScreenState extends State<EstablishmentsScreen> {
  bool isLoading = true;
  List<Map<String, dynamic>> establishments = [];
  // final ApiService apiService = ApiService(); // Commented out as it's no longer needed

  @override
  void initState() {
    super.initState();
    fetchUserEstablishments();
  }

  Future<void> fetchUserEstablishments() async {
    try {
      print("==== STARTING FIREBASE FETCH ====");
      print("Current User ID: ${FirebaseAuth.instance.currentUser?.uid}");

      final results = await FirebaseFirestore.instance
          .collectionGroup('establishments')
          .where('uid', isEqualTo: FirebaseAuth.instance.currentUser!.uid)
          .get();

      print("==== FIREBASE QUERY RESULTS ====");
      print("Number of documents found: ${results.docs.length}");

      final List<Map<String, dynamic>> fetchedEstablishments = results.docs
          .map((doc) => {
                ...doc.data(),
                'id': doc.id,
              })
          .toList();

      // // Print each establishment
      // for (var est in fetchedEstablishments) {
      //   print("==== ESTABLISHMENT ====");
      //   print("ID: ${est['id']}");
      //   print("Name: ${est['name']}");
      //   print("Address: ${est['vicinity']}");
      //   print("Price Range: ${est['price_level']}");
      //   print("Dining Style: ${est['diningStyle']}");
      //   print("Location: ${est['locationRegion']}");
      //   print("Features: ${est['specialFeatures']}");
      //   print("-------------------------");
      // }

      if (!mounted) return; // Check if widget is still mounted
      setState(() {
        establishments = fetchedEstablishments;
        isLoading = false;
      });
    } catch (e) {
      print("==== ERROR FETCHING ESTABLISHMENTS ====");
      print("Error details: $e");
      print("Error stack trace: ${StackTrace.current}");
      if (!mounted) return; // Check if widget is still mounted
      setState(() {
        isLoading = false;
      });
    }
  }

  // This method will work after adding the url_launcher package
  void _openMap(Map<String, dynamic> place) {
    // Show a not implemented message until url_launcher is added
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Add url_launcher package to enable this feature'),
        duration: Duration(seconds: 2),
      ),
    );

    // TODO: Uncomment this after adding url_launcher package
    try {
      // Try to open using coordinates first (most accurate)
      if (place['geometry'] != null && place['geometry']['location'] != null) {
        final lat = place['geometry']['location']['lat'];
        final lng = place['geometry']['location']['lng'];
        final Uri url = Uri.parse(
            'https://www.openstreetmap.org/?mlat=$lat&mlon=$lng&zoom=15');
        launchUrl(url, mode: LaunchMode.externalApplication);
        return;
      }

      // Fallback to name search
      final query = Uri.encodeComponent(place['name'] as String? ?? '');
      final Uri url =
          Uri.parse('https://www.openstreetmap.org/search?query=$query');
      launchUrl(url, mode: LaunchMode.externalApplication);
    } catch (e) {
      print('Could not launch map: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not open maps'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  // This method will work after adding the url_launcher package
  void _openWebsite(Map<String, dynamic> place) {
    // Show a not implemented message until url_launcher is added
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Add url_launcher package to enable this feature'),
        duration: Duration(seconds: 2),
      ),
    );

    /*
    // TODO: Uncomment this after adding url_launcher package
    try {
      // Try to use website field first
      if (place['website'] != null) {
        final Uri url = Uri.parse(place['website']);
        launchUrl(url, mode: LaunchMode.externalApplication);
        return;
      }
      
      // Try to use url field next
      if (place['url'] != null) {
        final Uri url = Uri.parse(place['url']);
        launchUrl(url, mode: LaunchMode.externalApplication);
        return;
      }
      
      // Fallback to opening map
      _openMap(place);
    } catch (e) {
      print('Could not open website: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not open website'),
          duration: Duration(seconds: 2),
        ),
      );
    }
    */
  }

  /*
  Future<void> fetchFullGooglePayload() async {
    try {
      // Example coordinates - replace with actual user location
      final double lat = 37.7749;
      final double lon = -122.4194;
      
      print("==== FETCHING FULL GOOGLE PLACES API PAYLOAD ====");
      final fullData = await apiService.fetchFullGooglePlacesPayload(lat, lon);
      print("==== FETCHED ${fullData['results']?.length ?? 0} PLACES ====");
    } catch (e) {
      print("==== ERROR FETCHING GOOGLE PLACES API ====");
      print("Error details: $e");
    }
  }
  */

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Your Establishments"),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                  builder: (context) => const ModeSelectionScreen()),
            );
          },
        ),
        /* 
        actions: [
          IconButton(
            icon: const Icon(Icons.api),
            onPressed: fetchFullGooglePayload,
            tooltip: 'Fetch full Google API payload',
          ),
        ],
        */
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : establishments.isEmpty
              ? const Center(child: Text("No establishments found."))
              : ListView.builder(
                  itemCount: establishments.length,
                  itemBuilder: (context, index) {
                    final est = establishments[index];
                    return Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      child: ShadCard(
                        child: InkWell(
                          onTap: () => _showActionSheet(context, est),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Image section - full width image at the top
                              _buildPlaceImage(est),
                              // Details section
                              Padding(
                                padding: const EdgeInsets.all(12.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    // Restaurant name and price level
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceBetween,
                                      children: [
                                        Expanded(
                                          child: Text(
                                            est['name'] ?? 'No Name',
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 18,
                                            ),
                                          ),
                                        ),
                                        if (est['price_level'] != null)
                                          Text(
                                            _formatPriceLevel(
                                                est['price_level']),
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 16,
                                            ),
                                          ),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      est['vicinity'] ?? 'No Address',
                                      style: TextStyle(
                                          color: const Color(0xFF616161)),
                                    ),
                                    const SizedBox(height: 8),

                                    // Restaurant details in a more organized way
                                    if (est['diningStyle'] != null)
                                      Text(
                                        'Dining Style: ${_formatDiningStyle(est['diningStyle'])}',
                                        style: const TextStyle(fontSize: 14),
                                      ),

                                    if (est['locationRegion'] != null)
                                      Text(
                                        'Location: ${est['locationRegion']}',
                                        style: const TextStyle(fontSize: 14),
                                      ),

                                    // Types section
                                    if (est['types'] != null &&
                                        est['types'] is List &&
                                        (est['types'] as List).isNotEmpty)
                                      Padding(
                                        padding: const EdgeInsets.only(top: 12),
                                        child: Wrap(
                                          spacing: 6,
                                          runSpacing: 4,
                                          children: _buildTypeChips(
                                              est['types'] as List),
                                        ),
                                      ),

                                    // Features section
                                    if ((est['specialFeatures'] as List?)
                                            ?.isNotEmpty ??
                                        false)
                                      Padding(
                                        padding: const EdgeInsets.only(top: 12),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            const Text(
                                              'Features:',
                                              style: TextStyle(
                                                  fontWeight: FontWeight.bold),
                                            ),
                                            const SizedBox(height: 4),
                                            Wrap(
                                              spacing: 6,
                                              runSpacing: 4,
                                              children: _buildFeatureChips(
                                                  est['specialFeatures']
                                                      as List),
                                            ),
                                          ],
                                        ),
                                      ),

                                    // Action buttons
                                    Padding(
                                      padding: const EdgeInsets.only(top: 16),
                                      child: Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.end,
                                        children: [
                                          TextButton.icon(
                                            icon: const Icon(Icons.map),
                                            label: const Text('View on Map'),
                                            onPressed: () => _openMap(est),
                                            style: TextButton.styleFrom(
                                              foregroundColor: Colors.blue,
                                            ),
                                          ),
                                          const SizedBox(width: 12),
                                          if (est['website'] != null ||
                                              est['url'] != null)
                                            TextButton.icon(
                                              icon: const Icon(Icons.public),
                                              label: const Text('Website'),
                                              onPressed: () =>
                                                  _openWebsite(est),
                                              style: TextButton.styleFrom(
                                                foregroundColor: Colors.green,
                                              ),
                                            ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
    );
  }

  Widget _buildPlaceImage(Map<String, dynamic> place) {
    // Check if photos array exists and has entries
    if (place['photos'] != null &&
        place['photos'] is List &&
        (place['photos'] as List).isNotEmpty) {
      final photo = (place['photos'] as List)[0];

      // Check if we have a direct photo_url (rare)
      if (photo['photo_url'] != null) {
        return ClipRRect(
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(8),
            topRight: Radius.circular(8),
          ),
          child: Image.network(
            photo['photo_url'],
            width: double.infinity,
            height: 200,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return _buildPlaceholderImage();
            },
          ),
        );
      }

      // Wikimedia Commons provides direct photo URLs
      final photoUrl = photo['url'] as String?;
      if (photoUrl != null && photoUrl.isNotEmpty) {
        return ClipRRect(
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(8),
            topRight: Radius.circular(8),
          ),
          child: Image.network(
            photoUrl,
            width: double.infinity,
            height: 200,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return _buildPlaceholderImage();
            },
          ),
        );
      }
    }

    // If no photos or if they couldn't be accessed, show placeholder
    return _buildPlaceholderImage();
  }

  Widget _buildPlaceholderImage() {
    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(
        color: const Color(0xFFEEEEEE),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(8),
          topRight: Radius.circular(8),
        ),
      ),
      child: const Icon(
        Icons.restaurant,
        size: 50,
        color: Color(0xFF9E9E9E),
      ),
    );
  }

  List<Widget> _buildTypeChips(List<dynamic> types) {
    // Filter out common/generic types
    final List<String> filteredTypes = types
        .map((type) => type.toString())
        .where((type) => !_isCommonType(type))
        .toList();

    // If all types were filtered out, show at least one meaningful type
    if (filteredTypes.isEmpty && types.isNotEmpty) {
      filteredTypes.add(types.first.toString());
    }

    // Show only first 3 types
    final int maxTypesToShow = 3;
    final int typesToShow = filteredTypes.length > maxTypesToShow
        ? maxTypesToShow
        : filteredTypes.length;

    List<Widget> chips = [];

    for (var i = 0; i < typesToShow; i++) {
      String displayType = filteredTypes[i];
      // Convert snake_case to Title Case
      displayType = displayType
          .split('_')
          .map((word) => word.isEmpty
              ? ''
              : '${word[0].toUpperCase()}${word.substring(1)}')
          .join(' ');

      chips.add(Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.blue.shade50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.blue.shade100),
        ),
        child: Text(
          displayType,
          style: TextStyle(
            fontSize: 10,
            color: Colors.blue.shade700,
          ),
        ),
      ));
    }

    if (filteredTypes.length > maxTypesToShow) {
      chips.add(Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Text(
          '+${filteredTypes.length - maxTypesToShow}',
          style: TextStyle(
            fontSize: 10,
            color: Colors.grey.shade600,
          ),
        ),
      ));
    }

    return chips;
  }

  // Helper method to check if a type is common/generic
  bool _isCommonType(String type) {
    const List<String> commonTypes = [
      'food',
      'restaurant',
      'establishment',
      'point_of_interest',
      'place',
      'store',
      'business',
      'meal_takeaway',
      'meal_delivery'
    ];

    return commonTypes.contains(type.toLowerCase());
  }

  void _showActionSheet(BuildContext context, Map<String, dynamic> place) {
    showModalBottomSheet(
      context: context,
      builder: (BuildContext context) {
        return SafeArea(
          child: Wrap(
            children: <Widget>[
              ListTile(
                leading: const Icon(Icons.place),
                title: const Text('Open in Google Maps'),
                onTap: () {
                  Navigator.pop(context);
                  _openMap(place);
                },
              ),
              if (place['website'] != null || place['url'] != null)
                ListTile(
                  leading: const Icon(Icons.open_in_browser),
                  title: const Text('Open Website'),
                  onTap: () {
                    Navigator.pop(context);
                    _openWebsite(place);
                  },
                ),
              ListTile(
                leading: const Icon(Icons.close),
                title: const Text('Cancel'),
                onTap: () {
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  String _formatPriceLevel(dynamic priceLevel) {
    // Convert numeric price level to dollar signs
    if (priceLevel is num) {
      int level = priceLevel.toInt();
      if (level >= 1 && level <= 4) {
        return List.filled(level, '\$').join();
      }
      return '\$' * level; // Fallback
    }
    // If it's already a string of dollar signs
    else if (priceLevel is String) {
      if (priceLevel.contains('\$')) {
        return priceLevel;
      }
      // Try to parse as number if it's a numeric string
      try {
        int level = int.parse(priceLevel);
        return '\$' * level;
      } catch (_) {
        return priceLevel; // Just return the original string
      }
    }
    // For any other case, return a safe default
    return '';
  }

  String _formatDiningStyle(dynamic diningStyle) {
    if (diningStyle == null) return '';

    if (diningStyle is String) {
      // Convert SNAKE_CASE to Title Case
      return diningStyle
          .split('_')
          .map((word) => word.isEmpty
              ? ''
              : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
          .join(' ');
    } else if (diningStyle is List) {
      // Format list of dining styles
      return diningStyle
          .map((style) => style is String
              ? style
                  .split('_')
                  .map((word) => word.isEmpty
                      ? ''
                      : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
                  .join(' ')
              : style.toString())
          .join(', ');
    } else {
      // For any other case, convert to string
      return diningStyle.toString();
    }
  }

  List<Widget> _buildFeatureChips(List<dynamic> features) {
    // Filter out common/generic features
    final List<String> filteredFeatures = features
        .map((feature) => feature.toString())
        .where((feature) => !_isCommonFeature(feature))
        .toList();

    // If all features were filtered out, show at least one meaningful feature
    if (filteredFeatures.isEmpty && features.isNotEmpty) {
      filteredFeatures.add(features.first.toString());
    }

    // Show only first 3 features
    final int maxFeaturesToShow = 3;
    final int featuresToShow = filteredFeatures.length > maxFeaturesToShow
        ? maxFeaturesToShow
        : filteredFeatures.length;

    List<Widget> chips = [];

    for (var i = 0; i < featuresToShow; i++) {
      String displayFeature = filteredFeatures[i];
      // Convert snake_case to Title Case
      displayFeature = displayFeature
          .split('_')
          .map((word) => word.isEmpty
              ? ''
              : '${word[0].toUpperCase()}${word.substring(1)}')
          .join(' ');

      chips.add(Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Text(
          displayFeature,
          style: TextStyle(
            fontSize: 10,
            color: Colors.grey.shade600,
          ),
        ),
      ));
    }

    if (filteredFeatures.length > maxFeaturesToShow) {
      chips.add(Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Text(
          '+${filteredFeatures.length - maxFeaturesToShow}',
          style: TextStyle(
            fontSize: 10,
            color: Colors.grey.shade600,
          ),
        ),
      ));
    }

    return chips;
  }

  // Helper method to check if a feature is common/generic
  bool _isCommonFeature(String feature) {
    const List<String> commonFeatures = [
      'food',
      'restaurant',
      'establishment',
      'point_of_interest',
      'place',
      'store',
      'business',
      'meal_takeaway',
      'meal_delivery'
    ];

    return commonFeatures.contains(feature.toLowerCase());
  }
}
