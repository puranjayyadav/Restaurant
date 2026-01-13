import os
import requests
from typing import List, Dict, Any, Optional
from supabase import create_client
from decouple import config
from django.conf import settings

class EmbeddingService:
    def __init__(self):
        self.openrouter_api_key = (getattr(settings, 'OPENROUTER_API_KEYv3', '') or 
                                  config('OPENROUTER_API_KEYv3', default='') or
                                  getattr(settings, 'OPENROUTER_API_KEY', '') or 
                                  config('OPENROUTER_API_KEY', default=''))
        self.embedding_model = 'openai/text-embedding-3-small'
        
        supabase_url = getattr(settings, 'SUPABASE_URL', config('SUPABASE_URL', default=''))
        supabase_key = getattr(settings, 'SUPABASE_KEY', config('SUPABASE_KEY', default=''))
        self.supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text using OpenRouter."""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.embedding_model,
                    "input": text
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['data'][0]['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def create_venue_text(self, venue: Dict[str, Any], vibes: List[str], reviews: List[str]) -> str:
        """Create a rich text representation of a venue for embedding."""
        parts = [venue.get('name', '')]
        
        # Add vibes
        if vibes:
            parts.append(f"Vibes: {', '.join(vibes)}")
        
        # Add neighborhood context from address
        address = venue.get('address', '')
        if address:
            # Extract neighborhood/city from address if possible
            address_parts = address.split(',')
            if len(address_parts) > 1:
                # Try to get neighborhood/area info
                location_info = address_parts[-2].strip() if len(address_parts) >= 2 else address
                parts.append(f"Location: {location_info}")
            else:
                parts.append(f"Location: {address}")
        
        # Add rating info
        rating = venue.get('rating')
        if rating:
            parts.append(f"Rating: {rating}")
        
        # Add review excerpts (top 3 most relevant)
        if reviews:
            review_text = ' '.join(reviews[:3])
            # Limit review text to avoid overly long embeddings
            parts.append(f"Reviews: {review_text[:400]}")
        
        return ' | '.join(parts)
    
    def generate_venue_embedding(self, place_id: str, retry_count: int = 3) -> bool:
        """Generate and store embedding for a single venue with retry logic."""
        import time
        
        for attempt in range(retry_count):
            try:
                # Fetch venue data (only fields that exist in venues table)
                venue_result = self.supabase.table('venues').select('place_id, name, address, rating').eq('place_id', place_id).single().execute()
                if not venue_result.data:
                    return False
                venue = venue_result.data
                
                # Fetch vibes
                try:
                    vibes_result = self.supabase.table('venue_vibes').select('vibe_slug').eq('place_id', place_id).limit(20).execute()
                    vibes = [v['vibe_slug'] for v in vibes_result.data if v.get('vibe_slug')]
                except:
                    vibes = []
                
                # Fetch reviews (top 5 by rating)
                try:
                    reviews_result = self.supabase.table('reviews').select('text').eq('place_id', place_id).order('rating', desc=True).limit(5).execute()
                    reviews = [r['text'] for r in reviews_result.data if r.get('text')]
                except:
                    reviews = []
                
                # Create text representation
                venue_text = self.create_venue_text(venue, vibes, reviews)
                
                # Generate embedding
                embedding = self.generate_embedding(venue_text)
                if not embedding:
                    return False
                
                # Store in database with timeout handling
                try:
                    # Format embedding as PostgreSQL array string for vector type
                    # Supabase Python client should handle this, but ensure it's a list
                    if not isinstance(embedding, list):
                        print(f"Warning: Embedding is not a list: {type(embedding)}")
                        return False
                    
                    # Use a more efficient update - only update embedding column
                    # The Supabase client should automatically convert list to vector type
                    update_result = self.supabase.table('venues').update({
                        'embedding': embedding,  # List should be converted to vector by Supabase
                        'embedding_updated_at': 'now()'
                    }).eq('place_id', place_id).execute()
                    
                    print(f"Generated embedding for {venue.get('name', place_id)}")
                    return True
                    
                except Exception as update_error:
                    error_str = str(update_error)
                    # Check for timeout errors
                    if 'timeout' in error_str.lower() or '57014' in error_str:
                        if attempt < retry_count - 1:
                            wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                            print(f"Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"Failed after {retry_count} attempts due to timeout")
                            return False
                    else:
                        # Other errors, don't retry
                        raise
                    
            except Exception as e:
                error_str = str(e)
                if 'timeout' in error_str.lower() or '57014' in error_str:
                    if attempt < retry_count - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"Timeout error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Failed after {retry_count} attempts: {e}")
                        return False
                else:
                    print(f"Error generating embedding for {place_id}: {e}")
                    return False
        
        return False
    
    def batch_generate_embeddings(self, limit: int = 100, min_rating: float = 0.0, batch_size: int = 50):
        """Generate embeddings for venues that don't have them yet."""
        import time
        
        try:
            # Process in smaller batches to avoid timeouts
            total_processed = 0
            total_success = 0
            offset = 0
            
            while total_processed < limit:
                current_batch_size = min(batch_size, limit - total_processed)
                
                try:
                    # Get venues without embeddings
                    query = self.supabase.table('venues').select('place_id, name, rating').is_('embedding', 'null')
                    
                    if min_rating > 0:
                        query = query.gte('rating', min_rating)
                    
                    result = query.order('rating', desc=True).range(offset, offset + current_batch_size - 1).execute()
                    venues = result.data
                    
                    if not venues:
                        print("No more venues to process.")
                        break
                    
                    print(f"Processing batch {offset // batch_size + 1}: {len(venues)} venues (offset {offset})...")
                    
                    batch_success = 0
                    for i, venue in enumerate(venues):
                        venue_num = total_processed + i + 1
                        print(f"[{venue_num}/{limit}] Processing {venue.get('name', venue['place_id'])}...")
                        
                        if self.generate_venue_embedding(venue['place_id']):
                            batch_success += 1
                            total_success += 1
                        
                        # Small delay between each venue to avoid overwhelming the database
                        time.sleep(0.5)
                    
                    total_processed += len(venues)
                    offset += len(venues)
                    
                    print(f"Batch complete: {batch_success}/{len(venues)} successful. Total: {total_success}/{total_processed}")
                    
                    # Longer delay between batches
                    if total_processed < limit:
                        print("Waiting 3 seconds before next batch...")
                        time.sleep(3)
                    
                except Exception as batch_error:
                    error_str = str(batch_error)
                    if 'timeout' in error_str.lower() or '57014' in error_str:
                        print(f"Batch timeout error: {batch_error}")
                        print("Waiting 5 seconds before retrying batch...")
                        time.sleep(5)
                        # Don't increment offset, retry same batch
                        continue
                    else:
                        print(f"Batch error: {batch_error}")
                        # Move to next batch
                        offset += current_batch_size
                        total_processed += current_batch_size
            
            print(f"Completed: {total_success}/{total_processed} embeddings generated successfully")
            return total_success
            
        except Exception as e:
            print(f"Batch generation error: {e}")
            return total_success if 'total_success' in locals() else 0
