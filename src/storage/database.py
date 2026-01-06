"""SQLite database for storing paper metadata."""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import threading

from ..core.models import PaperMetadata, Author


class PaperDatabase:
    """Manages paper metadata storage in SQLite."""
    
    def __init__(self, db_path: str = "data/database/papers.db"):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False) # check_same_thread=False is required to make changes from different tabs
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        with self._lock:
            cursor = self.conn.cursor()
            
            # Papers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    overview TEXT,
                    conference_name TEXT,
                    pdf_found BOOLEAN DEFAULT 0,
                    pdf_path TEXT,
                    pdf_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    UNIQUE(name)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_authors (
                    paper_id TEXT,
                    author_id INTEGER,
                    author_order INTEGER,
                    FOREIGN KEY (paper_id) REFERENCES papers(paper_id),
                    FOREIGN KEY (author_id) REFERENCES authors(author_id),
                    PRIMARY KEY (paper_id, author_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT,
                    file_path TEXT NOT NULL,
                    file_type TEXT,
                    FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conference_summaries (
                    conference_name TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    paper_count INTEGER
                )
            """)
            
            self.conn.commit()
    
    def save_paper(self, paper: PaperMetadata) -> bool:
        with self._lock:
            try:
                cursor = self.conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO papers (
                        paper_id, title, overview, conference_name, pdf_found, pdf_path, pdf_url,
                        created_at, updated_at, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper.paper_id,
                    paper.title,
                    paper.overview,
                    paper.conference_name,
                    paper.pdf_found,
                    paper.pdf_path,
                    paper.pdf_url,
                    paper.created_at.isoformat(),
                    datetime.now().isoformat(),
                    paper.version
                ))
                

                for order, author in enumerate(paper.authors):
                    cursor.execute("""
                        INSERT OR IGNORE INTO authors (name) VALUES (?)
                    """, (author.name,))
                    
                    cursor.execute("SELECT author_id FROM authors WHERE name = ?", (author.name,))
                    author_id = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO paper_authors (paper_id, author_id, author_order)
                        VALUES (?, ?, ?)
                    """, (paper.paper_id, author_id, order))
                
                for source_file in paper.source_files:
                    cursor.execute("""
                        INSERT OR IGNORE INTO source_files (paper_id, file_path, file_type)
                        VALUES (?, ?, ?)
                    """, (paper.paper_id, source_file, 'image'))
                
                self.conn.commit()
                return True
                
            except Exception as e:
                print(f"Error saving paper: {e}")
                self.conn.rollback()
                return False
    
    def get_paper(self, paper_id: str) -> Optional[PaperMetadata]:
        """Retrieve a paper by ID."""
        with self._lock:
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            cursor.execute("""
                SELECT a.name
                FROM authors a
                JOIN paper_authors pa ON a.author_id = pa.author_id
                WHERE pa.paper_id = ?
                ORDER BY pa.author_order
            """, (paper_id,))
            
            authors = [Author(name=r[0]) for r in cursor.fetchall()]
            
            cursor.execute("""
                SELECT file_path FROM source_files WHERE paper_id = ?
            """, (paper_id,))
            
            source_files = [r[0] for r in cursor.fetchall()]
            
            paper = PaperMetadata(
                paper_id=row['paper_id'],
                title=row['title'],
                authors=authors,
                overview=row['overview'],
                conference_name=row['conference_name'],
                pdf_found=bool(row['pdf_found']),
                pdf_path=row['pdf_path'],
                pdf_url=row['pdf_url'],
                source_files=source_files,
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                version=row['version']
            )
            
            return paper
    
    def get_all_papers(self) -> List[PaperMetadata]:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT paper_id FROM papers")
            paper_ids = [row[0] for row in cursor.fetchall()]
        
        return [p for p in (self.get_paper(pid) for pid in paper_ids) if p is not None]
    
    def search_papers(self, query: str) -> List[PaperMetadata]:
        """Search papers by title, author, or overview."""
        with self._lock:
            cursor = self.conn.cursor()
            
            query_lower = f"%{query.lower()}%"
            
            # Search in titles
            cursor.execute("""
                SELECT DISTINCT paper_id FROM papers 
                WHERE LOWER(title) LIKE ?
            """, (query_lower,))
            paper_ids = set(row[0] for row in cursor.fetchall())
            
            # Search in authors
            cursor.execute("""
                SELECT DISTINCT pa.paper_id
                FROM authors a
                JOIN paper_authors pa ON a.author_id = pa.author_id
                WHERE LOWER(a.name) LIKE ?
            """, (query_lower,))
            paper_ids.update(row[0] for row in cursor.fetchall())
            
            # Search in overview
            cursor.execute("""
                SELECT DISTINCT paper_id FROM papers 
                WHERE LOWER(overview) LIKE ?
            """, (query_lower,))
            paper_ids.update(row[0] for row in cursor.fetchall())
        
        return [p for p in (self.get_paper(pid) for pid in paper_ids) if p is not None]

    def update_overview(self, paper_id: str, overview: str) -> bool:
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE papers 
                    SET overview = ?,
                        updated_at = ?
                    WHERE paper_id = ?
                """, (overview, datetime.now().isoformat(), paper_id))
                
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error updating overview: {e}")
                return False
            
    def get_statistics(self) -> Dict:
        with self._lock:
            cursor = self.conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM papers")
            stats['total_papers'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM papers WHERE pdf_found = 1")
            stats['papers_with_pdf'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM authors")
            stats['unique_authors'] = cursor.fetchone()[0]
            
            return stats
    
    def get_all_conferences(self) -> List[str]:
        """Get list of all unique conference names."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT conference_name FROM papers WHERE conference_name IS NOT NULL ORDER BY conference_name")
            return [row[0] for row in cursor.fetchall()]
        
    def get_conference_papers(self, conference_name: str, limit: Optional[int] = None) -> List[PaperMetadata]:
        """Get all papers from a specific conference."""
        with self._lock:
            cursor = self.conn.cursor()
            
            if limit:
                cursor.execute("""
                    SELECT paper_id FROM papers 
                    WHERE conference_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (conference_name, limit))
            else:
                cursor.execute("""
                    SELECT paper_id FROM papers 
                    WHERE conference_name = ?
                    ORDER BY created_at DESC
                """, (conference_name,))
            
            paper_ids = [row[0] for row in cursor.fetchall()]
            
        return [p for p in (self.get_paper(pid) for pid in paper_ids) if p is not None]

    def get_most_recent_conference(self) -> Optional[str]:
        """Get the conference with the most recent papers."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT conference_name, MAX(created_at) as latest
                FROM papers
                WHERE conference_name IS NOT NULL
                GROUP BY conference_name
                ORDER BY latest DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else None
        
    def save_conference_summary(self, conference_name: str, summary: str, paper_count: int) -> bool:
        """Save or update conference summary."""
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO conference_summaries 
                    (conference_name, summary, generated_at, paper_count)
                    VALUES (?, ?, ?, ?)
                """, (conference_name, summary, datetime.now().isoformat(), paper_count))
                
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error saving summary: {e}")
                return False

    def get_conference_summary(self, conference_name: str) -> Optional[dict]:
        """Get stored conference summary."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT summary, generated_at, paper_count
                FROM conference_summaries
                WHERE conference_name = ?
            """, (conference_name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'summary': row[0],
                    'generated_at': row[1],
                    'paper_count': row[2]
                }
            return None

    def delete_conference_summary(self, conference_name: str) -> bool:
        """Delete conference summary (to force regeneration)."""
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM conference_summaries WHERE conference_name = ?", 
                            (conference_name,))
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error deleting summary: {e}")
                return False
    
    def update_pdf_info(self, paper_id: str, pdf_path: Optional[str] = None, pdf_url: Optional[str] = None) -> bool:
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE papers 
                    SET pdf_found = 1,
                        pdf_path = ?,
                        pdf_url = ?,
                        updated_at = ?
                    WHERE paper_id = ?
                """, (pdf_path, pdf_url, datetime.now().isoformat(), paper_id))
                
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error updating PDF info: {e}")
                return False
    
    def export_to_json(self, output_path: Path):
        papers = self.get_all_papers()
        papers_dict = [paper.model_dump(mode='json') for paper in papers]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(papers_dict, f, indent=2, ensure_ascii=False)
    
    def add_pdf_url_column(self):
        """Add pdf_url column if it doesn't exist."""
        with self._lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute("ALTER TABLE papers ADD COLUMN pdf_url TEXT")
                self.conn.commit()
                print("Added pdf_url column")
            except Exception:
                pass  # Column already exists
            
    def close(self):
        with self._lock:
            self.conn.close()