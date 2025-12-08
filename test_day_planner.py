import datetime
import math # For _calculate_distance if you bring it in or RestaurantRecommender uses it
import firebase_admin
from firebase_admin import credentials, firestore # or 'db' for Realtime Database
import json
from collections import defaultdict

# --- Assume your classes are defined here or imported ---
# Option 1: If recommendation.py and day_planner.py are in the same directory
# from recommendation import RestaurantRecommender 
# from day_planner import DayPlanner # (assuming you move DayPlanner to its own file)

# Option 2: For simplicity in this example, let's define them inline (you'd import normally)

def initialize_firebase():
    # IMPORTANT: Replace 'path/to/your/serviceAccountKey.json' with the actual path
    cred_path = 'creds/restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json'
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully.")
        return True
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")
        print("Please ensure 'firebase-admin' is installed and the service account key path is correct.")
        return False

class Establishment: # Mock/Simplified Establishment for testing
    def __init__(self, id, name, type, latitude, longitude, operating_hours, features=None, 
                 dining_style=None, price_range=None, types=None, category=None):
        self.id = id
        self.name = name
        self.type = type # e.g., "CAFE", "RESTAURANT_LUNCH", "PARK", "MUSEUM"
        self.latitude = latitude
        self.longitude = longitude
        self.operating_hours = operating_hours # e.g., {"Mon": ["09:00-18:00"], "Tue": ["09:00-22:00"]}
        self.features_data = features if features else [] # Simplified
        self.dining_style = dining_style or "CASUAL" # Placeholder for recommender
        self.price_range = price_range or "$$" # Placeholder for recommender
        self.types = types if types else [] # Added for Google Places data
        self.category = category # Added for Google Places data

    def __repr__(self):
        return f"<Establishment: {self.name} ({self.type})>"
    
    # Mock for recommender.get_establishment_vector compatibility
    @property
    def features(self):
        # Simple implementation without complex nested classes
        feature_set = set(self.features_data)
        
        class SimpleFeatureQuerySet:
            def __init__(self, feature_list):
                self.feature_list = feature_list
                
            def all(self):
                return [{'feature_type': f} for f in self.feature_list]
                
            def filter(self, feature_type):
                return SimpleFilterResult(feature_type in feature_set)
        
        class SimpleFilterResult:
            def __init__(self, result):
                self._result = result
                
            def exists(self):
                return self._result
        
        return SimpleFeatureQuerySet(self.features_data)


class RestaurantRecommender:
    def __init__(self):
        self.feature_columns = [] 
        # Mock: In a real scenario, this would be initialized from all establishments
        self.known_establishment_features = set()
        self.known_dining_styles = set()
        self.known_price_ranges = set()


    def _initialize_features(self, establishments_data):
        """Simplified initialize_features for console testing."""
        if not establishments_data:
            print("Warning: No establishment data to initialize features.")
            self.feature_columns = []
            return False

        for est_data in establishments_data:
            self.known_dining_styles.add(est_data.get('dining_style', 'CASUAL'))
            self.known_price_ranges.add(est_data.get('price_range', '$$'))
            for f_type in est_data.get('features', []):
                self.known_establishment_features.add(f_type)
        
        self.feature_columns = (
            [f"dining_{s}" for s in self.known_dining_styles] +
            [f"price_{p}" for p in self.known_price_ranges] +
            [f"feature_{f}" for f in self.known_establishment_features]
        )
        if not self.feature_columns:
             print("Warning: Feature columns are empty after initialization.")
        return True

    def get_user_vector(self, user_id):
        # Mock user vector: prioritize cafes and parks for testing
        if not self.feature_columns: self._initialize_features([]) # Ensure feature_columns exists
        
        user_vector = [0] * len(self.feature_columns)
        for i, feature_name in enumerate(self.feature_columns):
            if feature_name == "feature_CAFE_RELATED": # Made-up feature
                 user_vector[i] = 0.5
            if feature_name == "feature_OUTDOOR_SEATING":
                 user_vector[i] = 0.3
            if feature_name == "dining_CASUAL": # Assuming CAFE is a dining style
                 user_vector[i] = 0.6
        
        # Normalize
        vec_sum = sum(user_vector)
        if vec_sum > 0:
            user_vector = [v / vec_sum for v in user_vector]
        return user_vector

    def get_establishment_vector(self, establishment):
        if not self.feature_columns: self._initialize_features([])

        est_vector = [0] * len(self.feature_columns)
        for i, feature_name in enumerate(self.feature_columns):
            if feature_name == f"dining_{establishment.dining_style}":
                est_vector[i] = 1
            elif feature_name == f"price_{establishment.price_range}":
                est_vector[i] = 1
            elif feature_name.startswith('feature_'):
                feat = feature_name[8:]
                if establishment.features.filter(feature_type=feat).exists():
                    est_vector[i] = 1
        return est_vector

    def cosine_similarity(self, vector_a, vector_b):
        if not vector_a or not vector_b or len(vector_a) != len(vector_b): return 0
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        magnitude_a = math.sqrt(sum(a * a for a in vector_a))
        magnitude_b = math.sqrt(sum(b * b for b in vector_b))
        if magnitude_a == 0 or magnitude_b == 0:
            return 0
        return dot_product / (magnitude_a * magnitude_b)

    def _calculate_distance(self, lat1, lon1, lat2, lon2): # Haversine
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a)) # Earth radius in km

