"""Extract detailed overview from PDF files using Ollama."""
from pathlib import Path
from typing import Optional
import yaml
import fitz  # PyMuPDF

from .ollama_client import OllamaClient


class PDFExtractor:
    """Extract detailed paper information from PDFs."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        model_name = config['model']['name']
        self.client = OllamaClient(model_name=model_name)
    
    def extract_detailed_overview(self, pdf_path: Path, max_pages: int = 5) -> Optional[str]:
        """Extract detailed overview from PDF."""
        if not pdf_path.exists():
            return None
        
        try:
            text = self._extract_text_from_pdf(pdf_path, max_pages)
            
            if not text or len(text.strip()) < 100:
                print("Insufficient text extracted from PDF")
                return None
            
            prompt = f"""Analyze this research paper text and provide a detailed overview.

Paper text:
{text[:8000]}

Provide a comprehensive overview including:
1. **Problem Statement**: What problem does this paper address? Why is it important?
2. **Key Contributions**: What are the main contributions or innovations?
3. **Methodology**: What techniques, algorithms, or approaches are used?
4. **Results**: What are the key findings or performance improvements?
5. **Significance**: Why does this work matter? What impact could it have?

Be specific and technical. Extract concrete numbers, dataset names, and model architectures when mentioned.
Keep it under 300 words but be comprehensive.

Format as clear paragraphs with bold headings."""

            result = self.client.generate_text(
                prompt=prompt,
                temperature=0.1,
                max_tokens=2000
            )
            
            if not result['success']:
                print(f"Error extracting from PDF: {result['error']}")
                return None
            
            overview = result['response'].strip()
            
            return overview
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return None
    
    def _extract_text_from_pdf(self, pdf_path: Path, max_pages: int = 5) -> str:
        """Extract text from PDF pages."""
        text: str = ""
        
        try:
            pdf_document = fitz.open(str(pdf_path))
            
            for page_num in range(min(max_pages, len(pdf_document))):
                page = pdf_document[page_num]
                text += str(page.get_text("text"))
                text += "\n\n"  # Separate pages
            
            pdf_document.close()
            
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
        
        return text.strip()