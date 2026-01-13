"""
User History Service - Tracks user itinerary history and venue interactions
"""
from supabase_config import get_supabase_client
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class UserHistoryService:
    """Service for managing user itinerary history and venue interactions"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def get_excluded_place_ids(self, user_id: str, days_back: int = 30) -> List[str]:
        """Get place IDs user has seen in recent itineraries"""
        if not self.supabase:
            return []
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            result = self.supabase.table('user_itinerary_history')\
                .select('place_ids')\
                .eq('user_id', user_id)\
                .gte('generated_at', cutoff_date)\
                .execute()
            
            excluded = set()
            for row in result.data:
                place_ids = row.get('place_ids', [])
                if isinstance(place_ids, list):
                    excluded.update(place_ids)
            
            # Also get "not interested" venues (no time limit)
            interactions = self.supabase.table('user_venue_interactions')\
                .select('place_id')\
                .eq('user_id', user_id)\
                .eq('interaction_type', 'not_interested')\
                .execute()
            
            for row in interactions.data:
                excluded.add(row['place_id'])
            
            return list(excluded)
        except Exception as e:
            print(f"ERROR: Failed to get excluded place IDs: {str(e)}")
            return []
    
    def save_itinerary_history(self, user_id: str, itinerary_id: str, 
                                place_ids: List[str], filters: Dict):
        """Save generated itinerary to user history"""
        if not self.supabase:
            return
        
        try:
            self.supabase.table('user_itinerary_history').insert({
                'user_id': user_id,
                'itinerary_id': itinerary_id,
                'place_ids': place_ids,
                'filters': filters
            }).execute()
        except Exception as e:
            print(f"ERROR: Failed to save itinerary history: {str(e)}")
    
    def mark_venue_interaction(self, user_id: str, place_id: str, 
                                interaction_type: str):
        """Mark a venue as seen/not_interested/loved"""
        if not self.supabase:
            return
        
        if interaction_type not in ['seen', 'not_interested', 'loved']:
            raise ValueError(f"Invalid interaction_type: {interaction_type}")
        
        try:
            self.supabase.table('user_venue_interactions').upsert({
                'user_id': user_id,
                'place_id': place_id,
                'interaction_type': interaction_type
            }, on_conflict='user_id,place_id,interaction_type').execute()
        except Exception as e:
            print(f"ERROR: Failed to mark venue interaction: {str(e)}")