# --- Your DayPlanner Class (Copied and pasted, then modified) ---
class DayPlanner:
    def __init__(self, establishments_data, user_trips_data):
        self.recommender = RestaurantRecommender()
        # Initialize features in recommender based on mock establishments
        # This is a bit of a chicken-and-egg, adjust as needed.
        # We need features to be known by the recommender *before* establishments are fully processed by DayPlanner
        # Or, DayPlanner passes all raw establishment data to recommender first.
        
        # Let's assume mock_establishments_data is a list of dicts for Recommender init
        # And then we convert to Establishment objects for DayPlanner
        self.recommender._initialize_features(establishments_data)


        self.establishments = self._load_establishments(establishments_data)
        self.user_trips = self._load_user_trips(user_trips_data)
        self._initialize_day_slots_and_rules()
        self.MAX_RADIUS_KM = 30 # Define here for testing

    def _load_establishments(self, source_data): # Source data is now list of dicts
        print(f"Loading {len(source_data)} establishments...")
        loaded_establishments = []
        for est_data in source_data:
            try:
                loaded_establishments.append(
                    Establishment(
                        id=est_data['id'],
                        name=est_data.get('name', f"Unnamed-{est_data['id']}"),
                        type=est_data.get('type', 'RESTAURANT_LUNCH'),
                        latitude=est_data.get('latitude', 0),
                        longitude=est_data.get('longitude', 0),
                        operating_hours=est_data.get('operating_hours', {}),
                        features=est_data.get('features', []),
                        dining_style=est_data.get('dining_style', 'CASUAL'),
                        price_range=est_data.get('price_range', '$$'),
                        types=est_data.get('types', []),
                        category=est_data.get('category', None)
                    )
                )
            except Exception as e:
                print(f"Error creating Establishment from data: {e}")
                print(f"Problematic data: {est_data}")
                
        print(f"Loaded {len(loaded_establishments)} establishment objects.")
        return loaded_establishments


    def _load_user_trips(self, source_data): # Placeholder
        print(f"Loading user trips: {len(source_data)} trips")
        return source_data # Just returning the mock data for now

    def _initialize_day_slots_and_rules(self):
        self.day_slots_config = {
            "morning": {"name": "morning", "start_time": "09:00", "end_time": "11:00", "allowed_types": ["CAFE", "BREAKFAST_SPOT"]},
            "mid_day": {"name": "mid_day", "start_time": "11:00", "end_time": "14:00", "allowed_types": ["RESTAURANT_LUNCH", "PARK"]},
            "afternoon": {"name": "afternoon", "start_time": "14:00", "end_time": "17:00", "allowed_types": ["MUSEUM", "LIBRARY", "CAFE"]},
            "evening": {"name": "evening", "start_time": "17:00", "end_time": "20:00", "allowed_types": ["RESTAURANT_DINNER", "BAR"]},
        }
        print("Day slots initialized.")


    def _get_user_preferences_for_slot(self, user_id, slot_name, context):
        # Using the mock get_user_vector from recommender for now
        # In future, this could be more sophisticated, e.g., fetch preferences specific to 'slot_name' activities
        print(f"Getting user preferences for slot: {slot_name} (User ID: {user_id})")
        return self.recommender.get_user_vector(user_id)

    def _is_open(self, establishment, datetime_to_check, slot_start_time_str):
        # Simplified check: always open for testing.
        # Implement actual logic based on establishment.operating_hours and datetime_to_check
        day_of_week = datetime_to_check.strftime("%a") # Mon, Tue, etc.
        
        if day_of_week not in establishment.operating_hours:
            return False # Closed on this day

        current_time_obj = datetime_to_check.time()

        for time_range_str in establishment.operating_hours[day_of_week]:
            open_str, close_str = time_range_str.split('-')
            open_time = datetime.datetime.strptime(open_str, "%H:%M").time()
            close_time = datetime.datetime.strptime(close_str, "%H:%M").time()
            
            if open_time <= current_time_obj < close_time:
                # Optional: check if it will remain open for a minimum duration from slot_start_time
                # slot_start_datetime = datetime.datetime.combine(datetime_to_check.date(), datetime.datetime.strptime(slot_start_time_str, "%H:%M").time())
                # if (datetime.datetime.combine(datetime_to_check.date(), close_time) - slot_start_datetime).total_seconds() / 3600 >= 1: # open for at least 1 hour from slot start
                return True
        return False


    def _get_datetime_for_slot_start(self, date_obj, time_str):
        # Helper to combine a date object with a time string (HH:MM)
        time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
        return datetime.datetime.combine(date_obj, time_obj)

    def _recommend_for_slot(self, user_id, slot_config, user_location_tuple, contextual_dt):
        """
        Generate recommendations for a specific time slot.
        
        Args:
            user_id: The user's ID to generate recommendations for
            slot_config: Dictionary with slot configuration (name, start_time, end_time, allowed_types)
            user_location_tuple: (latitude, longitude) - starting point for distance calculation
            contextual_dt: Datetime object representing when this slot will occur
            
        Returns:
            List of establishment objects, sorted by relevance & filtered for the slot
        """
        print(f"\nRecommending for slot: {slot_config['name']} at {contextual_dt}")
        
        # 1. Get preferences relevant to this slot (might vary by time)
        slot_preferences = self._get_user_preferences_for_slot(user_id, slot_config['name'], contextual_dt)
        
        # 2. Filter for establishments:
        # - Open during the slot's timeframe
        # - Of an appropriate type for the slot
        # - Within a reasonable distance
        
        day_of_week = contextual_dt.strftime("%a")  # Returns 'Mon', 'Tue', etc.
        slot_start_hour = int(slot_config["start_time"].split(":")[0])
        slot_end_hour = int(slot_config["end_time"].split(":")[0]) 
        
        # Check if slot crosses midnight
        crosses_midnight = slot_end_hour < slot_start_hour
        
        # Get candidate establishments
        candidate_establishments = []
        
        # Print the allowed types for debugging
        print(f" Establishments available: {len(self.establishments)}")
        
        # Debug: Print the first 5 establishments to check their data
        print(f" Sample establishments (first 5):")
        for i, est in enumerate(self.establishments[:5]):
            print(f"  {i+1}. {est.name} (Type: {est.type})")
            if hasattr(est, 'types') and est.types:
                print(f"     Types: {est.types}")
            if hasattr(est, 'category') and est.category:
                print(f"     Category: {est.category}")
        
        # Track count of establishments rejected by each filter
        type_rejected = 0
        hours_rejected = 0
        distance_rejected = 0
        
        for establishment in self.establishments:
            # Type check - first filter
            establishment_type_match = False
            
            # First check if we have a direct match with allowed types
            if hasattr(establishment, 'type') and establishment.type in slot_config["allowed_types"]:
                establishment_type_match = True
            
            # If no direct match, try to check if any types field entries or category fields match
            if not establishment_type_match:
                # Check 'types' field which is often a list in Google Places data
                if hasattr(establishment, 'types') and isinstance(establishment.types, list):
                    types_lower = [t.lower() for t in establishment.types if isinstance(t, str)]
                    for allowed_type in slot_config["allowed_types"]:
                        # Try various mappings
                        if allowed_type == 'CAFE' and ('cafe' in types_lower or 'bakery' in types_lower or 'coffee' in types_lower):
                            establishment_type_match = True
                            break
                        elif allowed_type == 'RESTAURANT_LUNCH' and 'restaurant' in types_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'RESTAURANT_DINNER' and 'restaurant' in types_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'BAR' and ('bar' in types_lower or 'night_club' in types_lower):
                            establishment_type_match = True
                            break
                        elif allowed_type == 'PARK' and 'park' in types_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'MUSEUM' and 'museum' in types_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'LIBRARY' and 'library' in types_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'BREAKFAST_SPOT' and ('cafe' in types_lower or 'bakery' in types_lower or 'restaurant' in types_lower or 'coffee' in types_lower):
                            establishment_type_match = True
                            break
                
                # Check category field which might be directly usable
                if not establishment_type_match and hasattr(establishment, 'category') and isinstance(establishment.category, str):
                    category_lower = establishment.category.lower()
                    for allowed_type in slot_config["allowed_types"]:
                        if allowed_type == 'CAFE' and ('cafe' in category_lower or 'coffee' in category_lower):
                            establishment_type_match = True
                            break
                        elif allowed_type == 'RESTAURANT_LUNCH' and 'restaurant' in category_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'RESTAURANT_DINNER' and 'restaurant' in category_lower:
                            establishment_type_match = True
                            break
                        elif allowed_type == 'BAR' and ('bar' in category_lower or 'pub' in category_lower):
                            establishment_type_match = True
                            break
            
            if not establishment_type_match:
                type_rejected += 1
                continue
                
            # Check if establishment is open during this slot's hours
            is_open_during_slot = False
            
            if day_of_week in establishment.operating_hours:
                for hours_range in establishment.operating_hours[day_of_week]:
                    # Parse opening hours
                    try:
                        open_close = hours_range.split("-")
                        open_hour = int(open_close[0].split(":")[0])
                        close_hour = int(open_close[1].split(":")[0])
                        
                        # Handle cases crossing midnight
                        if close_hour < open_hour:  # Place closes after midnight
                            if slot_start_hour >= open_hour or slot_end_hour <= close_hour:
                                is_open_during_slot = True
                                break
                        # Normal case
                        elif open_hour <= slot_start_hour and close_hour >= slot_end_hour:
                            is_open_during_slot = True
                            break
                    except (ValueError, IndexError):
                        # If we can't parse properly, assume it's open
                        is_open_during_slot = True
                        break
            else:
                # No hours for this day? For testing purposes, let's assume it's open
                is_open_during_slot = True
            
            if not is_open_during_slot:
                hours_rejected += 1
                continue
                
            # Check if establishment is within reasonable distance
            # For simplicity using straight-line distance; in real app would use route distance
            if hasattr(self.recommender, '_calculate_distance'):
                user_lat, user_lng = user_location_tuple
                est_lat, est_lng = establishment.latitude, establishment.longitude
                
                distance = self.recommender._calculate_distance(user_lat, user_lng, est_lat, est_lng)
                if distance > self.MAX_RADIUS_KM:
                    distance_rejected += 1
                    continue
            
            # If we got here, establishment is a candidate for this slot
            candidate_establishments.append(establishment)
        
        # Print filter rejection stats
        print(f" Filter stats: Type rejected: {type_rejected}, Hours rejected: {hours_rejected}, Distance rejected: {distance_rejected}")
        
        # If no candidates, return empty list
        if not candidate_establishments:
            print(f" Found 0 candidates for slot '{slot_config['name']}'.")
            return []
            
        # 3. Rank establishments by relevance 
        # Get vectors for each candidate and calculate similarity
        establishment_scores = []
        
        for est in candidate_establishments:
            est_vector = self.recommender.get_establishment_vector(est)
            similarity = self.recommender.cosine_similarity(slot_preferences, est_vector)
            establishment_scores.append((est, similarity))
        
        # Sort by score, highest first
        ranked_establishments = sorted(establishment_scores, key=lambda x: x[1], reverse=True)
        
        # Display top recommendations for debugging
        print(f" Found {len(candidate_establishments)} candidates for slot '{slot_config['name']}'.")
        top_results = [(est.name, score) for est, score in ranked_establishments[:3]]
        print(f" Top 3 for slot '{slot_config['name']}': {top_results}")
        
        # Return just the establishments, not the scores
        return [est for est, _ in ranked_establishments]


    def generate_day_plan(self, user_id, target_date_obj, user_start_location_tuple):
        print(f"\n--- Generating Day Plan for User {user_id} on {target_date_obj.strftime('%Y-%m-%d')} ---")
        timeline = []
        last_location_tuple = user_start_location_tuple
        used_establishments = set()  # Track establishments already used in the plan

        # Ensure slots are processed in chronological order
        sorted_slots = sorted(self.day_slots_config.items(), key=lambda item: datetime.datetime.strptime(item[1]["start_time"], "%H:%M").time())

        for slot_name, config in sorted_slots:
            contextual_dt_for_slot = self._get_datetime_for_slot_start(target_date_obj, config["start_time"])
            
            recommendations_for_slot = self._recommend_for_slot(user_id, config, last_location_tuple, contextual_dt_for_slot)
            
            # Filter out already used establishments
            fresh_recommendations = [est for est in recommendations_for_slot if est.id not in used_establishments]
            
            if fresh_recommendations:
                chosen_activity = fresh_recommendations[0]  # Choose the first (highest ranked) fresh recommendation
                used_establishments.add(chosen_activity.id)  # Mark as used
                
                timeline.append({
                    "slot_name": slot_name,
                    "start_time": config["start_time"],
                    "activity_name": chosen_activity.name,
                    "activity_type": chosen_activity.type,
                    "location": (chosen_activity.latitude, chosen_activity.longitude)
                })
                last_location_tuple = (chosen_activity.latitude, chosen_activity.longitude)
                print(f"  Added to plan: {chosen_activity.name} for {slot_name}")
            elif recommendations_for_slot:
                # If we have recommendations but they're all used, use the first one anyway
                chosen_activity = recommendations_for_slot[0]
                timeline.append({
                    "slot_name": slot_name,
                    "start_time": config["start_time"],
                    "activity_name": chosen_activity.name + " (revisit)",
                    "activity_type": chosen_activity.type,
                    "location": (chosen_activity.latitude, chosen_activity.longitude)
                })
                last_location_tuple = (chosen_activity.latitude, chosen_activity.longitude)
                print(f"  Added to plan (revisit): {chosen_activity.name} for {slot_name}")
            else:
                print(f"  No suitable activity found for slot: {slot_name}")
        
        print("--- Day Plan Generation Complete ---")
        return timeline

