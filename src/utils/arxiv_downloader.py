"""Download papers from arXiv."""
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple
import time
import re
from urllib.parse import quote


class ArxivDownloader:
    """Download papers from arXiv using their API."""
    
    def __init__(self, delay: float = 3.0):
        self.base_url = "http://export.arxiv.org/api/query"
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ResearchReader/1.0 (Academic research tool)'
        })
    
    def search_paper(self, title: str, max_results: int = 5) -> Optional[dict]:
        """Search for a paper on arXiv by title."""
        try:
            clean_title = self._clean_title(title)
            
            print(f"Original title: {title}")
            print(f"Cleaned title: {clean_title}")
        
            params = {
                'search_query': f'all:"{clean_title}"',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            print(f"Search query: {params['search_query']}")
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            
            print(f"Found {len(entries)} results")
            
            if not entries:
                return None
            
            entry = entries[0]
            
            id_elem = entry.find('atom:id', ns)
            title_elem = entry.find('atom:title', ns)
            
            if id_elem is None or id_elem.text is None:
                return None
            if title_elem is None or title_elem.text is None:
                return None
            
            arxiv_id = id_elem.text.split('/abs/')[-1]
            arxiv_title = title_elem.text.strip()
            
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            authors = []
            for author in entry.findall('atom:author', ns):
                name_elem = author.find('atom:name', ns)
                if name_elem is not None and name_elem.text is not None:
                    authors.append(name_elem.text)
            
            similarity = self._calculate_similarity(title.lower(), arxiv_title.lower())
            
            return {
                'arxiv_id': arxiv_id,
                'title': arxiv_title,
                'pdf_url': pdf_url,
                'authors': authors,
                'similarity': similarity
            }
            
        except Exception as e:
            print(f"Error searching arXiv: {e}")
            return None
    
    def download_pdf(self, pdf_url: str, output_path: Path) -> bool:
        """Download PDF from URL."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = self.session.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type:
                print(f"Warning: Content type is {content_type}, not PDF")
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if output_path.stat().st_size < 1000:
                print("Warning: Downloaded file is suspiciously small")
                output_path.unlink()
                return False
            
            return True
            
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            if output_path.exists():
                output_path.unlink()
            return False
    
    def search_and_download(self, title: str, output_path: Path, min_similarity: float = 0.6
    ) -> Tuple[bool, str, Optional[dict]]:
        """Search for paper and download if found."""
        result = self.search_paper(title)
        
        if not result:
            return False, "Paper not found on arXiv", None
        
        if result['similarity'] < min_similarity:
            return False, f"Low similarity ({result['similarity']:.2f}): '{result['title']}'", None
        
        time.sleep(self.delay)
        
        success = self.download_pdf(result['pdf_url'], output_path)
        
        if success:
            return True, f"Downloaded from arXiv: {result['arxiv_id']}", result
        else:
            return False, "Failed to download PDF", None
    
    def download_from_url(self, url: str, output_path: Path) -> Tuple[bool, str]:
        try:
            # Check if it's an arXiv abstract URL and convert to PDF URL
            if 'arxiv.org/abs/' in url:
                arxiv_id = url.split('/abs/')[-1].strip()
                url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                print(f"Converted to PDF URL: {url}")
            
            success = self.download_pdf(url, output_path)
            
            if success:
                return True, f"Downloaded from URL: {url}"
            else:
                return False, "Failed to download PDF from URL"
                
        except Exception as e:
            return False, f"Error: {e}"
    
    def _clean_title(self, title: str) -> str:
        """Clean title for search query."""
        title = re.sub(r'[^\w\s-]', ' ', title)
        title = ' '.join(title.split())
        return title
    
    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple similarity between two titles using word overlap."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0