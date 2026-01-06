"""Service for managing paper downloads."""
from pathlib import Path
from typing import Tuple, Optional

from .arxiv_downloader import ArxivDownloader
from ..storage.database import PaperDatabase
from ..core.models import PaperMetadata
from ..extractors.pdf_extractor import PDFExtractor


class DownloadService:
    """Coordinate downloading papers and updating database."""
    
    def __init__(self, conferences_root: str = "data/conferences"):
        self.conferences_root = Path(conferences_root)
        self.arxiv_downloader = ArxivDownloader()
        self.database = PaperDatabase()
        self.pdf_extractor = PDFExtractor()
    
    def download_paper(self, paper: PaperMetadata, conference_name: str
    ) -> Tuple[bool, str]:
        """Download paper PDF, extract detailed overview, and update database."""
        pdf_filename = self._generate_pdf_filename(paper)
        output_path = self.conferences_root / conference_name / "pdfs" / pdf_filename
        
        if output_path.exists():
            return False, "PDF already exists locally"
        
        success, message, arxiv_data = self.arxiv_downloader.search_and_download(
            paper.title,
            output_path
        )
        
        if not success:
            return False, message
        
        pdf_url = arxiv_data.get('pdf_url') if arxiv_data else None

        print(f"Extracting detailed overview from PDF...")
        detailed_overview = self.pdf_extractor.extract_detailed_overview(output_path)
        
        if not detailed_overview:
            output_path.unlink()
            return False, f"{message} | Failed to extract overview from PDF"
        
        self.database.update_overview(paper.paper_id, detailed_overview)
        self.database.update_pdf_info(paper.paper_id, str(output_path), pdf_url)
        
        return True, f"{message} | Overview updated from PDF"
    
    def download_paper_from_url(self, paper: PaperMetadata, conference_name: str, url: str) -> Tuple[bool, str]:
        """Download paper from manual URL and extract overview."""
        pdf_filename = self._generate_pdf_filename(paper)
        output_path = self.conferences_root / conference_name / "pdfs" / pdf_filename
        
        if output_path.exists():
            return False, "PDF already exists locally"
        
        success, message = self.arxiv_downloader.download_from_url(url, output_path)
        
        if not success:
            return False, message
        
        print(f"Extracting detailed overview from PDF...")
        detailed_overview = self.pdf_extractor.extract_detailed_overview(output_path)
        
        if not detailed_overview:
            output_path.unlink()
            return False, f"{message} | Failed to extract overview from PDF"
        
        self.database.update_overview(paper.paper_id, detailed_overview)
        self.database.update_pdf_info(paper.paper_id, str(output_path), url)
        
        return True, f"{message} | Overview updated from PDF"
        
    def download_all_missing(self, conference_name: Optional[str] = None) -> dict:
        """Download all papers that don't have PDFs."""
        all_papers = self.database.get_all_papers()
        
        if conference_name:
            papers_to_download = [
                p for p in all_papers 
                if not p.pdf_found and p.conference_name == conference_name
            ]
        else:
            papers_to_download = [p for p in all_papers if not p.pdf_found]
        
        stats = {
            'total': len(papers_to_download),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        print(f"Found {stats['total']} papers to download PDFs for.")
        for paper in papers_to_download:
            conf_name = paper.conference_name or conference_name or "unknown"
            success, message = self.download_paper(paper, conf_name)
            print(f"Paper: {paper.title} - {'Success' if success else 'Failed'}: {message}")
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
                stats['errors'].append({
                    'title': paper.title,
                    'error': message
                })
        print(f"Download summary: {stats['success']} succeeded, {stats['failed']} failed out of {stats['total']}")
        
        return stats
    
    def _generate_pdf_filename(self, paper: PaperMetadata) -> str:
        """Generate PDF filename from paper metadata."""
        title_part = paper.title[:50]
        title_part = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in title_part)
        title_part = '_'.join(title_part.split())
        
        return f"{title_part}_{paper.paper_id[:8]}.pdf"