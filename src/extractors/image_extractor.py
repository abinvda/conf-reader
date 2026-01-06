"""Extract paper information from poster images using vision models."""
import json
import re
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from rich.console import Console

from ..core.models import SourceFile, PaperMetadata, Author
from .ollama_client import OllamaClient
from .prompts import get_extraction_prompt
from .json_utils import extract_json_safely, validate_paper_data

console = Console()

class ImageExtractor:
    """Extract structured paper data from poster images."""
    
    def __init__(self, model_name: str = "llama3.2-vision:11b",
                 temperature: float = 0.1, verbose: bool = True):
        self.client = OllamaClient(model_name=model_name)
        self.temperature = temperature
        self.verbose = verbose
        
        self.stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "json_errors": 0,
            "retries": 0
        }
    
    def extract_from_image(self, source_file: SourceFile, retry:bool = True) -> Dict:
        """Extract paper metadata from poster image."""
        result = {
            'success': False,
            'paper_metadata': None,
            'raw_response': '',
            'error': None,
            'processing_time': 0
        }
        
        if not self.client.check_connection():
            result['error'] = "Cannot connect to Ollama. Is it running?"
            self.stats['failed'] += 1
            return result
        
        # Try with detailed prompt first
        result = self._attempt_extraction(source_file, use_simple=False)
        
        # If failed and retry enabled, try with simpler prompt
        if not result['success'] and retry:
            if self.verbose:
                console.print("[yellow]Retrying with simpler prompt...[/yellow]")
            
            self.stats['retries'] += 1
            result = self._attempt_extraction(source_file, use_simple=True)
        
        self.stats['processed'] += 1
        return result
    
    def _attempt_extraction(self, source_file: SourceFile, use_simple: bool = False) -> Dict:
        """Single extraction attempt."""
        result = {
            'success': False,
            'paper_metadata': None,
            'raw_response': '',
            'error': None,
            'processing_time': 0
        }
        
        prompt = get_extraction_prompt(use_simple=use_simple)
        
        if self.verbose:
            prompt_type = "simple" if use_simple else "detailed"
            console.print(f"\n[cyan]Processing:[/cyan] {source_file.file_path.name} ({prompt_type} prompt)")
            console.print(f"[dim]Sending to Ollama...[/dim]")
        
        start_time = datetime.now()
        response = self.client.analyze_image(image_path=source_file.file_path, prompt=prompt, temperature=self.temperature)
        end_time = datetime.now()
        
        result['processing_time'] = (end_time - start_time).total_seconds()
        
        if self.verbose:
            console.print(f"[green]✓ Ollama responded in {result['processing_time']:.1f} seconds[/green]")
        
        if not response['success']:
            result['error'] = response['error']
            self.stats['failed'] += 1
            if self.verbose:
                console.print(f"[red]✗ Error: {result['error']}[/red]")
            return result
        
        result['raw_response'] = response['response']
        
        if self.verbose:
            console.print("\n[bold]Raw Model Response:[/bold]")
            console.print("[dim]" + "="*60 + "[/dim]")
            console.print(result['raw_response'])
            console.print("[dim]" + "="*60 + "[/dim]\n")
        
        if self.verbose:
            console.print("[cyan]Attempting to parse JSON...[/cyan]")
        
        paper_metadata = self._parse_response(
            response['response'], 
            source_file.file_path
        )
        
        if paper_metadata:
            result['success'] = True
            result['paper_metadata'] = paper_metadata
            self.stats['successful'] += 1
            if self.verbose:
                console.print("[green]✓ Successfully parsed paper metadata[/green]")
        else:
            result['error'] = "Failed to parse model response as JSON"
            self.stats['json_errors'] += 1
            if self.verbose:
                console.print("[red]✗ JSON parsing failed[/red]")
        
        return result
    
    def _parse_response(self, 
                       response_text: str, 
                       source_path: Path) -> Optional[PaperMetadata]:
        """
        Parse LLM response into PaperMetadata object.
        
        Args:
            response_text: Raw text from LLM
            source_path: Path to source image
            
        Returns:
            PaperMetadata object or None if parsing fails
        """
        try:
            # Use robust JSON extraction
            data = extract_json_safely(response_text)
            
            if data is None:
                if self.verbose:
                    console.print("[red]Could not extract valid JSON from response[/red]")
                return None
            
            # Validate and fix data structure
            data = validate_paper_data(data)
            
            if self.verbose:
                console.print("[green]✓ JSON parsed and validated[/green]")
            
            # Create Author objects (just names)
            authors = []
            for author_name in data.get('authors', []):
                if author_name:
                    authors.append(Author(name=author_name))
            
            # Create PaperMetadata with simplified fields
            paper = PaperMetadata(
                title=data.get('title', 'Untitled'),
                authors=authors,
                overview=data.get('overview'),
                source_files=[str(source_path)],
                pdf_found=False  # Will be updated later when matching PDFs
            )
            
            return paper
            
        except Exception as e:
            if self.verbose:
                console.print(f"[red]⚠️  Error creating PaperMetadata:[/red] {e}")
            return None
    
    def _clean_json_response(self, text: str) -> str:
        """
        Clean LLM response to extract JSON.
        
        Sometimes models wrap JSON in markdown:
        ```json
        { ... }
        ```
        
        Args:
            text: Raw response text
            
        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON object (starts with { ends with })
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        
        return text.strip()
    
    def batch_extract(self, source_files: List[SourceFile]) -> List[Dict]:
        """
        Extract from multiple images.
        
        Args:
            source_files: List of SourceFile objects
            
        Returns:
            List of extraction results
        """
        results = []
        for source_file in source_files:
            result = self.extract_from_image(source_file)
            results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get extraction statistics."""
        return self.stats.copy()