from django.core.management.base import BaseCommand

from res_backend.rag.lemon8_indexer import index_lemon8_articles


class Command(BaseCommand):
    help = "Index Lemon8 articles into Pinecone for RAG search"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Limit number of articles to index")
        parser.add_argument("--batch-size", type=int, default=200, help="Batch size for embeddings")
        parser.add_argument("--namespace", type=str, default=None, help="Pinecone namespace override")

    def handle(self, *args, **options):
        limit = options.get("limit")
        batch_size = options.get("batch_size")
        namespace = options.get("namespace")

        embedded_count, skipped_count = index_lemon8_articles(
            limit=limit,
            batch_size=batch_size,
            namespace=namespace,
        )

        self.stdout.write(self.style.SUCCESS(f"Indexed {embedded_count} vectors"))
        if skipped_count:
            self.stdout.write(self.style.WARNING(f"Skipped {skipped_count} empty items"))
