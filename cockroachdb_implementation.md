# CockroachDB Implementation Details

## Overview

This document outlines the implementation and usage of CockroachDB within this project. The primary role of CockroachDB is to serve as a scalable, distributed SQL backend for data migrated from Supabase, which is then used to power the application's Retrieval-Augmented Generation (RAG) features.

The core of the implementation revolves around the `lemon8_articles` table, which stores article data used for search and providing context to AI models.

## Configuration and Connection

The application and related scripts connect to a CockroachDB Cloud instance.

*   **Connection Method:** Connection is managed via a `COCKROACHDB_URL` environment variable.
*   **Connection String:** The URL is a standard PostgreSQL connection string, for example:
    ```
    postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full
    ```
*   **SSL Certificate:** A secure connection is enforced using `sslmode=verify-full`. This requires a CA certificate, which can be downloaded and set up using the `setup_cockroachdb_cert.ps1` script. This script fetches the certificate and places it in the appropriate directory (`%APPDATA%\postgresql\` on Windows).

## Database Schema

The main table used in the CockroachDB implementation is `public.lemon8_articles`. The schema is designed to store article content, extracted metadata, and enriched data for fast retrieval.

The table is created and managed by the `migrate_lemon8_to_cockroachdb.py` script.

```sql
CREATE TABLE IF NOT EXISTS public.lemon8_articles (
    url TEXT PRIMARY KEY,
    html_content TEXT,
    itinerary_data JSONB,
    enriched_itinerary_data JSONB,
    stops_lat DOUBLE PRECISION[],
    stops_lng DOUBLE PRECISION[],
    scraped_at TIMESTAMP,
    extracted_at TIMESTAMP,
    extraction_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_lemon8_articles_extracted_at ON public.lemon8_articles(extracted_at);
CREATE INDEX IF NOT EXISTS idx_lemon8_articles_created_at ON public.lemon8_articles(created_at);
CREATE INDEX IF NOT EXISTS idx_lemon8_articles_itinerary_data ON public.lemon8_articles USING GIN (itinerary_data);
CREATE INDEX IF NOT EXISTS idx_lemon8_articles_enriched_itinerary_data ON public.lemon8_articles USING GIN (enriched_itinerary_data);
```

### Key Columns:
*   `url`: The primary key, uniquely identifying each article.
*   `itinerary_data`, `enriched_itinerary_data`: JSONB fields that store structured data extracted or enriched from the articles. These are indexed using a GIN index for efficient querying within the JSON structure.
*   `stops_lat`, `stops_lng`: Arrays of doubles to store coordinates related to the itineraries.

## Current Usage & Implementation

The CockroachDB database is currently used in two main ways:

### 1. Data Migration and Storage

A suite of Python scripts manages the migration of data from a Supabase instance into CockroachDB. This process is documented in `MIGRATE_TO_COCKROACHDB.md` and automated by `run_migration.ps1`.

*   **`migrate_lemon8_to_cockroachdb.py`**: The core script that fetches all records from Supabase, creates the `lemon8_articles` schema in CockroachDB if it doesn't exist, and inserts the data using an "upsert" logic (`ON CONFLICT DO UPDATE`). This makes the script idempotent and safe to re-run.
*   **`add_missing_columns_to_cockroachdb.py`**: A utility script to backfill new columns with data, demonstrating ongoing schema evolution.
*   **`verify_migration.py`**: A script to ensure data integrity by comparing record counts and URLs between the Supabase source and the CockroachDB destination.

### 2. Retrieval-Augmented Generation (RAG) Backend

The primary application-level use of CockroachDB is to serve as the "retrieval" component in a RAG pipeline for the `lemon8_search` feature.

The workflow, implemented in `my_new_project/res_backend/rag/lemon8_search.py`, is as follows:

1.  A user submits a natural language query.
2.  The query is converted into a vector embedding.
3.  This embedding is used to search a **Pinecone** vector index, which returns a list of semantically similar article URLs.
4.  The `_fetch_articles_by_url` function then executes a SQL query against **CockroachDB** to fetch the full details (title, description, etc.) for the URLs retrieved from Pinecone.
5.  This retrieved content is used as context for an LLM (like GPT-4o-mini via OpenRouter) to generate a helpful, context-aware answer for the user.

```