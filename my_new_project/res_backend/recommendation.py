import math
from .models import Establishment, User

class RestaurantRecommender:
    """Machine learning recommendation system for restaurants.
    
    This class implements a content-based filtering approach to recommend restaurants
    based on user preferences and trip data using pure Python (no scikit-learn).
    """
    def __init__(self):
        self.feature_columns = []  # Will be populated during model initialization
        self.users_data = {}  # Cached user preference data
        
    def _initialize_features(self):
        """Initialize feature columns from all establishments in database."""
        try:
            establishments = Establishment.objects.all()
            
            # Extract all possible values for categorical features
            dining_styles = set(e.dining_style for e in establishments)
            price_ranges = set(e.price_range for e in establishments)
            features = set(f.feature_type for e in establishments for f in e.features.all())
            
            # Create feature column names
            self.feature_columns = (
                [f"dining_{s}" for s in dining_styles] + 
                [f"price_{p}" for p in price_ranges] + 
                [f"feature_{f}" for f in features]
            )
            
            return True
        except Exception as e:
            print(f"Error initializing features: {e}")
            return False
    
    def extract_user_preferences(self, user_id):
        """Extract user preferences based on their interaction history.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            Dictionary containing user preferences for different features.
        """
        # This would normally fetch from UserInteraction model
        # For initial implementation, we'll use dummy data if no interactions exist
        
        try:
            user = User.objects.get(id=user_id)
            establishments = Establishment.objects.filter(user=user)
            
            # Track feature frequencies
            dining_styles = {}
            price_preferences = {}
            feature_preferences = {}
            
            for est in establishments:
                # Count dining style
                style = est.dining_style
                dining_styles[style] = dining_styles.get(style, 0) + 1
                
                # Count price range
                price = est.price_range
                price_preferences[price] = price_preferences.get(price, 0) + 1
                
                # Count features
                for feature in est.features.all():
                    feature_type = feature.feature_type
                    feature_preferences[feature_type] = feature_preferences.get(feature_type, 0) + 1
            
            # If no data exists yet, provide reasonable defaults
            if not dining_styles:
                dining_styles = {'CASUAL': 1, 'FINE': 1}  # Default to balanced preferences
                
            if not price_preferences:
                price_preferences = {'$$': 2, '$$$': 1}  # Default to mid-range
                
            if not feature_preferences:
                feature_preferences = {'OUTDOOR': 1, 'TAKEOUT': 1}  # Common defaults
            
            return {
                'dining_styles': dining_styles,
                'price_preferences': price_preferences,
                'feature_preferences': feature_preferences
            }
        except User.DoesNotExist:
            # Return default preferences for new users
            return {
                'dining_styles': {'CASUAL': 1, 'FINE': 1},
                'price_preferences': {'$$': 2, '$$$': 1},
                'feature_preferences': {'OUTDOOR': 1, 'TAKEOUT': 1}
            }
        except Exception as e:
            print(f"Error extracting user preferences: {e}")
            return {
                'dining_styles': {},
                'price_preferences': {},
                'feature_preferences': {}
            }
    
    def get_user_vector(self, user_id):
        """Create feature vector for a user based on their preferences.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            List representing user preferences.
        """
        # Initialize features if not already done
        if not self.feature_columns:
            self._initialize_features()
            
        # Get user preferences
        user_preferences = self.extract_user_preferences(user_id)
        
        # Initialize vector with zeros
        user_vector = [0] * len(self.feature_columns)
        
        # Fill in user preferences
        for i, feature in enumerate(self.feature_columns):
            if feature.startswith('dining_'):
                style = feature[7:]  # Remove 'dining_' prefix
                user_vector[i] = user_preferences['dining_styles'].get(style, 0)
            elif feature.startswith('price_'):
                price = feature[6:]  # Remove 'price_' prefix
                user_vector[i] = user_preferences['price_preferences'].get(price, 0)
            elif feature.startswith('feature_'):
                feat = feature[8:]  # Remove 'feature_' prefix
                user_vector[i] = user_preferences['feature_preferences'].get(feat, 0)
        
        # Normalize vector
        vector_sum = sum(user_vector)
        if vector_sum > 0:
            user_vector = [value / vector_sum for value in user_vector]
            
        return user_vector
    
    def get_establishment_vector(self, establishment):
        """Create feature vector for an establishment.
        
        Args:
            establishment: Establishment object.
            
        Returns:
            List representing establishment features.
        """
        # Initialize vector with zeros
        est_vector = [0] * len(self.feature_columns)
        
        # Fill in establishment features
        for i, feature in enumerate(self.feature_columns):
            if feature == f"dining_{establishment.dining_style}":
                est_vector[i] = 1
            elif feature == f"price_{establishment.price_range}":
                est_vector[i] = 1
            elif feature.startswith('feature_'):
                feat = feature[8:]  # Remove 'feature_' prefix
                if establishment.features.filter(feature_type=feat).exists():
                    est_vector[i] = 1
        
        return est_vector
    
    def cosine_similarity(self, vector_a, vector_b):
        """Calculate cosine similarity between two vectors without NumPy.
        
        Args:
            vector_a, vector_b: Lists of equal length representing feature vectors.
            
        Returns:
            Similarity score between 0 and 1.
        """
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        
        # Calculate magnitudes
        magnitude_a = math.sqrt(sum(a * a for a in vector_a))
        magnitude_b = math.sqrt(sum(b * b for b in vector_b))
        
        # Calculate similarity (handle division by zero)
        if magnitude_a == 0 or magnitude_b == 0:
            return 0
        
        return dot_product / (magnitude_a * magnitude_b)
    
    def recommend_for_trip(self, user_id, trip_location, n=5):
        """Recommend restaurants for a user in a specific trip location.
        
        Args:
            user_id: The ID of the user.
            trip_location: String containing location information.
            n: Number of recommendations to return.
            
        Returns:
            List of recommended Establishment objects.
        """
        # Initialize features if not already done
        if not self.feature_columns:
            success = self._initialize_features()
            if not success:
                return []
        
        # Get user preferences vector
        user_vector = self.get_user_vector(user_id)
        
        # Get establishments near the trip location
        # This is a simplified approach - in production you'd use geospatial queries
        nearby_establishments = Establishment.objects.filter(
            location_region__icontains=trip_location)
        
        if not nearby_establishments:
            return []
            
        # Calculate establishment vectors and similarity to user
        establishment_scores = []
        
        for est in nearby_establishments:
            est_vector = self.get_establishment_vector(est)
            
            # Calculate similarity if the establishment has features
            if sum(est_vector) > 0:
                similarity = self.cosine_similarity(user_vector, est_vector)
                establishment_scores.append((est, similarity))
        
        # Sort by similarity and return top N
        establishment_scores.sort(key=lambda x: x[1], reverse=True)
        return [est for est, score in establishment_scores[:n]]
    
    def recommend_similar_restaurants(self, establishment_id, n=5):
        """Find similar restaurants to a given establishment.
        
        This method uses content-based filtering to find restaurants
        similar to one the user has already expressed interest in.
        
        Args:
            establishment_id: ID of the establishment to find similar ones to.
            n: Number of recommendations to return.
            
        Returns:
            List of similar Establishment objects.
        """
        # Initialize features if not already done
        if not self.feature_columns:
            success = self._initialize_features()
            if not success:
                return []
                
        try:
            # Get the source establishment
            source_est = Establishment.objects.get(id=establishment_id)
            source_vector = self.get_establishment_vector(source_est)
            
            # Get all other establishments
            other_establishments = Establishment.objects.exclude(id=establishment_id)
            
            # Calculate similarities
            establishment_scores = []
            for est in other_establishments:
                est_vector = self.get_establishment_vector(est)
                
                # Calculate similarity if both have features
                if sum(source_vector) > 0 and sum(est_vector) > 0:
                    similarity = self.cosine_similarity(source_vector, est_vector)
                    establishment_scores.append((est, similarity))
            
            # Sort by similarity and return top N
            establishment_scores.sort(key=lambda x: x[1], reverse=True)
            return [est for est, score in establishment_scores[:n]]
            
        except Establishment.DoesNotExist:
            return []
        except Exception as e:
            print(f"Error finding similar restaurants: {e}")
            return []
    
    def recommend_by_coordinates(self, user_id, lat, lon, radius_km=5, n=5):
        """Recommend restaurants for a user near specific coordinates.
        
        Args:
            user_id: The ID of the user.
            lat: Latitude coordinate.
            lon: Longitude coordinate.
            radius_km: Search radius in kilometers.
            n: Number of recommendations to return.
            
        Returns:
            List of recommended Establishment objects.
        """
        # Initialize features if not already done
        if not self.feature_columns:
            success = self._initialize_features()
            if not success:
                return []
        
        # Get user preferences vector
        user_vector = self.get_user_vector(user_id)
        
        # Get all establishments
        all_establishments = Establishment.objects.all()
        
        if not all_establishments:
            return []
            
        # Filter by coordinates (simplified implementation)
        # In production, use geodjango or postgis for proper spatial queries
        nearby_establishments = []
        for est in all_establishments:
            # Skip establishments without coordinate data
            if not est.latitude or not est.longitude:
                continue
                
            # Simple haversine distance calculation
            distance = self._calculate_distance(
                float(lat), float(lon), 
                float(est.latitude), float(est.longitude)
            )
            
            # Add if within radius
            if distance <= radius_km:
                nearby_establishments.append(est)
        
        # If no nearby establishments found, return empty list
        if not nearby_establishments:
            return []
            
        # Calculate establishment vectors and similarity to user
        establishment_scores = []
        
        for est in nearby_establishments:
            est_vector = self.get_establishment_vector(est)
            
            # Calculate similarity if the establishment has features
            if sum(est_vector) > 0:
                similarity = self.cosine_similarity(user_vector, est_vector)
                establishment_scores.append((est, similarity))
        
        # Sort by similarity and return top N
        establishment_scores.sort(key=lambda x: x[1], reverse=True)
        return [est for est, score in establishment_scores[:n]]
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates using Haversine formula.
        
        Args:
            lat1, lon1: First coordinate.
            lat2, lon2: Second coordinate.
            
        Returns:
            Distance in kilometers.
        """
        # Convert to radians
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        
        return c * r 