from django.core.management.base import BaseCommand
from adminSection.models import Proposal
from adminSection.utils import extract_text_from_file, compute_embedding
import time

class Command(BaseCommand):
    help = "Generate missing text and embeddings for all proposals"

    def handle(self, *args, **kwargs):
        proposals = Proposal.objects.all()
        total = proposals.count()
        processed = 0
        skipped = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n🔍 Starting embedding generation for {total} proposals...\n"
        ))

        for proposal in proposals:
            processed += 1
            self.stdout.write(f"Processing ({processed}/{total}): {proposal.title}")

            # ✅ Skip if already has embedding AND extracted text
            if proposal.embedding and proposal.extracted_text:
                skipped += 1
                self.stdout.write(self.style.WARNING(" → Skipped (already processed)\n"))
                continue

            # ✅ Extract text if missing
            if not proposal.extracted_text:
                try:
                    text = extract_text_from_file(proposal.document.path)
                    proposal.extracted_text = text
                    self.stdout.write(" → Extracted text")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f" → Text extraction failed: {e}"))
                    continue

            # ✅ Generate embedding
            try:
                embedding = compute_embedding(proposal.extracted_text)
                proposal.embedding = embedding
                proposal.save()
                self.stdout.write(self.style.SUCCESS(" → Embedding generated ✅\n"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f" → Embedding error: {e}"))

            time.sleep(0.1)  # slight pause for readability

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Done! Processed: {processed}, Skipped: {skipped}\n"
        ))