def parse_operating_hours(hours_data):
    """
    Parse hours data from Firebase into the format expected by DayPlanner:
    {"Mon": ["09:00-18:00"], "Tue": ["09:00-18:00", "19:00-22:00"], ...}
    
    Adjust this function based on how your hours data is stored in Firebase.
    """
    days_map = {
        "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", 
        "thursday": "Thu", "friday": "Fri", "saturday": "Sat", "sunday": "Sun"
    }
    
    result = {}
    
    # This is just an example - adjust to your actual data structure
    if isinstance(hours_data, dict):
        for day, hours in hours_data.items():
            day_short = days_map.get(day.lower(), day[:3])
            
            if isinstance(hours, list):
                result[day_short] = hours
            elif isinstance(hours, dict) and 'open' in hours and 'close' in hours:
                result[day_short] = [f"{hours['open']}-{hours['close']}"]
            elif isinstance(hours, str):
                # Handle "9am-5pm" type strings
                result[day_short] = [hours]
    
    # Ensure all days have at least empty lists
    for day in days_map.values():
        if day not in result:
            result[day] = []
            
    return result

def check_firebase_collections():
    """List all collections in the Firebase database to help diagnose connection issues."""
    db = firestore.client()
    
    # List all top-level collections
    collections = db.collections()
    print("Available top-level collections in Firebase:")
    for collection in collections:
        doc_count = len(list(collection.stream()))
        print(f" - {collection.id} (contains {doc_count} documents)")
        
        # If it's the sessions collection, check for subcollections
        if collection.id == 'sessions':
            # Get a few session documents
            session_docs = list(collection.limit(5).stream())
            for session_doc in session_docs:
                print(f"   Checking subcollections in session: {session_doc.id}")
                # List subcollections in this session
                subcollections = session_doc.reference.collections()
                for subcoll in subcollections:
                    subcount = len(list(subcoll.stream()))
                    print(f"    - {subcoll.id} (contains {subcount} documents)")
                    
                    # If there are establishments, peek at the first one
                    if subcoll.id == 'establishments' and subcount > 0:
                        print(f"      Sample establishment data:")
                        sample_est = next(subcoll.limit(1).stream())
                        sample_data = sample_est.to_dict()
                        # Print a few key fields
                        for key in ['name', 'type', 'category', 'location', 'coordinates', 'features']:
                            if key in sample_data:
                                print(f"      {key}: {sample_data[key]}")
    
    return [coll.id for coll in collections]

