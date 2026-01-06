"""Ollama API client for vision and text models."""
import base64
from pathlib import Path
from typing import Dict, Any
import requests


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434",
                 model_name: str = "llama3.2-vision:11b", timeout: int = 300):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.api_url = f"{base_url}/api/generate"
    
    def analyze_image(self, image_path: Path, prompt: str,
                     temperature: float = 0.1, max_tokens: int = 2000) -> Dict[str, Any]:
        """Analyze image with vision model."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return {'success': False, 'error': f"Failed to read image: {e}", 'response': None}
        
        payload = {
            'model': self.model_name,
            'prompt': prompt,
            'images': [image_base64],
            'stream': False,
            'options': {'temperature': temperature, 'num_predict': max_tokens}
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'response': result.get('response', ''),
                'model': result.get('model', self.model_name),
                'total_duration': result.get('total_duration', 0),
                'error': None
            }
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Cannot connect to Ollama. Is it running?', 'response': None}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': f'Request timed out after {self.timeout}s', 'response': None}
        except Exception as e:
            return {'success': False, 'error': str(e), 'response': None}
    
    def generate_text(self, prompt: str, temperature: float = 0.1,
                     max_tokens: int = 4000) -> Dict[str, Any]:
        """Generate text without image."""
        payload = {
            'model': self.model_name,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': temperature, 'num_predict': max_tokens}
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return {'success': True, 'response': result.get('response', ''), 'error': None}
        except Exception as e:
            return {'success': False, 'error': str(e), 'response': None}
    
    def check_connection(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False