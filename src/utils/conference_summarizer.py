"""Generate conference summaries using LLM."""
from typing import Optional, List
import yaml

from ..core.models import PaperMetadata
from ..extractors.ollama_client import OllamaClient
from ..extractors.prompts import CONFERENCE_SUMMARY_PROMPT
from ..storage.database import PaperDatabase


class ConferenceSummarizer:
    """Generate summaries of conference paper collections."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        model_name = config['model']['name']
        self.client = OllamaClient(model_name=model_name)
        self.db = PaperDatabase()

    def get_or_generate_summary(self, conference_name: str, force_regenerate: bool = False) -> Optional[str]:
        """Get existing summary or generate new one."""
        
        # Check if summary exists and we're not forcing regeneration (which can be done using the UI)
        if not force_regenerate:
            stored = self.db.get_conference_summary(conference_name)
            if stored:
                print(f"Using cached summary from {stored['generated_at']}")
                return stored['summary']
        
        print(f"Generating new summary for {conference_name}...")
        papers = self.db.get_conference_papers(conference_name, limit=30)
        print(f"Found {len(papers)} papers for summarization")
        if not papers:
            return None
        
        summary = self._generate_summary(papers)
        
        if summary:
            self.db.save_conference_summary(conference_name, summary, len(papers))
            print(f"Summary saved to database")
        
        return summary
    
    def _generate_summary(self, papers: List[PaperMetadata], max_papers: int = 100) -> Optional[str]:
        """Internal method to generate summary from papers."""
        if not papers:
            return None
        
        papers_text = []
        for i, paper in enumerate(papers[:max_papers], 1):
            paper_info = f"Title: **{paper.title}**"
            if paper.overview:
                overview_preview = paper.overview[:200] + "..." if len(paper.overview) > 200 else paper.overview
                paper_info += f"\n   {overview_preview}"
            papers_text.append(paper_info)
    
        combined_text = "\n\n".join(papers_text)
        prompt = CONFERENCE_SUMMARY_PROMPT.format(papers_text=combined_text)
        
        result = self.client.generate_text(
            prompt=prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        if not result['success']:
            print(f"Error generating summary: {result['error']}")
            return None
        
        print(f"Summary generated successfully")
        return result['response'].strip()