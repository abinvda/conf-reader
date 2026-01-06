"""Core data models for the research reader."""
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


class Author(BaseModel):
    """Author information."""
    name: str


class PaperMetadata(BaseModel):
    """Extracted paper metadata - simplified to essential fields only."""
    paper_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    authors: List[Author] = []
    overview: Optional[str] = "Unknown"
    conference_name: Optional[str] = "Unknown"
    
    # PDF tracking
    pdf_found: bool = False
    pdf_path: Optional[str] = "Unknown"
    pdf_url: Optional[str] = "Unknown"
    
    # Metadata
    source_files: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    
    def get_authors_string(self, max_authors: int = 30) -> str:
        """Get formatted author string."""
        if not self.authors:
            return "Unknown Authors"
        
        if len(self.authors) <= max_authors:
            return ", ".join(a.name for a in self.authors)
        
        shown = ", ".join(a.name for a in self.authors[:max_authors])
        remaining = len(self.authors) - max_authors
        return f"{shown}, +{remaining} more"


class Conference(BaseModel):
    """Conference metadata."""
    name: str
    year: Optional[int] = None
    path: Path
    
    @property
    def images_path(self) -> Path:
        """Path to images folder."""
        return self.path / "images"
    
    @property
    def pdfs_path(self) -> Path:
        """Path to PDFs folder."""
        return self.path / "pdfs"
    
    @property
    def output_path(self) -> Path:
        """Path to output folder."""
        return self.path / "output"


class SourceFile(BaseModel):
    """Source file metadata."""
    file_path: Path
    file_type: FileType  # Using the FileType enum
    file_size: int = 0
    modified_date: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        """Get file name."""
        return self.file_path.name
    
    @property
    def extension(self) -> str:
        """Get file extension."""
        return self.file_path.suffix.lower()
    
    @property
    def size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size / (1024 * 1024)
    
    class Config:
        """Pydantic config."""
        use_enum_values = True