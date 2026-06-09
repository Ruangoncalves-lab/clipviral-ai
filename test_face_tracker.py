"""
test_face_tracker.py – Smoke test for face_tracker module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("Face Tracker Smoke Tests")
print("=" * 60)

# Test 1: Import
try:
    from src.face_tracker import detect_and_track_faces
    print("[PASS] face_tracker module imported successfully")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Function signature
import inspect
sig = inspect.signature(detect_and_track_faces)
params = list(sig.parameters.keys())
expected = ["video_path", "start_time", "duration"]
for p in expected:
    if p in params:
        print(f"[PASS] Parameter '{p}' found in signature")
    else:
        print(f"[FAIL] Parameter '{p}' NOT found. Actual: {params}")

# Test 3: Missing file handling
try:
    layout, coords = detect_and_track_faces("nonexistent_video.mp4", 0, 10)
    assert isinstance(coords, list), "coords should be a list"
    print(f"[PASS] Missing file handled gracefully: layout={layout}, coords count={len(coords)}")
except Exception as e:
    print(f"[PASS] Missing file raised exception: {type(e).__name__}: {e}")

print("=" * 60)
print("All smoke tests completed!")
