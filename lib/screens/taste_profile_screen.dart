// lib/screens/taste_profile_screen.dart
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import '../services/user_preferences_service.dart';

class TasteProfileScreen extends StatefulWidget {
  const TasteProfileScreen({super.key});

  @override
  _TasteProfileScreenState createState() => _TasteProfileScreenState();
}

class _TasteProfileScreenState extends State<TasteProfileScreen> {
  final UserPreferencesService _prefsService = UserPreferencesService();
  final User? _user = FirebaseAuth.instance.currentUser;

  Map<String, Map<String, dynamic>> _allPlaces = {};
  Set<String> _selectedPlaceIds = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    if (_user == null) return;
    try {
      // Load visited places
      final query = await FirebaseFirestore.instance
          .collectionGroup('establishments')
          .where('uid', isEqualTo: _user.uid)
          .get();
      final unique = <String, Map<String, dynamic>>{};
      for (var doc in query.docs) {
        unique[doc.id] = doc.data();
      }
      // Load saved preferences
      final prefs = await _prefsService.fetchUserPreferences(_user.uid);

      setState(() {
        _allPlaces = unique;
        _selectedPlaceIds = prefs.toSet();
        _isLoading = false;
      });
    } catch (e) {
      print('Error initializing Taste Profile: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _toggleSelection(String placeId) {
    setState(() {
      if (_selectedPlaceIds.contains(placeId)) {
        _selectedPlaceIds.remove(placeId);
      } else {
        _selectedPlaceIds.add(placeId);
      }
    });
  }

  Future<void> _savePreferences() async {
    if (_user == null) return;
    await _prefsService.saveUserPreferences(
      userId: _user.uid,
      placeIds: _selectedPlaceIds.toList(),
    );
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Preferences updated!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Taste Profile')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Taste Profile')),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(8.0),
              children: _allPlaces.entries.map((entry) {
                final placeId = entry.key;
                final place = entry.value;
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                  child: ShadCard(
                    child: CheckboxListTile(
                      title: Text(place['name'] ?? 'Unnamed'),
                      subtitle: Text(place['vicinity'] ?? ''),
                      value: _selectedPlaceIds.contains(placeId),
                      onChanged: (_) => _toggleSelection(placeId),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: SizedBox(
              width: double.infinity,
              child: ShadButton(
                size: ShadButtonSize.lg,
                onPressed: _selectedPlaceIds.isEmpty ? null : _savePreferences,
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.save, size: 20),
                    SizedBox(width: 8),
                    Text('Save'),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
