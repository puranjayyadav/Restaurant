import json
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import psycopg2
import requests
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


def get_jina_embedding_model() -> str:
    return _get_env("JINA_EMBEDDING_MODEL", "jina-embeddings-v4")


def get_jina_api_key() -> str:
    api_key = _get_env("JINA_API_KEY")
    if not api_key:
        raise RuntimeError("JINA_API_KEY is not set")
    return api_key


def get_pinecone_index():
    api_key = _get_env("PINECONE_API_KEY")
    index_name = get_pinecone_index_name()
    if not api_key or not index_name:
        raise RuntimeError("PINECONE_API_KEY or PINECONE_INDEX_NAME is not set")
    client = Pinecone(api_key=api_key)
    return client.Index(index_name)


def get_pinecone_index_name() -> str:
    return _get_env("PINECONE_INDEX_NAME")


def get_pinecone_namespace() -> str:
    return _get_env("PINECONE_NAMESPACE", "lemon8")


def get_cockroach_connection():
    conn_string = _get_env("COCKROACHDB_URL")
    if not conn_string:
        raise RuntimeError("COCKROACHDB_URL is not set")
    return psycopg2.connect(conn_string)


def _safe_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def _coerce_json(value: Any) -> Any:
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _extract_itineraries(article: Dict[str, Any]) -> List[Dict[str, Any]]:
    enriched = _coerce_json(article.get("enriched_itinerary_data"))
    basic = _coerce_json(article.get("itinerary_data"))

    if isinstance(enriched, list):
        return [item for item in enriched if isinstance(item, dict)]
    if isinstance(enriched, dict):
        return [enriched]
    if isinstance(basic, dict):
        return [basic]
    return []


def _build_stop_text(stop: Dict[str, Any], article: Dict[str, Any]) -> str:
    parts = []
    place_name = stop.get("place_name") or ""
    if place_name:
        parts.append(f"Place: {place_name}")
    city = stop.get("city") or article.get("city") or ""
    if city:
        parts.append(f"City: {city}")

    category = stop.get("category") or ""
    if category:
        parts.append(f"Category: {category}")

    solver = stop.get("solver_data") or {}
    if isinstance(solver, dict):
        category_normalized = solver.get("category_normalized")
        if category_normalized:
            parts.append(f"CategoryNormalized: {category_normalized}")
        vibe_tags = solver.get("vibe_tags")
        if vibe_tags:
            parts.append(f"Vibes: {', '.join(_safe_list(vibe_tags))}")

    notes = stop.get("notes") or ""
    if notes:
        parts.append(f"Notes: {notes}")

    title = article.get("title") or ""
    if title:
        parts.append(f"Title: {title}")

    description = article.get("description") or ""
    if description:
        parts.append(f"Description: {description}")

    return "\n".join(parts).strip()


def _build_fallback_text(article: Dict[str, Any]) -> str:
    title = article.get("title") or ""
    description = article.get("description") or ""
    combined = "\n".join([part for part in [title, description] if part])
    return combined.strip()


def _build_metadata(stop: Optional[Dict[str, Any]], article: Dict[str, Any]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "url": article.get("url"),
        "source": "lemon8",
        "created_at": article.get("created_at"),
        "contained_categories": _safe_list(article.get("contained_categories")),
        "contained_vibes": _safe_list(article.get("contained_vibes")),
    }

    if stop:
        metadata["place_name"] = stop.get("place_name")
        metadata["city"] = stop.get("city") or article.get("city")
        metadata["category"] = stop.get("category")

        solver = stop.get("solver_data") or {}
        if isinstance(solver, dict):
            metadata["category_normalized"] = solver.get("category_normalized")
            metadata["vibe_tags"] = _safe_list(solver.get("vibe_tags"))
    else:
        metadata["title"] = article.get("title")
        metadata["city"] = article.get("city")

    return _clean_metadata(metadata)


def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            cleaned_list = [str(item) for item in value if item is not None]
            if cleaned_list:
                cleaned[key] = cleaned_list
            continue
        cleaned[key] = value
    return cleaned