def fetch_establishments_from_firebase():
    """Fetch establishment data from Firebase.
    
    This function attempts to get establishment data from the subcollections within session documents,
    with a fallback to looking for top-level collections.
    """
    establishments_data = []
    db = firestore.client()
    
    # Try to get establishments from sessions collection
    try:
        # Try the session subcollections
        sessions_ref = db.collection('sessions')
        sessions = list(sessions_ref.stream())
        print(f"Found {len(sessions)} session documents")
        
        # For each session, try to access the establishments subcollection
        for session in sessions:
            session_id = session.id
            print(f"Checking session {session_id} for establishments subcollection")
            
            try:
                # Access establishments subcollection
                establishments_ref = sessions_ref.document(session_id).collection('establishments').stream()
                
                session_establishments = []
                sample_count = 0
                for doc in establishments_ref:
                    est_dict = doc.to_dict()
                    est_dict['id'] = doc.id
                    
                    # Extract location data from geometry field
                    if 'geometry' in est_dict and isinstance(est_dict['geometry'], dict):
                        if 'location' in est_dict['geometry']:
                            location = est_dict['geometry']['location']
                            if isinstance(location, dict):
                                if 'lat' in location and 'lng' in location:
                                    est_dict['latitude'] = location['lat']
                                    est_dict['longitude'] = location['lng']
                                elif 'latitude' in location and 'longitude' in location:
                                    est_dict['latitude'] = location['latitude']
                                    est_dict['longitude'] = location['longitude']
                    
                    # If we still don't have location data, try other possible fields
                    if 'latitude' not in est_dict or 'longitude' not in est_dict:
                        if 'coordinates' in est_dict:
                            if hasattr(est_dict['coordinates'], 'latitude') and hasattr(est_dict['coordinates'], 'longitude'):
                                est_dict['latitude'] = est_dict['coordinates'].latitude
                                est_dict['longitude'] = est_dict['coordinates'].longitude
                            elif isinstance(est_dict['coordinates'], dict):
                                if 'latitude' in est_dict['coordinates'] and 'longitude' in est_dict['coordinates']:
                                    est_dict['latitude'] = est_dict['coordinates']['latitude']
                                    est_dict['longitude'] = est_dict['coordinates']['longitude']
                                elif 'lat' in est_dict['coordinates'] and 'lng' in est_dict['coordinates']:
                                    est_dict['latitude'] = est_dict['coordinates']['lat']
                                    est_dict['longitude'] = est_dict['coordinates']['lng']
                        elif 'location' in est_dict and isinstance(est_dict['location'], dict):
                            if 'latitude' in est_dict['location'] and 'longitude' in est_dict['location']:
                                est_dict['latitude'] = est_dict['location']['latitude']
                                est_dict['longitude'] = est_dict['location']['longitude']
                            elif 'lat' in est_dict['location'] and 'lng' in est_dict['location']:
                                est_dict['latitude'] = est_dict['location']['lat']
                                est_dict['longitude'] = est_dict['location']['lng']
                        elif 'lat' in est_dict and 'lng' in est_dict:
                            est_dict['latitude'] = est_dict['lat']
                            est_dict['longitude'] = est_dict['lng']
                    
                    # Print first few successful establishments
                    if 'latitude' in est_dict and 'longitude' in est_dict:
                        if sample_count < 2:
                            print(f"\nSuccessfully processed establishment in {session_id}:")
                            print(f"  Name: {est_dict.get('name', 'Unknown')}")
                            print(f"  Type: {est_dict.get('type', est_dict.get('category', 'Unknown'))}")
                            print(f"  Location: ({est_dict['latitude']}, {est_dict['longitude']})")
                            sample_count += 1
                        
                        # Handle establishment type
                        if 'type' not in est_dict:
                            if 'category' in est_dict:
                                # Map categories to our type system
                                category = est_dict['category'].lower() if isinstance(est_dict['category'], str) else ''
                                category_to_type = {
                                    'restaurant': 'RESTAURANT_LUNCH',
                                    'cafe': 'CAFE',
                                    'bar': 'BAR',
                                    'museum': 'MUSEUM',
                                    'park': 'PARK',
                                    'library': 'LIBRARY',
                                }
                                est_dict['type'] = category_to_type.get(category, 'RESTAURANT_LUNCH')
                            # Check types field if available
                            elif 'types' in est_dict and isinstance(est_dict['types'], list):
                                types = [t.lower() for t in est_dict['types'] if isinstance(t, str)]
                                if 'cafe' in types:
                                    est_dict['type'] = 'CAFE'
                                elif 'bar' in types:
                                    est_dict['type'] = 'BAR'
                                elif 'museum' in types:
                                    est_dict['type'] = 'MUSEUM'
                                elif 'park' in types:
                                    est_dict['type'] = 'PARK'
                                elif 'library' in types:
                                    est_dict['type'] = 'LIBRARY'
                                elif 'restaurant' in types:
                                    est_dict['type'] = 'RESTAURANT_LUNCH'
                                else:
                                    est_dict['type'] = 'RESTAURANT_LUNCH'
                            else:
                                # Default type
                                est_dict['type'] = 'RESTAURANT_LUNCH'
                        
                        # Handle features
                        if 'features' not in est_dict:
                            # Try to extract from types or categories if available
                            est_dict['features'] = []
                            if 'types' in est_dict and isinstance(est_dict['types'], list):
                                est_dict['features'].extend(est_dict['types'])
                            
                        # Ensure features is a list of strings
                        if est_dict.get('features') is None:
                            est_dict['features'] = []
                        elif isinstance(est_dict['features'], dict):
                            est_dict['features'] = [k for k, v in est_dict['features'].items() if v]
                        elif not isinstance(est_dict['features'], list):
                            est_dict['features'] = [str(est_dict['features'])]
                        else:
                            est_dict['features'] = [str(f) for f in est_dict['features']]
                        
                        # Handle operating hours
                        if 'operating_hours' not in est_dict:
                            if 'opening_hours' in est_dict:
                                if isinstance(est_dict['opening_hours'], dict):
                                    # Handle different opening_hours formats
                                    # For now, just create a simple default schedule
                                    est_dict['operating_hours'] = {
                                        "Mon": ["09:00-17:00"], "Tue": ["09:00-17:00"], 
                                        "Wed": ["09:00-17:00"], "Thu": ["09:00-17:00"], 
                                        "Fri": ["09:00-17:00"], "Sat": ["09:00-17:00"],
                                        "Sun": ["09:00-17:00"]
                                    }
                                else:
                                    est_dict['operating_hours'] = parse_operating_hours(est_dict['opening_hours'])
                            else:
                                # Create default hours
                                est_dict['operating_hours'] = {
                                    "Mon": ["09:00-17:00"], "Tue": ["09:00-17:00"], 
                                    "Wed": ["09:00-17:00"], "Thu": ["09:00-17:00"], 
                                    "Fri": ["09:00-17:00"], "Sat": ["09:00-17:00"],
                                    "Sun": ["09:00-17:00"]
                                }
                        
                        # Add establishment to our data list
                        session_establishments.append(est_dict)
                    else:
                        # Skip without flooding console
                        if sample_count < 5:
                            print(f"Skipping establishment {est_dict.get('name', est_dict.get('id', 'Unknown'))} - missing location data")
                            sample_count += 1
                
                # Add establishments from this session to the total list
                if session_establishments:
                    print(f"Found {len(session_establishments)} establishments with valid location data in session '{session_id}'")
                    establishments_data.extend(session_establishments)
                else:
                    print(f"No establishments with valid location data found in session '{session_id}'")
                
            except Exception as e:
                print(f"Error accessing establishments subcollection for session '{session_id}': {e}")
    
    except Exception as e:
        print(f"Error fetching sessions from Firebase: {e}")
    
    # If we found data in sessions, use it
    print(f"Total establishments data fetched from all sessions: {len(establishments_data)}")
    
    # If no establishments found, try the old approach of looking for top-level collections
    if not establishments_data:
        print("No establishments found in sessions. Trying top-level collections as fallback...")
        possible_collections = ['establishments', 'Establishments', 'restaurants', 'Restaurants', 'places', 'Places']
        
        for collection_name in possible_collections:
            try:
                # Try this collection
                print(f"Trying to fetch from collection: '{collection_name}'")
                establishments_ref = db.collection(collection_name).stream()
                
                collection_data = []
                for doc in establishments_ref:
                    est_dict = doc.to_dict()
                    est_dict['id'] = doc.id
                    
                    # Transform data to match what DayPlanner expects
                    # Same location extraction logic as above
                    if 'geometry' in est_dict and isinstance(est_dict['geometry'], dict):
                        if 'location' in est_dict['geometry']:
                            location = est_dict['geometry']['location']
                            if isinstance(location, dict):
                                if 'lat' in location and 'lng' in location:
                                    est_dict['latitude'] = location['lat']
                                    est_dict['longitude'] = location['lng']
                                elif 'latitude' in location and 'longitude' in location:
                                    est_dict['latitude'] = location['latitude']
                                    est_dict['longitude'] = location['longitude']
                    
                    # If we still don't have location data, skip
                    if 'latitude' not in est_dict or 'longitude' not in est_dict:
                        continue
                    
                    # Add establishment to our data list
                    collection_data.append(est_dict)
                
                # If we found data in this collection, use it
                if collection_data:
                    print(f"Found {len(collection_data)} establishments in collection '{collection_name}'")
                    establishments_data = collection_data
                    break
                    
            except Exception as e:
                print(f"Error fetching from collection '{collection_name}': {e}")
    
    # Check if we need to use mock data
    if not establishments_data:
        print("No establishments found in Firebase. Using mock data instead.")
        return MOCK_ESTABLISHMENTS_DATA
    
    print(f"Total establishments data fetched: {len(establishments_data)}")
    return establishments_data

