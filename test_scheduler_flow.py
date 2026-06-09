import requests
import json
import uuid
import time
from datetime import datetime, timedelta, timezone

def run_scheduler_flow_test():
    supabase_url = "https://uksjleoytwuyuahlrvoy.supabase.co"
    anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrc2psZW95dHd1eXVhaGxydm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1OTUwMjcsImV4cCI6MjA5NjE3MTAyN30.tWkbQkUKk_eJTie0cTohb32JgJwHNsXdmzGoC5w_0LI"
    backend_url = "http://127.0.0.1:8000"
    
    print("=== Running Scheduler & Social Integration Integration Test ===")
    
    headers = {
        "apikey": anon_key,
        "Accept": "application/json"
    }
    
    # 1. Fetch a profile using security definer RPC
    print("\n[Step 1] Fetching an active user profile ID ...")
    try:
        profile_res = requests.post(f"{supabase_url}/rest/v1/rpc/test_get_any_profile_id", headers={**headers, "Content-Type": "application/json"}, json={})
        user_id = profile_res.json()
        if not user_id:
            print("[ERROR] No profiles found in the database. Please register a user first.")
            return False
        print(f"Using test User ID: {user_id}")
    except Exception as e:
        print(f"[ERROR] Failed to query profiles: {e}")
        return False
        
    # Setup dummy video and clip using security definer RPC to bypass RLS
    print("Setting up dummy video and clip in DB ...")
    try:
        clip_res = requests.post(
            f"{supabase_url}/rest/v1/rpc/test_setup_video_and_clip",
            headers={**headers, "Content-Type": "application/json"},
            json={"p_user_id": user_id}
        )
        clip_id = clip_res.json()
        if not clip_id:
            print("[ERROR] Failed to get clip_id from setup function.")
            return False
        print(f"Using test Clip ID: {clip_id}")
    except Exception as e:
        print(f"[ERROR] Failed to set up video/clip: {e}")
        return False

    # 2. Test Connection Mock
    print("\n[Step 2] Inserting connected social account (TikTok) ...")
    try:
        res = requests.post(
            f"{supabase_url}/rest/v1/rpc/test_setup_social_account", 
            headers={**headers, "Content-Type": "application/json"}, 
            json={
                "p_user_id": user_id,
                "p_provider": "tiktok",
                "p_account_name": "TikTok Test Account",
                "p_access_token": "mock_token_123",
                "p_refresh_token": "mock_refresh_token_123"
            }
        )
        if res.status_code in [200, 201, 204]:
            print("[OK] Connected social account created successfully!")
        else:
            print(f"[ERROR] Failed to insert social account via RPC: {res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Request exception: {e}")
        return False

    # 3. Schedule a post via backend API 5 seconds in the future
    print("\n[Step 3] Scheduling post to publish 5 seconds in the future ...")
    future_time = datetime.now(timezone.utc) + timedelta(seconds=5)
    schedule_payload = {
        "user_id": user_id,
        "clip_id": clip_id,
        "provider": "tiktok",
        "title": "Clip Viral #shorts #tiktok",
        "description": "Motivacional de teste",
        "scheduled_time": future_time.isoformat(),
        "supabase_url": supabase_url,
        "supabase_key": anon_key
    }
    
    try:
        res = requests.post(f"{backend_url}/api/schedule", json=schedule_payload)
        if res.status_code == 200:
            print(f"[OK] Post scheduled successfully! Server response: {res.json()}")
            post_id = res.json()["data"][0]["id"]
        else:
            print(f"[ERROR] Scheduling failed: {res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Request exception: {e}")
        return False

    # 4. Wait for background daemon to process it
    print("\n[Step 4] Waiting for background daemon thread to process the scheduled post (checking every 5s) ...")
    max_wait = 30
    elapsed = 0
    success = False
    
    while elapsed < max_wait:
        time.sleep(5)
        elapsed += 5
        print(f"Elapsed: {elapsed}s... checking status")
        
        try:
            status_res = requests.post(
                f"{supabase_url}/rest/v1/rpc/test_get_scheduled_post_status",
                headers={**headers, "Content-Type": "application/json"},
                json={"p_post_id": post_id}
            )
            current_status = status_res.json()
            if current_status:
                print(f"Current post status in DB: {current_status}")
                if current_status == "posted":
                    print("[OK] Success! Background daemon successfully picked up the post, simulated upload, and updated status to 'posted'!")
                    success = True
                    break
                elif current_status == "failed":
                    print("[ERROR] Post status updated to failed")
                    break
        except Exception as e:
            print(f"[ERROR] Checking status failed: {e}")
            
    if not success:
        print("[ERROR] Post did not transition to 'posted' status within timeout.")
        return False

    # 5. Cleanup
    print("\n[Step 5] Cleaning up test records ...")
    try:
        requests.post(
            f"{supabase_url}/rest/v1/rpc/test_cleanup_records",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "p_post_id": post_id,
                "p_user_id": user_id,
                "p_provider": "tiktok"
            }
        )
        print("[OK] Cleanup completed.")
    except Exception as e:
        print(f"[WARNING] Cleanup failed: {e}")
        
    print("\n=== All Integration Tests Completed Successfully ===")
    return True

if __name__ == "__main__":
    run_scheduler_flow_test()
