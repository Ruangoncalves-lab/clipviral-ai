"""
test_youtube.py — Smoke tests for youtube_downloader module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("YouTube Downloader Smoke Tests")
print("=" * 60)

# Test 1: Import
try:
    from src.youtube_downloader import (
        is_valid_youtube_url,
        extract_video_id,
        get_video_info,
        download_video,
        YOUTUBE_REGEX
    )
    print("[PASS] youtube_downloader imported successfully")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

passed = 0
failed = 0

# Test 2: URL validation - valid URLs
valid_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/embed/dQw4w9WgXcQ",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/shorts/dQw4w9WgXcQ",
]

for url in valid_urls:
    if is_valid_youtube_url(url):
        print(f"[PASS] Valid URL accepted: {url[:50]}...")
        passed += 1
    else:
        print(f"[FAIL] Valid URL rejected: {url}")
        failed += 1

# Test 3: URL validation - invalid URLs
invalid_urls = [
    "https://google.com",
    "https://vimeo.com/12345",
    "not a url at all",
    "",
    "https://youtube.com/channel/abc",
]

for url in invalid_urls:
    if not is_valid_youtube_url(url):
        print(f"[PASS] Invalid URL correctly rejected: {url[:50]}")
        passed += 1
    else:
        print(f"[FAIL] Invalid URL incorrectly accepted: {url}")
        failed += 1

# Test 4: Video ID extraction
test_extractions = [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtube.com/shorts/abc12345678", "abc12345678"),
]

for url, expected_id in test_extractions:
    result = extract_video_id(url)
    if result == expected_id:
        print(f"[PASS] Extracted ID '{result}' from {url[:40]}...")
        passed += 1
    else:
        print(f"[FAIL] Expected '{expected_id}', got '{result}' from {url}")
        failed += 1

# Test 5: Invalid URL returns None for extraction
result = extract_video_id("https://google.com")
if result is None:
    print("[PASS] extract_video_id returns None for invalid URL")
    passed += 1
else:
    print(f"[FAIL] Expected None, got '{result}'")
    failed += 1

# Test 6: download_video raises ValueError for invalid URL
try:
    download_video("https://google.com", "/tmp/test.mp4")
    print("[FAIL] Should have raised ValueError for invalid URL")
    failed += 1
except ValueError as e:
    print(f"[PASS] download_video raises ValueError: {e}")
    passed += 1
except Exception as e:
    print(f"[FAIL] Wrong exception type: {type(e).__name__}: {e}")
    failed += 1

# Test 7: Function signatures
import inspect
for func_name in ['is_valid_youtube_url', 'extract_video_id', 'get_video_info', 'download_video']:
    func = locals().get(func_name) or getattr(sys.modules['src.youtube_downloader'], func_name)
    if callable(func):
        print(f"[PASS] {func_name} is callable")
        passed += 1
    else:
        print(f"[FAIL] {func_name} is not callable")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed > 0:
    sys.exit(1)
print("All YouTube downloader smoke tests passed!")