def fetch_user_trips_from_firebase(user_id=None):
    trips_data = []
    db = firestore.client()
    
    try:
        # Change 'trips' to your actual collection name
        trips_ref = db.collection('user_preferences')
        sessions = list(trips_ref.stream())
        print(f"Found {len(sessions)} session documents")
        print("TRIPS REF: ", trips_ref)
        if user_id:
            # If we want trips for a specific user
            trips_ref = trips_ref.where('user_id', '==', user_id)
            print("USER FOUND IN USER_PREFERENCES COLLECTION")
        for doc in trips_ref.stream():
            trip_dict = doc.to_dict()
            trip_dict['trip_id'] = doc.id
            
            # Ensure we have establishments_visited
            if 'establishments_visited' not in trip_dict:
                trip_dict['establishments_visited'] = []
                
            trips_data.append(trip_dict)
            
        print(f"Fetched {len(trips_data)} trips from Firebase.")
    except Exception as e:
        print(f"Error fetching trips from Firebase: {e}")
        
    return trips_data

def examine_firebase_establishments():
    """Examine establishment documents in Firebase to understand their structure"""
    db = firestore.client()
    
    # Try top-level establishments collection first
    print("\n--- Examining top-level establishments collection ---")
    try:
        establishments_ref = db.collection('establishments').stream()
        est_count = 0
        for doc in establishments_ref:
            est_count += 1
            est_dict = doc.to_dict()
            if est_count <= 2:  # Just show first two for diagnostics
                print(f"\nEstablishment {doc.id}:")
                print(f"  Available fields: {list(est_dict.keys())}")
                for key, value in est_dict.items():
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error examining top-level establishments: {e}")
    
    # Now check establishments in session subcollections
    print("\n--- Examining establishments in sessions ---")
    try:
        sessions_ref = db.collection('sessions')
        for session in sessions_ref.limit(2).stream():  # Just look at first 2 sessions
            session_id = session.id
            print(f"\nSession: {session_id}")
            
            try:
                establishments_ref = sessions_ref.document(session_id).collection('establishments')
                est_count = 0
                for doc in establishments_ref.limit(2).stream():  # Just look at first 2 establishments
                    est_count += 1
                    est_dict = doc.to_dict()
                    print(f"\n  Establishment {doc.id}:")
                    print(f"    Available fields: {list(est_dict.keys())}")
                    
                    # Look for location or coordinates data specifically
                    if 'coordinates' in est_dict:
                        print(f"    coordinates: {est_dict['coordinates']}")
                        print(f"    coordinates type: {type(est_dict['coordinates'])}")
                    if 'location' in est_dict:
                        print(f"    location: {est_dict['location']}")
                        print(f"    location type: {type(est_dict['location'])}")
                    if 'latitude' in est_dict:
                        print(f"    latitude: {est_dict['latitude']}")
                    if 'longitude' in est_dict:
                        print(f"    longitude: {est_dict['longitude']}")
                    if 'lat' in est_dict:
                        print(f"    lat: {est_dict['lat']}")
                    if 'lng' in est_dict:
                        print(f"    lng: {est_dict['lng']}")
                    
                    # Look at a few other important fields
                    if 'name' in est_dict:
                        print(f"    name: {est_dict['name']}")
                    if 'type' in est_dict:
                        print(f"    type: {est_dict['type']}")
                    if 'category' in est_dict:
                        print(f"    category: {est_dict['category']}")
            except Exception as e:
                print(f"  Error examining establishments in session {session_id}: {e}")
    except Exception as e:
        print(f"Error examining sessions: {e}")


