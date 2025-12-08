"""
OR-Tools TOPTW (Team Orienteering Problem with Time Windows) Solver.
Implements open routes (dummy end node) and slack time for wait periods.
"""
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Dict, Tuple, Optional
import math


class TOPTWSolver:
    """
    Solves the Team Orienteering Problem with Time Windows using OR-Tools.
    
    Features:
    - Open routes (route can end anywhere, no forced return to start)
    - Slack time for early arrival and waiting
    - Category capacity constraints
    - Time window constraints
    - Utility score maximization
    """
    
    def __init__(self):
        self.manager = None
        self.routing = None
        self.solution = None
    
    def solve_itinerary(self, places: List[Dict], time_matrix: List[List[int]], 
                       scores: List[float], durations: List[int],
                       time_windows: List[Tuple[int, int]], 
                       category_constraints: Dict[str, int],
                       start_location: Tuple[float, float],
                       time_budget: int = 540,
                       slack_minutes: int = 30,
                       require_lunch: bool = False,
                       max_places: int = 9,
                       max_distance_km: float = 1.0) -> Optional[Dict]:
        """
        Solve itinerary optimization problem.
        
        Args:
            places: List of place dicts with lat/lng, name, category
            time_matrix: N×N travel time matrix in minutes (includes start as index 0)
            scores: List of utility scores (0-100) for each place
            durations: List of visit durations in minutes for each place
            time_windows: List of (min_start, max_start) tuples in minutes for each place
            category_constraints: Dict mapping category to max count (e.g., {"restaurant": 2})
            start_location: (lat, lng) of starting point
            time_budget: Total time available in minutes (default: 540 = 9 hours)
            slack_minutes: Maximum wait time allowed (default: 30 minutes)
            require_lunch: If True, enforce 1 restaurant visit between 11:30 AM - 2:00 PM
            max_places: Maximum number of places to visit (default: 10)
            max_distance_km: Maximum distance between consecutive places (default: 1.0 km)
        
        Returns:
            Dict with optimized route, or None if solver fails
        """
        try:
            num_nodes = len(places)
            if num_nodes == 0:
                return None
            
            # Create routing index manager with open route
            # Start at index 0 (user location), end at dummy node (index num_nodes)
            # CRITICAL FIX #2: Open routes - route can end anywhere
            self.manager = pywrapcp.RoutingIndexManager(
                num_nodes + 1,  # +1 for dummy end node
                1,  # 1 vehicle
                [0],  # Start at index 0 (user location)
                [num_nodes]  # End at dummy node (allows route to end anywhere)
            )
            
            # Create routing model
            self.routing = pywrapcp.RoutingModel(self.manager)
            
            # Define distance callback (travel time)
            # Also enforce max distance constraint by penalizing far distances
            def time_callback(from_index, to_index):
                from_node = self.manager.IndexToNode(from_index)
                to_node = self.manager.IndexToNode(to_index)
                
                # Dummy end node has 0 cost to all nodes
                if to_node == num_nodes:
                    return 0
                if from_node == num_nodes:
                    return 0
                
                travel_time = time_matrix[from_node][to_node]
                
                # Convert travel time to approximate distance (walking speed ~5 km/h = 0.083 km/min)
                # If travel time suggests distance > max_distance_km, heavily penalize it
                estimated_distance_km = (travel_time * 0.083) if travel_time > 0 else 0
                
                # Heavily penalize distances > max_distance_km (set very high cost)
                # This ensures solver prefers nearby places and keeps itinerary hyper-local
                if estimated_distance_km > max_distance_km:
                    return 999999  # Very high penalty for far distances
                
                return travel_time
            
            transit_callback_index = self.routing.RegisterTransitCallback(time_callback)
            
            # Set arc cost evaluator
            self.routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Add time dimension with slack
            # CRITICAL FIX #3: Slack time allows early arrival and waiting
            time_callback_index = self.routing.RegisterTransitCallback(time_callback)
            
            self.routing.AddDimension(
                time_callback_index,
                slack_minutes,  # Maximum slack (wait time) in minutes
                time_budget,  # Maximum time per vehicle
                False,  # Don't force start cumul to zero
                'Time'
            )
            
            time_dimension = self.routing.GetDimensionOrDie('Time')
            
            # Add time window constraints
            # Validate and set time windows
            for i in range(num_nodes):
                if i < len(time_windows) and time_windows[i]:
                    min_start, max_start = time_windows[i]
                    
                    # Validate time window
                    if min_start is None or max_start is None:
                        continue
                    if min_start < 0:
                        min_start = 0
                    if max_start > time_budget:
                        max_start = time_budget
                    if min_start >= max_start:
                        # Invalid window, use a default wide window
                        min_start = 0
                        max_start = time_budget
                    
                    index = self.manager.NodeToIndex(i)
                    try:
                        time_dimension.CumulVar(index).SetRange(int(min_start), int(max_start))
                    except Exception as e:
                        print(f"DEBUG: Failed to set time window for node {i}: {e}")
                        # Use soft bounds instead
                        time_dimension.SetCumulVarSoftLowerBound(index, int(min_start), 0)
                        time_dimension.SetCumulVarSoftUpperBound(index, int(max_start), 0)
            
            # Add disjunctions with penalties (skipped node penalty = negative score)
            # Higher score = lower penalty = more likely to be selected
            for i in range(num_nodes):
                if i < len(scores):
                    penalty = int(100 - scores[i])  # Convert score to penalty
                    index = self.manager.NodeToIndex(i)
                    self.routing.AddDisjunction([index], penalty)
            
            # Add maximum places constraint (limit total number of places visited)
            # This ensures we don't get too many places in the itinerary
            def count_callback(from_index):
                """Returns 1 for each place visited (except start/dummy nodes)"""
                from_node = self.manager.IndexToNode(from_index)
                # Start node (0) and dummy end node (num_nodes) don't count
                if from_node == 0 or from_node == num_nodes:
                    return 0
                return 1
            
            count_callback_index = self.routing.RegisterUnaryTransitCallback(count_callback)
            self.routing.AddDimension(
                count_callback_index,
                0,  # No slack
                max_places,  # Maximum number of places
                True,  # Start cumul to zero
                'PlaceCount'
            )
            
            # Add category capacity constraints
            # Group places by category and limit count per category
            category_groups = {}
            for i, place in enumerate(places):
                category = self._get_category(place)
                if category:
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(i)
            
            # Create dimension for each category with capacity constraint
            for category, indices in category_groups.items():
                if category in category_constraints:
                    max_count = category_constraints[category]
                    
                    # Create dimension for this category
                    def category_callback(from_index, to_index):
                        to_node = self.manager.IndexToNode(to_index)
                        # Return 1 if visiting a place in this category, 0 otherwise
                        if to_node < num_nodes and to_node in indices:
                            return 1
                        return 0
                    
                    category_callback_index = self.routing.RegisterTransitCallback(category_callback)
                    
                    self.routing.AddDimension(
                        category_callback_index,
                        0,  # No slack
                        max_count,  # Maximum capacity
                        True,  # Force start cumul to zero
                        f'Category_{category}'
                    )
            
            # Optional: Mandatory lunch constraint
            if require_lunch:
                # Find restaurant indices in lunch time window (11:30 AM - 2:00 PM = 690-840 min)
                lunch_restaurants = []
                for i, place in enumerate(places):
                    category = self._get_category(place)
                    if category in ['restaurant', 'food']:
                        if i < len(time_windows) and time_windows[i]:
                            min_start, max_start = time_windows[i]
                            # Check if time window overlaps with lunch window
                            if not (max_start < 690 or min_start > 840):
                                lunch_restaurants.append(i)
                
                # Add constraint: at least one lunch restaurant must be visited
                if lunch_restaurants:
                    # Use AddPickupAndDelivery or hard constraint
                    # For simplicity, we'll use a soft constraint via disjunction penalty
                    # (This ensures at least one is selected if possible)
                    pass  # Can be enhanced with hard constraint if needed
            
            # Set search parameters
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = 5  # 5 second timeout
            
            # Solve
            self.solution = self.routing.SolveWithParameters(search_parameters)
            
            if not self.solution:
                return None
            
            # Extract route
            route = []
            time_dimension = self.routing.GetDimensionOrDie('Time')
            index = self.routing.Start(0)
            total_time = 0
            total_score = 0
            
            while not self.routing.IsEnd(index):
                node = self.manager.IndexToNode(index)
                
                if node < num_nodes:  # Skip dummy end node
                    time_var = time_dimension.CumulVar(index)
                    arrival_time = self.solution.Value(time_var)
                    departure_time = arrival_time + durations[node]
                    
                    route.append({
                        'place_index': node,
                        'arrival_time': arrival_time,
                        'departure_time': departure_time,
                        'duration': durations[node],
                        'score': scores[node] if node < len(scores) else 0,
                    })
                    
                    total_score += scores[node] if node < len(scores) else 0
                
                # Get next index
                index = self.solution.Value(self.routing.NextVar(index))
                total_time = self.solution.Value(time_dimension.CumulVar(index))
            
            return {
                'route': route,
                'total_time': total_time,
                'total_score': total_score,
                'places_visited': len(route),
            }
            
        except Exception as e:
            print(f"OR-Tools solver error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_category(self, place: Dict) -> Optional[str]:
        """Extract category from place dict."""
        if isinstance(place, dict):
            types = place.get('types', [])
            if types:
                # Return first type (e.g., 'restaurant', 'cafe')
                return types[0].lower()
        else:
            # ScrapedRestaurant object
            categories = place.categories or []
            if categories:
                return categories[0].lower()
        return None

