import 'package:flutter/material.dart';

enum StopTimeOfDay { morning, brunch, lunch, afternoon, dinner, lateNight }

enum StopCrowdLevel { empty, bustling, lineOutDoor, sardineCan }

class TimelineStop {
  final String id;
  String? placeId;
  String? name;
  String? address;
  DateTime? timestamp;
  StopTimeOfDay timeOfDay;
  int costPerPerson; // 1-4
  int aestheticRating; // 1-5 sparkles
  StopCrowdLevel crowdLevel;
  String? bestShotLocation;
  String? mustOrder;
  String? overhypedItem;
  String? tweetReview;
  List<String> photoPaths;
  Map<String, dynamic> contextualAnswers;
  String? category; // e.g., 'Coffee Shop', 'Bar'

  TimelineStop({
    required this.id,
    this.placeId,
    this.name,
    this.address,
    this.timestamp,
    this.timeOfDay = StopTimeOfDay.afternoon,
    this.costPerPerson = 2,
    this.aestheticRating = 3,
    this.crowdLevel = StopCrowdLevel.bustling,
    this.bestShotLocation,
    this.mustOrder,
    this.overhypedItem,
    this.tweetReview,
    this.photoPaths = const [],
    this.contextualAnswers = const {},
    this.category,
  });

  TimelineStop copyWith({
    String? id,
    String? placeId,
    String? name,
    String? address,
    DateTime? timestamp,
    StopTimeOfDay? timeOfDay,
    int? costPerPerson,
    int? aestheticRating,
    StopCrowdLevel? crowdLevel,
    String? bestShotLocation,
    String? mustOrder,
    String? overhypedItem,
    String? tweetReview,
    List<String>? photoPaths,
    Map<String, dynamic>? contextualAnswers,
    String? category,
  }) {
    return TimelineStop(
      id: id ?? this.id,
      placeId: placeId ?? this.placeId,
      name: name ?? this.name,
      address: address ?? this.address,
      timestamp: timestamp ?? this.timestamp,
      timeOfDay: timeOfDay ?? this.timeOfDay,
      costPerPerson: costPerPerson ?? this.costPerPerson,
      aestheticRating: aestheticRating ?? this.aestheticRating,
      crowdLevel: crowdLevel ?? this.crowdLevel,
      bestShotLocation: bestShotLocation ?? this.bestShotLocation,
      mustOrder: mustOrder ?? this.mustOrder,
      overhypedItem: overhypedItem ?? this.overhypedItem,
      tweetReview: tweetReview ?? this.tweetReview,
      photoPaths: photoPaths ?? this.photoPaths,
      contextualAnswers: contextualAnswers ?? this.contextualAnswers,
      category: category ?? this.category,
    );
  }
}

class ItineraryDraft {
  String title;
  String? heroImagePath;
  List<String> vibeTags;
  List<TimelineStop> stops;

  ItineraryDraft({
    this.title = '',
    this.heroImagePath,
    this.vibeTags = const [],
    this.stops = const [],
  });
}
