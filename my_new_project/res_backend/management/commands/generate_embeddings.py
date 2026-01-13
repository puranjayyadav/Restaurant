from django.core.management.base import BaseCommand
from res_backend.embedding_service import EmbeddingService

class Command(BaseCommand):
    help = 'Generate embeddings for venues'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Number of venues to process')
        parser.add_argument('--min-rating', type=float, default=0.0, help='Minimum rating filter')
        parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing (smaller = less timeout risk)')
        parser.add_argument('--regenerate', action='store_true', help='Regenerate all embeddings')

    def handle(self, *args, **options):
        service = EmbeddingService()
        
        if options['regenerate']:
            self.stdout.write('Regenerating all embeddings...')
            # TODO: Add regeneration logic
        else:
            count = service.batch_generate_embeddings(
                limit=options['limit'],
                min_rating=options['min_rating'],
                batch_size=options['batch_size']
            )
            self.stdout.write(self.style.SUCCESS(f'Generated {count} embeddings'))
