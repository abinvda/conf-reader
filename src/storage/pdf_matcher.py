"""Match extracted papers with local PDF files."""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from ..core.models import PaperMetadata, SourceFile


class PDFMatcher:
    """Match papers to PDF files by filename similarity."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize PDF matcher.
        
        Args:
            similarity_threshold: Minimum similarity score (0-1) for matching
        """
        self.similarity_threshold = similarity_threshold
        
        self.stats = {
            'papers_checked': 0,
            'pdfs_matched': 0,
            'no_match': 0
        }
    
    def match_paper_to_pdf(self, 
                          paper: PaperMetadata, 
                          pdf_files: List[SourceFile]) -> Optional[SourceFile]:
        """
        Find best matching PDF for a paper.
        
        Args:
            paper: Paper to match
            pdf_files: List of available PDF files
            
        Returns:
            Best matching SourceFile or None
        """
        if not pdf_files:
            return None
        
        # Generate search strings from paper metadata
        search_strings = self._generate_search_strings(paper)
        
        best_match = None
        best_score = 0.0
        
        for pdf_file in pdf_files:
            # Get filename without extension
            pdf_name = pdf_file.file_path.stem.lower()
            
            # Compare with each search string
            for search_str in search_strings:
                score = self._calculate_similarity(search_str, pdf_name)
                
                if score > best_score:
                    best_score = score
                    best_match = pdf_file
        
        # Return match only if above threshold
        if best_score >= self.similarity_threshold:
            return best_match
        
        return None
    
    def match_all_papers(self, 
                        papers: List[PaperMetadata], 
                        pdf_files: List[SourceFile]) -> Dict[str, Optional[SourceFile]]:
        """
        Match all papers to PDFs.
        
        Args:
            papers: List of papers to match
            pdf_files: List of available PDFs
            
        Returns:
            Dictionary mapping paper_id to matched PDF (or None)
        """
        matches = {}
        
        for paper in papers:
            self.stats['papers_checked'] += 1
            
            matched_pdf = self.match_paper_to_pdf(paper, pdf_files)
            matches[paper.paper_id] = matched_pdf
            
            if matched_pdf:
                self.stats['pdfs_matched'] += 1
                # Update paper metadata
                paper.pdf_found = True
                paper.pdf_path = str(matched_pdf.file_path)
            else:
                self.stats['no_match'] += 1
        
        return matches
    
    def _generate_search_strings(self, paper: PaperMetadata) -> List[str]:
        """
        Generate possible search strings from paper metadata.
        
        Args:
            paper: Paper metadata
            
        Returns:
            List of search strings
        """
        search_strings = []
        
        # Clean title
        clean_title = self._clean_string(paper.title)
        search_strings.append(clean_title)
        
        # Title + first author
        if paper.authors:
            first_author = self._clean_string(paper.authors[0].name)
            # Try "Author_Title" and "Title_Author"
            search_strings.append(f"{first_author}_{clean_title}")
            search_strings.append(f"{clean_title}_{first_author}")
        
        return search_strings
    
    def _clean_string(self, text: str) -> str:
        """
        Clean string for comparison.
        
        Args:
            text: Input string
            
        Returns:
            Cleaned string
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove common words
        stop_words = ['a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
        words = text.split()
        words = [w for w in words if w not in stop_words]
        
        # Join with underscores
        text = '_'.join(words)
        
        # Remove special characters
        text = ''.join(c for c in text if c.isalnum() or c == '_')
        
        return text
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score (0-1)
        """
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def get_statistics(self) -> Dict:
        """Get matching statistics."""
        return self.stats.copy()