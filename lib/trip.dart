import 'package:cloud_firestore/cloud_firestore.dart';

class Trip {
  final String sessionId;
  final String startAddress;
  final String endAddress;
  final DateTime date;
  final DateTime sessionDate;

  Trip({
    required this.sessionId,
    required this.startAddress,
    required this.endAddress,
    required this.date,
    required this.sessionDate,
  });

  factory Trip.fromDocument(DocumentSnapshot<Map<String, dynamic>> doc) {
    final data = doc.data()!;
    return Trip(
      sessionId: doc.id,
      startAddress: data['startAddress'] ?? '',
      endAddress: data['endAddress'] ?? '',
      // If 'date' is not provided, default to now.
      date: data.containsKey('date')
          ? DateTime.parse(data['date'])
          : DateTime.now(),
      sessionDate: (data['sessionDate'] as Timestamp).toDate(),
    );
  }
}
