"""Conference folder structure management."""
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
import yaml


@dataclass
class ConferenceFolder:
    """Represents a conference folder structure."""
    name: str
    root_path: Path
    images_path: Path
    pdfs_path: Path
    output_path: Path
    
    def validate(self) -> Dict[str, bool]:
        """
        Check which folders exist.
        
        Returns:
            Dictionary with existence status for each folder
        """
        return {
            'root': self.root_path.exists(),
            'images': self.images_path.exists(),
            'pdfs': self.pdfs_path.exists(),
            'output': self.output_path.exists()
        }
    
    def create_missing_folders(self):
        """Create any missing folders."""
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.images_path.mkdir(exist_ok=True)
        self.pdfs_path.mkdir(exist_ok=True)
        self.output_path.mkdir(exist_ok=True)


class ConferenceManager:
    """Manages conference folder structure."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize conference manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.data_root = Path(self.config['project']['data_root'])
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_conference(self, conference_name: Optional[str] = None) -> ConferenceFolder:
        """
        Get conference folder structure.
        
        Args:
            conference_name: Name of conference (uses default if None)
            
        Returns:
            ConferenceFolder object
        """
        # Ensure we have a conference name
        conf_name: str = (
            conference_name 
            if conference_name is not None 
            else self.config['project']['default_conference']
        )
        
        root_path = self.data_root / conf_name
        
        return ConferenceFolder(
            name=conf_name,
            root_path=root_path,
            images_path=root_path / self.config['folders']['images_subdir'],
            pdfs_path=root_path / self.config['folders']['pdfs_subdir'],
            output_path=root_path / self.config['folders']['output_subdir']
        )
    
    def list_conferences(self) -> list:
        """
        List all available conference folders.
        
        Returns:
            List of conference names
        """
        if not self.data_root.exists():
            return []
        
        conferences = []
        for item in self.data_root.iterdir():
            if item.is_dir():
                conferences.append(item.name)
        
        return sorted(conferences)