// lib/services/user_preferences_service.dart
import 'package:cloud_firestore/cloud_firestore.dart';

class UserPreferencesService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  /// Save the list of place IDs the user selected as favorites.
  Future<void> saveUserPreferences({
    required String userId,
    required List<String> placeIds,
  }) async {
    await _firestore.collection('user_preferences').doc(userId).set({
      'preferences': placeIds,
      'updatedAt': FieldValue.serverTimestamp(),
    });
  }

  /// Fetches the stored preferences for this user.
  Future<List<String>> fetchUserPreferences(String userId) async {
    final doc =
        await _firestore.collection('user_preferences').doc(userId).get();
    if (doc.exists) {
      final data = doc.data()!;
      return List<String>.from(data['preferences'] ?? []);
    }
    return [];
  }
}
