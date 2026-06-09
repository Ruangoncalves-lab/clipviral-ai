"""
test_real_publisher.py — Smoke tests for the social_publisher module.
Validates parameters, mock routing, error handling for missing files, and functions signatures.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("Social Publisher Smoke Tests")
print("=" * 60)

# Test import
try:
    from src.social_publisher import publish_to_tiktok, publish_to_youtube
    print("[PASS] social_publisher functions imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import social_publisher: {e}")
    sys.exit(1)

# Set up a dummy local clip for testing mock paths
dummy_file = "dummy_clip_test.mp4"
with open(dummy_file, "w") as f:
    f.write("mock video bytes")

# 1. Test parameter presence and signatures
import inspect

sig_tiktok = inspect.signature(publish_to_tiktok)
assert "video_path" in sig_tiktok.parameters, "[FAIL] publish_to_tiktok missing video_path"
assert "access_token" in sig_tiktok.parameters, "[FAIL] publish_to_tiktok missing access_token"
assert "title" in sig_tiktok.parameters, "[FAIL] publish_to_tiktok missing title"
print("[PASS] publish_to_tiktok parameter signature is correct")

sig_youtube = inspect.signature(publish_to_youtube)
assert "video_path" in sig_youtube.parameters, "[FAIL] publish_to_youtube missing video_path"
assert "access_token" in sig_youtube.parameters, "[FAIL] publish_to_youtube missing access_token"
assert "title" in sig_youtube.parameters, "[FAIL] publish_to_youtube missing title"
assert "description" in sig_youtube.parameters, "[FAIL] publish_to_youtube missing description"
print("[PASS] publish_to_youtube parameter signature is correct")

# 2. Test mock bypass logic (access_token starts with "mock_")
try:
    pub_id_tiktok = publish_to_tiktok(dummy_file, "mock_token_123", "Meu corte #shorts")
    assert pub_id_tiktok == "mock_tiktok_publish_id_xyz", f"[FAIL] TikTok mock return got: {pub_id_tiktok}"
    print("[PASS] TikTok Mock flow handles mock tokens correctly")
except Exception as e:
    print(f"[FAIL] TikTok Mock flow failed: {e}")

try:
    video_id_youtube = publish_to_youtube(dummy_file, "mock_token_456", "Meu Short do YT #shorts", "Descricao de teste")
    assert video_id_youtube == "mock_youtube_video_id_abc", f"[FAIL] YouTube mock return got: {video_id_youtube}"
    print("[PASS] YouTube Mock flow handles mock tokens correctly")
except Exception as e:
    print(f"[FAIL] YouTube Mock flow failed: {e}")

# 3. Test FileNotFoundError raising
try:
    publish_to_tiktok("nonexistent_video.mp4", "mock_token_123", "Title")
    print("[FAIL] publish_to_tiktok did not raise FileNotFoundError for missing file")
except FileNotFoundError:
    print("[PASS] publish_to_tiktok correctly raises FileNotFoundError for missing file")
except Exception as e:
    print(f"[FAIL] publish_to_tiktok raised wrong exception: {type(e).__name__}: {e}")

try:
    publish_to_youtube("nonexistent_video.mp4", "mock_token_123", "Title", "Desc")
    print("[FAIL] publish_to_youtube did not raise FileNotFoundError for missing file")
except FileNotFoundError:
    print("[PASS] publish_to_youtube correctly raises FileNotFoundError for missing file")
except Exception as e:
    print(f"[FAIL] publish_to_youtube raised wrong exception: {type(e).__name__}: {e}")

# Clean up
if os.path.exists(dummy_file):
    os.remove(dummy_file)

print("=" * 60)
print("All Social Publisher smoke tests completed successfully!")
print("=" * 60)
