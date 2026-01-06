"""File system scanner for discovering research papers."""
from pathlib import Path
from typing import List, Set, Optional
from datetime import datetime

from .models import SourceFile, FileType


class FileScanner:
    """Scans directories for PDF and image files."""
    
    def __init__(self, 
                 image_extensions: Optional[Set[str]] = None,
                 pdf_extensions: Optional[Set[str]] = None):
        """
        Initialize scanner.
        
        Args:
            image_extensions: Set of image file extensions
            pdf_extensions: Set of PDF file extensions
        """
        self.image_extensions = image_extensions or {".jpg", ".jpeg", ".png", ".heic"}
        self.pdf_extensions = pdf_extensions or {".pdf"}
        
        self.stats = {
            "total_scanned": 0,
            "pdfs_found": 0,
            "images_found": 0,
            "skipped": 0
        }
    
    def scan_images(self, images_path: Path) -> List[SourceFile]:
        """
        Scan for image files only.
        
        Args:
            images_path: Path to images folder
            
        Returns:
            List of image SourceFile objects
        """
        return self._scan_directory(images_path, file_type_filter=FileType.IMAGE)
    
    def scan_pdfs(self, pdfs_path: Path) -> List[SourceFile]:
        """
        Scan for PDF files only.
        
        Args:
            pdfs_path: Path to PDFs folder
            
        Returns:
            List of PDF SourceFile objects
        """
        return self._scan_directory(pdfs_path, file_type_filter=FileType.PDF)
    
    def _scan_directory(self, 
                       root_path: Path, 
                       file_type_filter: Optional[FileType] = None) -> List[SourceFile]:
        """
        Scan directory for files.
        
        Args:
            root_path: Directory to scan
            file_type_filter: Only return files of this type
            
        Returns:
            List of discovered source files
        """
        if not root_path.exists():
            print(f"⚠️  Path does not exist: {root_path}")
            return []
        
        if not root_path.is_dir():
            print(f"⚠️  Path is not a directory: {root_path}")
            return []
        
        print(f"🔍 Scanning: {root_path}")
        source_files = []
        
        # Only scan immediate directory (no recursion)
        for file_path in root_path.iterdir():
            if file_path.is_file():
                self.stats["total_scanned"] += 1
                source_file = self._create_source_file(file_path)
                
                if source_file:
                    # Apply filter if specified
                    if file_type_filter is None or source_file.file_type == file_type_filter.value:
                        source_files.append(source_file)
                        
                        if source_file.file_type == FileType.PDF:
                            self.stats["pdfs_found"] += 1
                        elif source_file.file_type == FileType.IMAGE:
                            self.stats["images_found"] += 1
                else:
                    self.stats["skipped"] += 1
        
        print(f"✅ Found {len(source_files)} files")
        return sorted(source_files, key=lambda x: x.file_path.name)
    
    def _create_source_file(self, file_path: Path) -> Optional[SourceFile]:
        """
        Create SourceFile object if file type is supported.
        
        Args:
            file_path: Path to file
            
        Returns:
            SourceFile object or None if unsupported
        """
        file_type = self._detect_file_type(file_path)
        
        if file_type == FileType.UNKNOWN:
            return None
        
        try:
            stats = file_path.stat()
            return SourceFile(
                file_path=file_path,
                file_type=file_type,
                file_size=stats.st_size,
                modified_date=datetime.fromtimestamp(stats.st_mtime)
            )
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
            return None
    
    def _detect_file_type(self, file_path: Path) -> FileType:
        """
        Detect file type from extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            FileType enum
        """
        extension = file_path.suffix.lower()
        
        if extension in self.pdf_extensions:
            return FileType.PDF
        elif extension in self.image_extensions:
            return FileType.IMAGE
        else:
            return FileType.UNKNOWN
    
    def get_statistics(self) -> dict:
        """Get scan statistics."""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset scan statistics."""
        self.stats = {
            "total_scanned": 0,
            "pdfs_found": 0,
            "images_found": 0,
            "skipped": 0
        }