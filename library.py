"""
Library management system for storing chapters and reading progress
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class Library:
    """Manages book chapters and reading progress"""
    
    def __init__(self, data_file: str = 'library_data.json'):
        self.data_file = data_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Load library data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading library data: {e}")
                return {'chapters': {}, 'progress': {}}
        return {'chapters': {}, 'progress': {}}
    
    def _save_data(self) -> None:
        """Save library data to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving library data: {e}")
    
    def add_chapter(self, chapter_id: str, title: str, content: str, 
                   audio_filename: str) -> Dict:
        """
        Add a new chapter to the library
        
        Args:
            chapter_id: Unique identifier for the chapter
            title: Chapter title
            content: Chapter text content
            audio_filename: Name of the audio file
            
        Returns:
            Dict containing chapter information
        """
        chapter_data = {
            'id': chapter_id,
            'title': title,
            'content': content,
            'audio_filename': audio_filename,
            'created_at': datetime.now().isoformat(),
            'word_count': len(content),
            'char_count': len(content)
        }
        
        self.data['chapters'][chapter_id] = chapter_data
        self.data['progress'][chapter_id] = {
            'current_time': 0,
            'last_read': datetime.now().isoformat()
        }
        self._save_data()
        
        return chapter_data
    
    def get_chapter(self, chapter_id: str) -> Optional[Dict]:
        """Get chapter by ID"""
        return self.data['chapters'].get(chapter_id)
    
    def get_all_chapters(self) -> List[Dict]:
        """Get all chapters sorted by creation date (newest first)"""
        chapters = list(self.data['chapters'].values())
        chapters.sort(key=lambda x: x['created_at'], reverse=True)
        return chapters
    
    def delete_chapter(self, chapter_id: str) -> bool:
        """
        Delete a chapter from the library
        
        Args:
            chapter_id: ID of the chapter to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if chapter_id in self.data['chapters']:
            # Get audio filename before deleting
            audio_filename = self.data['chapters'][chapter_id].get('audio_filename')
            
            # Delete from data
            del self.data['chapters'][chapter_id]
            if chapter_id in self.data['progress']:
                del self.data['progress'][chapter_id]
            
            self._save_data()
            
            # Return audio filename so it can be deleted
            return audio_filename
        return None
    
    def update_progress(self, chapter_id: str, current_time: float) -> None:
        """
        Update reading progress for a chapter
        
        Args:
            chapter_id: ID of the chapter
            current_time: Current playback time in seconds
        """
        if chapter_id in self.data['chapters']:
            self.data['progress'][chapter_id] = {
                'current_time': current_time,
                'last_read': datetime.now().isoformat()
            }
            self._save_data()
    
    def get_progress(self, chapter_id: str) -> Optional[Dict]:
        """Get reading progress for a chapter"""
        return self.data['progress'].get(chapter_id)
    
    def get_chapter_count(self) -> int:
        """Get total number of chapters"""
        return len(self.data['chapters'])

