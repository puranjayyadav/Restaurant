import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import psycopg2
import requests
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from supabase import create_client

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CHAT_ENDPOINT = f"{OPENROUTER_URL}/chat/completions"
OPENROUTER_EMBEDDINGS_ENDPOINT = f"{OPENROUTER_URL}/embeddings"


def _get_env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _get_openrouter_key() -> str:
    return _get_env("OPENROUTER_API_KEY")


def _openrouter_headers() -> Dict[str, str]:
    api_key = _get_openrouter_key()
    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _call_openrouter_chat(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a SQL assistant. Return ONLY a single SQL SELECT query, "
                    "no markdown, no commentary. The query MUST reference only the "
                    "lemon8_articles table and must be read-only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    resp = requests.post(
        OPENROUTER_CHAT_ENDPOINT,
        headers=_openrouter_headers(),
        data=json.dumps(payload),
        timeout=30,
    )
    if resp.status_code != 200:
        raise ValueError(f"OpenRouter error: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_openrouter_embedding(text: str, model: str) -> List[float]:
    payload = {"model": model, "input": text}
    resp = requests.post(
        OPENROUTER_EMBEDDINGS_ENDPOINT,
        headers=_openrouter_headers(),
        data=json.dumps(payload),
        timeout=30,
    )
    if resp.status_code != 200:
        raise ValueError(f"OpenRouter error: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["data"][0]["embedding"]


def _normalize_sql(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = re.sub(r"^```[a-zA-Z]*\n?", "", sql)
        sql = re.sub(r"\n?```$", "", sql)
    return sql.strip()


def _validate_sql(sql: str) -> Tuple[bool, str]:
    if not re.match(r"^\s*select\b", sql, flags=re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    forbidden = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
    ]
    if re.search(r"\b(" + "|".join(forbidden) + r")\b", sql, flags=re.IGNORECASE):
        return False, "Query contains forbidden keywords."

    tables = re.findall(r"\b(from|join)\s+([a-zA-Z0-9_\.\"`]+)", sql, flags=re.IGNORECASE)
    if not tables:
        return False, "Query must include a FROM clause."

    allowed = {"lemon8_articles"}
    for _, raw in tables:
        cleaned = raw.replace('"', "").replace("`", "")
        table = cleaned.split(".")[-1].strip()
        if table not in allowed:
            return False, f"Table not allowed: {table}"

    return True, ""


def _apply_limit(sql: str, limit: int) -> str:
    if re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
        return sql
    return f"{sql.rstrip().rstrip(';')} LIMIT {limit}"


def _build_db_url() -> str:
    url = _get_env("SUPABASE_DB_URL")
    if url:
        return url

    host = _get_env("SUPABASE_DB_HOST") or _get_env("PGHOST")
    user = _get_env("SUPABASE_DB_USER") or _get_env("PGUSER")
    password = _get_env("SUPABASE_DB_PASSWORD") or _get_env("PGPASSWORD")
    name = _get_env("SUPABASE_DB_NAME") or _get_env("PGDATABASE")
    port = _get_env("SUPABASE_DB_PORT") or _get_env("PGPORT") or "5432"
    if not (host and user and password and name):
        return ""
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def _rows_to_json(columns: List[str], rows: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
    data = []
    for row in rows:
        item = {}
        for idx, col in enumerate(columns):
            item[col] = _json_safe(row[idx])
        data.append(item)
    return data


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def lemon8_sql_extract(request):
    data = request.data or {}
    query = data.get("query")
    sql = data.get("sql")
    limit = int(data.get("limit", 50))

    if not sql and not query:
        return Response(
            {"error": "Provide either 'query' or 'sql'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not sql:
        model = data.get("model") or _get_env("OPENROUTER_CHAT_MODEL") or "openai/gpt-4o-mini"
        prompt = (
            "Write a SQL SELECT query for the lemon8_articles table to answer: "
            f"{query}. If the query is ambiguous, make a reasonable assumption."
        )
        try:
            sql = _call_openrouter_chat(prompt, model)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    sql = _normalize_sql(sql)
    is_valid, reason = _validate_sql(sql)
    if not is_valid:
        return Response({"error": reason, "sql": sql}, status=status.HTTP_400_BAD_REQUEST)

    sql = _apply_limit(sql, limit)

    db_url = _build_db_url()
    if not db_url:
        return Response(
            {"error": "Missing DB config. Set SUPABASE_DB_URL or PG* env vars."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout TO 5000")
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
        result = _rows_to_json(columns, rows)
        return Response({"sql": sql, "rows": result}, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response({"error": str(exc), "sql": sql}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def lemon8_semantic_search(request):
    data = request.data or {}
    query = data.get("query")
    if not query:
        return Response(
            {"error": "Missing 'query'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    k = int(data.get("k", 5))
    threshold = float(data.get("threshold", 0.2))
    embed_model = data.get("embedding_model") or _get_env("OPENROUTER_EMBEDDING_MODEL") or "text-embedding-3-small"

    try:
        embedding = _call_openrouter_embedding(query, embed_model)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    supabase_url = _get_env("SUPABASE_URL")
    supabase_key = _get_env("SUPABASE_SERVICE_KEY") or _get_env("SUPABASE_SERVICE_ROLE_KEY")
    if not (supabase_url and supabase_key):
        return Response(
            {"error": "Missing SUPABASE_URL or service role key."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        supabase = create_client(supabase_url, supabase_key)
        response = supabase.rpc(
            "match_lemon8_articles",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": k,
            },
        ).execute()
        return Response({"results": response.data or []}, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
