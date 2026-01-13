# Product Tech Stack

This document outlines the technical stack chosen for Plandit, covering frontend, backend, database, and infrastructure.

## Frontend
- **Framework:** [Flutter](https://flutter.dev/) (Dart)
  - Target Platforms: iOS, Android, Web
  - State Management: Provider / Hooks (inferred from common Flutter patterns in project)
  - Key Libraries: Google Maps Flutter, Supabase Flutter, Custom Heatmap Widgets

## Backend
- **Core:** [Django](https://www.djangoproject.com/) (Python)

- **Task Processing:** Custom Python scripts (intended for GitHub Actions / Cron)
- **AI Integration:** [OpenRouter](https://openrouter.ai/) for LLM access (GPT-4o, Claude 3.5 Sonnet)
- **Scraping Engine:**
  - Selenium / Playwright for dynamic content extraction.
  - Custom scrapers for Lemon8, Yelp, OpenTable, and Google Maps.

## Database & Infrastructure
- **Provider:** [Supabase](https://supabase.com/)
  - Database: PostgreSQL (with PostGIS for geocoding)
  - Authentication: Supabase Auth
  - Storage: Supabase Storage for location images and AI-generated covers
- **Realtime:** Supabase Realtime for live updates on itineraries and heatmaps
- **Hosting:** [Render](https://render.com/) for backend services.
- **CI/CD:** GitHub Actions for automated scraping and review enrichment.

## AI & Data Strategy
- **NLP:** Using LLMs via OpenRouter to:
  - Extract structured itinerary data from unstructured social media reviews from Supabase tables.
  - Generate "Insider" insights and tidbits.
  - Categorize and tag restaurants by "vibe" and "aesthetic".
- **Algorithms:** Custom Python-based "Itinerary Solver" using optimization algorithms to sequence locations based on geography and time.
