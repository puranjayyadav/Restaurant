import 'dart:math';

/// Utility functions for itinerary calculations and formatting

/// Calculate distance between two coordinates using Haversine formula
/// Returns distance in kilometers
double calculateDistance(double lat1, double lon1, double lat2, double lon2) {
  const double earthRadiusKm = 6371.0;
  
  double dLat = _degreesToRadians(lat2 - lat1);
  double dLon = _degreesToRadians(lon2 - lon1);
  
  double a = sin(dLat / 2) * sin(dLat / 2) +
      cos(_degreesToRadians(lat1)) *
          cos(_degreesToRadians(lat2)) *
          sin(dLon / 2) *
          sin(dLon / 2);
  
  double c = 2 * atan2(sqrt(a), sqrt(1 - a));
  return earthRadiusKm * c;
}

double _degreesToRadians(double degrees) {
  return degrees * (pi / 180);
}

/// Estimate walking time in minutes based on distance
/// Assumes average walking speed of 5 km/h
int estimateWalkTime(double distanceKm) {
  return ((distanceKm / 5.0) * 60).round();
}

/// Format distance for display
String formatDistance(double distanceKm) {
  if (distanceKm < 1.0) {
    return '${(distanceKm * 1000).round()}m';
  } else {
    return '${distanceKm.toStringAsFixed(1)}km';
  }
}

/// Check if two locations are within the specified radius
bool isWithinRadius(
  double lat1,
  double lon1,
  double lat2,
  double lon2,
  double maxKm,
) {
  return calculateDistance(lat1, lon1, lat2, lon2) <= maxKm;
}

/// Format walk time for display
String formatWalkTime(int minutes) {
  if (minutes < 1) {
    return '< 1 min';
  } else if (minutes < 60) {
    return '$minutes min';
  } else {
    int hours = minutes ~/ 60;
    int mins = minutes % 60;
    if (mins == 0) {
      return '$hours hr';
    } else {
      return '$hours hr $mins min';
    }
  }
}

