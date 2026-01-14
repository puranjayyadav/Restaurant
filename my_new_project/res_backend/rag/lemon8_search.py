import json
import os
from typing import Any, Dict, List, Optional

import psycopg2
import requests
from openai import OpenAI
from pinecone import Pinecone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        return ""
    return value


def get_openai_client() -> OpenAI:
    api_key = _get_env("OPENROUTER_API_KEYv4")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEYv4 is not set")
    base_url = _get_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def get_chat_model() -> str:
    return _get_env("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def get_jina_embedding_model() -> str:
    return _get_env("JINA_EMBEDDING_MODEL", "jina-embeddings-v4")


def get_jina_api_key() -> str:
    api_key = _get_env("JINA_API_KEY")
    if not api_key:
        raise RuntimeError("JINA_API_KEY is not set")
    return api_key


def get_pinecone_index():
    api_key = _get_env("PINECONE_API_KEY")
    index_name = _get_env("PINECONE_INDEX_NAME")
    if not api_key or not index_name:
        raise RuntimeError("PINECONE_API_KEY or PINECONE_INDEX_NAME is not set")
    client = Pinecone(api_key=api_key)
    return client.Index(index_name)


def get_pinecone_namespace() -> str:
    return _get_env("PINECONE_NAMESPACE", "lemon8")


def get_cockroach_connection():
    conn_string = _get_env("COCKROACHDB_URL")
    if not conn_string:
        raise RuntimeError("COCKROACHDB_URL is not set")
    return psycopg2.connect(conn_string)


def _embed_query(query: str) -> List[float]:
    model = get_jina_embedding_model()
    api_key = get_jina_api_key()
    response = requests.post(
        "https://api.jina.ai/v1/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": [query]},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"Jina embeddings error: {response.status_code} {response.text}")
    data = response.json().get("data", [])
    if not data:
        raise RuntimeError("Jina embeddings returned empty data")
    data_sorted = sorted(data, key=lambda item: item.get("index", 0))
    return data_sorted[0]["embedding"]


def _build_filter(
    city: Optional[str],
    category_normalized: Optional[str],
    vibe_tags: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    if city:
        filters["city"] = {"$eq": city}
    if category_normalized:
        filters["category_normalized"] = {"$eq": category_normalized}
    if vibe_tags:
        filters["vibe_tags"] = {"$in": vibe_tags}
    return filters if filters else None


def _fetch_articles_by_url(urls: List[str]) -> Dict[str, Dict[str, Any]]:
    if not urls:
        return {}
    query = """
        SELECT url, title, description, contained_categories, contained_vibes
        FROM public.lemon8_articles
        WHERE url = ANY(%s)
    """
    with get_cockroach_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (urls,))
            rows = cursor.fetchall()
            return {
                row[0]: {
                    "url": row[0],
                    "title": row[1],
                    "description": row[2],
                    "contained_categories": row[3],
                    "contained_vibes": row[4],
                }
                for row in rows
            }


def _build_context(matches: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for match in matches:
        metadata = match.get("metadata") or {}
        place_name = metadata.get("place_name") or "Unknown place"
        city = metadata.get("city") or "Unknown city"
        category = metadata.get("category_normalized") or metadata.get("category") or "Unknown category"
        notes = metadata.get("notes") or ""
        url = metadata.get("url") or ""
        chunk = f"Place: {place_name}\nCity: {city}\nCategory: {category}\nNotes: {notes}\nURL: {url}"
        lines.append(chunk)
    return "\n\n".join(lines)


def _generate_answer(client: OpenAI, query: str, context: str) -> str:
    model = get_chat_model()
    system_prompt = (
        "You are a helpful travel assistant. Use the provided context to recommend places. "
        "If the context is insufficient, say so and ask for more details."
    )
    user_prompt = f"User query: {query}\n\nContext:\n{context}\n\nAnswer:"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


def search_lemon8(
    query: str,
    limit: int = 8,
    city: Optional[str] = None,
    category_normalized: Optional[str] = None,
    vibe_tags: Optional[List[str]] = None,
    generate_answer: bool = True,
) -> Dict[str, Any]:
    openai_client = get_openai_client()
    pinecone_index = get_pinecone_index()
    namespace = get_pinecone_namespace()

    query_embedding = _embed_query(query)
    metadata_filter = _build_filter(city, category_normalized, vibe_tags)

    pinecone_results = pinecone_index.query(
        vector=query_embedding,
        top_k=limit,
        include_metadata=True,
        namespace=namespace,
        filter=metadata_filter,
    )

    matches = pinecone_results.get("matches", []) if isinstance(pinecone_results, dict) else pinecone_results.matches
    urls = [match.get("metadata", {}).get("url") for match in matches if match.get("metadata", {}).get("url")]
    articles = _fetch_articles_by_url(list(set(urls)))

    results: List[Dict[str, Any]] = []
    for match in matches:
        metadata = match.get("metadata") or {}
        url = metadata.get("url")
        article = articles.get(url, {}) if url else {}
        results.append(
            {
                "score": match.get("score"),
                "url": url,
                "place_name": metadata.get("place_name"),
                "city": metadata.get("city"),
                "category_normalized": metadata.get("category_normalized"),
                "vibe_tags": metadata.get("vibe_tags"),
                "title": article.get("title"),
                "description": article.get("description"),
            }
        )

    context = _build_context(matches)
    answer = _generate_answer(openai_client, query, context) if generate_answer else None

    return {
        "query": query,
        "results": results,
        "answer": answer,
        "citations": [item["url"] for item in results if item.get("url")],
    }