# --- Main Execution for Testing ---
if __name__ == "__main__":
    print("Starting Day Planner Test Script with Firebase Data...")

    # Initialize Firebase
    if not initialize_firebase():
        print("Failed to initialize Firebase. Exiting.")
        exit()
        
    # Check what collections are available
    available_collections = check_firebase_collections()
    
    # Examine establishments structure
    examine_firebase_establishments()
    
    # Try a simple test query
    try:
        db = firestore.client()
        # Try to query each available collection to verify connection
        for collection_name in available_collections:
            test_query = db.collection(collection_name).limit(3).stream()
            print(f"Sample documents in '{collection_name}':")
            for doc in test_query:
                print(f" - {doc.id}")
    except Exception as e:
        print(f"Firebase test query failed: {e}")

    # Fetch data from Firebase
    establishments_data = fetch_establishments_from_firebase()
    user_trips_data = fetch_user_trips_from_firebase()

    # Initialize DayPlanner with data (from Firebase or mock)
    day_planner = DayPlanner(establishments_data, user_trips_data)

    # Update to a larger radius since we're dealing with real-world data
    day_planner.MAX_RADIUS_KM = 30  # Increase from 10km to 30km
    
    # Test inputs
    test_user_id = "BOVJIa7LrZeGGw7pCpBk0kh4Em53"  # Replace with an actual user ID if needed
    test_date = datetime.date.today()
    
    # Ideally get this from user's last known location or home address
    test_start_location = (40.7282, -73.9942)  # New York City instead of Los Angeles

    # Generate the plan
    generated_plan = day_planner.generate_day_plan(test_user_id, test_date, test_start_location)

    # Print the results
    print("\n--- Generated Day Plan (Console Output) ---")
    if generated_plan:
        for item_index, item in enumerate(generated_plan):
            print(f"{item_index + 1}. Slot: {item['slot_name']} ({item['start_time']})")
            print(f"   Activity: {item['activity_name']} (Type: {item['activity_type']})")
            print(f"   Location: {item['location']}")
            print("-" * 20)
    else:
        print("No plan could be generated with the current settings and data.")

    print("\nDay Planner Test Script Finished.")


# Call this at the beginning of your script's execution
# if __name__ == "__main__":
#     if not initialize_firebase():
#         exit() # Or handle error appropriately
#     ... rest of your script
