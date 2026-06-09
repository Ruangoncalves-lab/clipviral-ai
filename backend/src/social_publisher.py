"""
social_publisher.py — Video publication modules for social platforms.
Integrates directly with the official TikTok Content Posting API v2 and
YouTube Data API v3 resumable upload protocols.
"""
import os
import time
import logging
import requests

logger = logging.getLogger("social_publisher")


def publish_to_tiktok(video_path: str, access_token: str, title: str) -> str:
    """
    Publishes a vertical clip to TikTok using Content Posting API v2.
    Flow: Initialize session, transfer media (PUT binary), complete publish.
    Ref: https://developers.tiktok.com/doc/content-posting-api-v2-direct-posting/
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    # Sandbox Mock Flow
    if access_token.startswith("mock_"):
        logger.info(f"[SIMULATED TIKTOK POST] Title: {title} (File: {os.path.basename(video_path)})")
        time.sleep(2)
        return "mock_tiktok_publish_id_xyz"

    file_size = os.path.getsize(video_path)
    init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    payload = {
        "post_info": {
            "title": title[:150],  # Max 150 chars
            "privacy_level": "MUTUAL_FOLLOW_FRIENDS",  # Safe default for testing
            "disable_duet": False,
            "disable_stitch": False,
            "disable_comment": False
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1
        }
    }
    
    logger.info(f"TikTok API: Initializing upload session of {file_size} bytes...")
    response = requests.post(init_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        raise RuntimeError(f"TikTok API Init failed: {response.text}")
        
    res_data = response.json()
    if res_data.get("error", {}).get("code") != "ok":
        # Fallback to Inbox Flow
        inbox_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        logger.info("Direct posting init restricted. Trying Inbox fallback flow...")
        response = requests.post(inbox_url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"TikTok API Inbox Init failed: {response.text}")
        res_data = response.json()
        if res_data.get("error", {}).get("code") != "ok":
            raise RuntimeError(f"TikTok API Init error: {res_data.get('error')}")
            
    upload_url = res_data["data"]["upload_url"]
    publish_id = res_data["data"].get("publish_id", "tiktok_pub_draft")
    
    # PUT binary file content
    logger.info(f"TikTok API: Transferring media bytes to {upload_url[:50]}...")
    put_headers = {
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
        "Content-Type": "video/mp4"
    }
    
    with open(video_path, "rb") as f:
        video_bytes = f.read()
        
    put_response = requests.put(upload_url, headers=put_headers, data=video_bytes, timeout=120)
    
    if put_response.status_code not in [200, 201]:
        raise RuntimeError(f"TikTok API upload failed: {put_response.text}")
        
    logger.info(f"TikTok API: Publication request submitted. Publish ID: {publish_id}")
    return publish_id


def publish_to_youtube(video_path: str, access_token: str, title: str, description: str = "") -> str:
    """
    Publishes a video to YouTube Data API v3 using the raw Resumable Upload protocol.
    Title / Description should contain #shorts to trigger YouTube Shorts categorization automatically.
    Ref: https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    # Sandbox Mock Flow
    if access_token.startswith("mock_"):
        logger.info(f"[SIMULATED YOUTUBE POST] Title: {title} (File: {os.path.basename(video_path)})")
        time.sleep(2)
        return "mock_youtube_video_id_abc"

    file_size = os.path.getsize(video_path)
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4"
    }
    
    metadata = {
        "snippet": {
            "title": title[:100],  # Max 100 chars
            "description": description or "Video publicado via ClipViral AI #shorts",
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    logger.info(f"YouTube API: Initiating resumable upload session for {file_size} bytes...")
    response = requests.post(init_url, headers=headers, json=metadata, timeout=30)
    
    if response.status_code != 200:
        raise RuntimeError(f"YouTube API Session Init failed: {response.text}")
        
    upload_url = response.headers.get("Location")
    if not upload_url:
        raise RuntimeError("YouTube API did not return Location header in response.")
        
    # PUT binary file content
    logger.info("YouTube API: Sending video binary data to location URL...")
    put_headers = {
        "Content-Type": "video/mp4",
        "Content-Length": str(file_size)
    }
    
    with open(video_path, "rb") as f:
        video_bytes = f.read()
        
    put_response = requests.put(upload_url, headers=put_headers, data=video_bytes, timeout=120)
    
    if put_response.status_code not in [200, 201]:
        raise RuntimeError(f"YouTube API media upload failed: {put_response.text}")
        
    res_data = put_response.json()
    video_id = res_data.get("id", "youtube_video_id")
    logger.info(f"YouTube API: Short uploaded successfully! Video ID: {video_id}")
    return video_id
