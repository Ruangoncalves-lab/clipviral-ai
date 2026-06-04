import requests
import logging

logger = logging.getLogger("supabase_client")

class SupabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        # Normalize trailing slash in URL
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        
        # Setup common headers
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}"
        }

    def update_video_status(self, video_id: str, fields: dict):
        """Updates a video record in public.videos table."""
        url = f"{self.supabase_url}/rest/v1/videos"
        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        params = {
            "id": f"eq.{video_id}"
        }
        
        logger.info(f"PATCH DB Table 'videos' for ID {video_id}: {fields}")
        response = requests.patch(url, headers=headers, params=params, json=fields)
        if response.status_code not in [200, 201, 204]:
            raise RuntimeError(f"Failed to update video status in database: {response.text}")
        return response.json()

    def download_video(self, storage_path: str) -> bytes:
        """Downloads a video file from 'videos' storage bucket."""
        # storage_path is like 'user_id/video_name.mp4'
        url = f"{self.supabase_url}/storage/v1/object/videos/{storage_path}"
        logger.info(f"GET Storage Bucket 'videos' path: {storage_path}")
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download video from Storage: {response.text}")
        return response.content

    def upload_clip(self, storage_path: str, file_path: str):
        """Uploads a clip file to 'clips' storage bucket."""
        url = f"{self.supabase_url}/storage/v1/object/clips/{storage_path}"
        headers = {
            **self.headers,
            "Content-Type": "video/mp4"
        }
        logger.info(f"POST Storage Bucket 'clips' path: {storage_path}")
        with open(file_path, "rb") as f:
            response = requests.post(url, headers=headers, data=f)
            
        if response.status_code != 200:
            raise RuntimeError(f"Failed to upload clip to Storage: {response.text}")
        return response.json()

    def insert_clip_record(self, record: dict):
        """Inserts a generated clip record into public.clips table."""
        url = f"{self.supabase_url}/rest/v1/clips"
        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        logger.info(f"POST DB Table 'clips': {record}")
        response = requests.post(url, headers=headers, json=record)
        if response.status_code not in [200, 201]:
            raise RuntimeError(f"Failed to insert clip record in database: {response.text}")
        return response.json()
