import 'package:cloud_firestore/cloud_firestore.dart';

class FirebaseService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  /// Creates a new session document using today's date as the session ID.
  /// You can now pass a required userId and an optional startAddress.
  Future<String> createSession(
      {required String userId, String? startAddress}) async {
    // Use the current date (yyyy-MM-dd) as a session ID.
    String sessionId = DateTime.now().toIso8601String().split('T').first;
    await _firestore.collection('sessions').doc(sessionId).set({
      'userId': userId,
      'startAddress': startAddress ?? '',
      'createdAt': FieldValue.serverTimestamp(),
    });
    return sessionId;
  }

  /// Saves a list of [] into the session's subcollection.
  Future<void> saveEstablishments(
      String sessionId, List<dynamic> establishments) async {
    CollectionReference sessionRef = _firestore
        .collection('sessions')
        .doc(sessionId)
        .collection('establishments');
    for (var place in establishments) {
      // Ensure each place has a 'place_id'
      String placeId = place['place_id'];
      await sessionRef.doc(placeId).set(place, SetOptions(merge: true));
    }
  }
}
