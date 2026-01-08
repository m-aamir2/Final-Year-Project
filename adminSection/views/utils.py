import os
import logging
import PyPDF2
import docx2txt
from pptx import Presentation
from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np
from nltk.tokenize import sent_tokenize  # For better text chunking

logger = logging.getLogger('adminSection')

# Load SBERT model once at startup
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("SBERT model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load SBERT model: {e}")
    model = None


def extract_text_from_file(file_path):
    """
    Extract text from PDF, TXT, DOCX, or PPTX files.
    Returns cleaned text or empty string.
    """
    try:
        if file_path.endswith('.pdf'):
            text = ''
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
            return text.strip()

        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()

        elif file_path.endswith('.docx'):
            text = docx2txt.process(file_path)
            return text.strip()

        elif file_path.endswith('.pptx'):
            prs = Presentation(file_path)
            text_runs = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_runs.append(shape.text)
            return "\n".join(text_runs).strip()

        else:
            logger.warning(f"Unsupported file type for {file_path}")
            return ''
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ''


def chunk_text(text, max_words=300):
    """
    Split long text into smaller chunks of approximately `max_words` words.
    This helps handle long PDFs that exceed the model's token limit.
    """
    try:
        sentences = sent_tokenize(text)
    except Exception:
        # Fallback if sentence tokenizer not available
        sentences = text.split('.')

    chunks = []
    current_chunk = []
    word_count = 0

    for sent in sentences:
        words = sent.split()
        if word_count + len(words) > max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            word_count = 0
        current_chunk.extend(words)
        word_count += len(words)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def compute_embedding(text):
    """
    Compute SBERT embedding for a given text.
    For long documents, automatically splits text into chunks
    and averages their embeddings.
    Returns a list of floats suitable for JSONField.
    """
    if not text or not model:
        logger.warning("No text provided or SBERT model not loaded.")
        return None

    try:
        # Split into chunks if the document is long
        chunks = chunk_text(text)

        if len(chunks) == 1:
            embedding = model.encode(chunks[0], show_progress_bar=False)
            return embedding.tolist()
        else:
            embeddings = model.encode(chunks, batch_size=8, show_progress_bar=False)
            # Average all chunk embeddings for one document-level vector
            avg_embedding = np.mean(embeddings, axis=0)
            return avg_embedding.tolist()

    except Exception as e:
        logger.error(f"Error computing embedding: {e}")
        return None


def compute_similarity(emb1, emb2):
    """
    Compute cosine similarity between two embeddings.
    Returns a float between 0.0 and 1.0.
    """
    if emb1 is None or emb2 is None:
        return 0.0
    try:
        return util.cos_sim(torch.tensor([emb1]), torch.tensor([emb2]))[0][0].item()
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        return 0.0