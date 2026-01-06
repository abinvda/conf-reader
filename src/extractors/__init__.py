# filepath: src/extractors/__init__.py
"""Extraction modules for different file types."""
from .ollama_client import OllamaClient
from .image_extractor import ImageExtractor

__all__ = ['OllamaClient', 'ImageExtractor']