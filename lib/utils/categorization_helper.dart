// lib/utils/categorization_helper.dart

enum EateryCategory {
  restaurant,
  cafe,
  dessert,
  bar,
  bakery,
  other,
}

EateryCategory categorizePlace(List<dynamic> types) {
  final t = types.cast<String>();
  if (t.contains('restaurant')) return EateryCategory.restaurant;
  if (t.contains('cafe')) return EateryCategory.cafe;
  if (t.contains('bakery') || t.contains('dessert')) {
    return EateryCategory.dessert;
  }
  if (t.contains('bar') || t.contains('night_club')) return EateryCategory.bar;
  // add more rules as needed
  return EateryCategory.other;
}

// a convenience to get a display-friendly name
String eateryCategoryLabel(EateryCategory c) {
  switch (c) {
    case EateryCategory.restaurant:
      return 'Restaurants';
    case EateryCategory.cafe:
      return 'Cafés';
    case EateryCategory.dessert:
      return 'Dessert Places';
    case EateryCategory.bar:
      return 'Bars';
    case EateryCategory.bakery:
      return 'Bakeries';
    default:
      return 'Other';
  }
}