def _iter_articles(
    limit: Optional[int],
    batch_size: int,
    status_tag: str,
) -> Iterable[Dict[str, Any]]:
    query = """
        SELECT url, title, description, itinerary_data, enriched_itinerary_data,
               contained_categories, contained_vibes, created_at, processing_status
        FROM public.lemon8_articles
        WHERE processing_status IS NULL OR processing_status != %s
        ORDER BY created_at
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    with get_cockroach_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (status_tag,))
            columns = [desc[0] for desc in cursor.description]
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    yield dict(zip(columns, row))


def _embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_jina_embedding_model()
    api_key = get_jina_api_key()
    max_retries = 5
    backoff_seconds = 2
    for attempt in range(max_retries):
        response = requests.post(
            "https://api.jina.ai/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": texts},
            timeout=60,
        )
        if response.ok:
            data = response.json().get("data", [])
            if not data:
                raise RuntimeError("Jina embeddings returned empty data")
            data_sorted = sorted(data, key=lambda item: item.get("index", 0))
            return [item["embedding"] for item in data_sorted]
        if response.status_code == 429 and attempt < max_retries - 1:
            sleep_for = backoff_seconds * (2 ** attempt)
            print(f"[RAG] Jina rate limit hit, sleeping {sleep_for}s before retry")
            time.sleep(sleep_for)
            continue
        raise RuntimeError(f"Jina embeddings error: {response.status_code} {response.text}")


def index_lemon8_articles(
    limit: Optional[int] = None,
    batch_size: int = 50,
    namespace: Optional[str] = None,
) -> Tuple[int, int]:
    namespace = namespace or get_pinecone_namespace()
    pinecone_index = get_pinecone_index()
    index_name = get_pinecone_index_name()
    status_tag = f"indexed:{index_name}"

    print(
        "[RAG] Starting Lemon8 indexing "
        f"(batch_size={batch_size}, limit={limit}, namespace={namespace}, index={index_name})"
    )

    vector_payloads: List[Tuple[str, Dict[str, Any], str]] = []
    urls_to_mark: List[str] = []
    embedded_count = 0
    skipped_count = 0
    processed_articles = 0

    for article in _iter_articles(limit=limit, batch_size=batch_size, status_tag=status_tag):
        url = article.get("url")
        itineraries = _extract_itineraries(article)
        stops: List[Dict[str, Any]] = []
        for itinerary in itineraries:
            stops.extend(itinerary.get("stops") or [])

        if stops:
            for idx, stop in enumerate(stops):
                text = _build_stop_text(stop, article)
                if not text:
                    skipped_count += 1
                    continue
                vector_id = f"{url}#stop#{idx}"
                metadata = _build_metadata(stop, article)
                vector_payloads.append((vector_id, metadata, text))
                if url:
                    urls_to_mark.append(url)
        else:
            fallback_text = _build_fallback_text(article)
            if not fallback_text:
                skipped_count += 1
                continue
            vector_id = f"{url}#article"
            metadata = _build_metadata(None, article)
            vector_payloads.append((vector_id, metadata, fallback_text))
            if url:
                urls_to_mark.append(url)

        processed_articles += 1
        if len(vector_payloads) >= batch_size:
            print(f"[RAG] Flushing {len(vector_payloads)} vectors (processed_articles={processed_articles})")
            embedded_count += _flush_vectors(pinecone_index, vector_payloads, namespace)
            urls_to_update = list(set(urls_to_mark))
            print(f"[RAG] Marking {len(urls_to_update)} articles as indexed ({status_tag})")
            _mark_articles_indexed(urls_to_update, status_tag)
            vector_payloads = []
            urls_to_mark = []

    if vector_payloads:
        print(f"[RAG] Flushing final {len(vector_payloads)} vectors (processed_articles={processed_articles})")
        embedded_count += _flush_vectors(pinecone_index, vector_payloads, namespace)
        urls_to_update = list(set(urls_to_mark))
        print(f"[RAG] Marking {len(urls_to_update)} articles as indexed ({status_tag})")
        _mark_articles_indexed(urls_to_update, status_tag)

    print(f"[RAG] Completed Lemon8 indexing (embedded={embedded_count}, skipped={skipped_count})")
    return embedded_count, skipped_count


def _flush_vectors(
    pinecone_index,
    payloads: List[Tuple[str, Dict[str, Any], str]],
    namespace: str,
) -> int:
    texts = [payload[2] for payload in payloads]
    print(f"[RAG] Embedding {len(texts)} texts")
    embeddings = _embed_texts(texts)

    vectors = []
    for (vector_id, metadata, _), embedding in zip(payloads, embeddings):
        vectors.append((vector_id, embedding, metadata))

    print(f"[RAG] Upserting {len(vectors)} vectors to Pinecone")
    pinecone_index.upsert(vectors=vectors, namespace=namespace)
    return len(vectors)


def _mark_articles_indexed(urls: List[str], status_tag: str) -> None:
    if not urls:
        return
    print(f"[RAG] Updating processing_status for {len(urls)} urls")
    query = """
        UPDATE public.lemon8_articles
        SET processing_status = %s
        WHERE url = ANY(%s)
    """
    with get_cockroach_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (status_tag, urls))
        conn.commit()
