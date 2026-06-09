"""
test_broll.py — Smoke tests for broll_generator module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("B-Roll Generator Smoke Tests")
print("=" * 60)

# Test 1: Import
try:
    from src.broll_generator import (
        BROLL_CATEGORIES,
        generate_broll_suggestions,
        generate_simple_suggestions
    )
    print(f"[PASS] broll_generator imported successfully ({len(BROLL_CATEGORIES)} categories)")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

passed = 0
failed = 0

# Test 2: Verify all B-Roll categories exist
expected_categories = ["illustration", "data_viz", "scene", "object", "environment", "metaphor", "text_overlay"]
for cat in expected_categories:
    if cat in BROLL_CATEGORIES:
        print(f"[PASS] Category '{cat}' exists")
        passed += 1
    else:
        print(f"[FAIL] Category '{cat}' missing")
        failed += 1

# Test 3: Simple fallback suggestions work with keywords
test_transcript = "Quando falamos de dinheiro e crescimento no negócio, a tecnologia é fundamental para o sucesso."
suggestions = generate_simple_suggestions(test_transcript, 30.0)
if isinstance(suggestions, list) and len(suggestions) > 0:
    print(f"[PASS] Simple suggestions returned {len(suggestions)} items for keyword transcript")
    passed += 1
else:
    print(f"[FAIL] Simple suggestions returned empty for keyword transcript")
    failed += 1

# Test 4: Suggestion structure validation
if suggestions:
    first = suggestions[0]
    required_keys = ["timestamp_start", "timestamp_end", "category", "visual_description", "reason", "text_context"]
    all_keys_present = all(k in first for k in required_keys)
    if all_keys_present:
        print(f"[PASS] Suggestion has all required keys: {required_keys}")
        passed += 1
    else:
        missing = [k for k in required_keys if k not in first]
        print(f"[FAIL] Missing keys: {missing}")
        failed += 1
    
    # Check timestamp validity
    if 0 <= first["timestamp_start"] < first["timestamp_end"] <= 30.0:
        print(f"[PASS] Timestamps are valid: {first['timestamp_start']}s - {first['timestamp_end']}s")
        passed += 1
    else:
        print(f"[FAIL] Invalid timestamps: {first['timestamp_start']}s - {first['timestamp_end']}s")
        failed += 1
    
    # Check category is valid
    if first["category"] in BROLL_CATEGORIES:
        print(f"[PASS] Category '{first['category']}' is valid")
        passed += 1
    else:
        print(f"[FAIL] Invalid category: {first['category']}")
        failed += 1
else:
    print("[SKIP] No suggestions to validate structure")

# Test 5: Empty transcript returns empty list
empty_result = generate_simple_suggestions("", 30.0)
if empty_result == []:
    print("[PASS] Empty transcript returns empty list")
    passed += 1
else:
    print(f"[FAIL] Empty transcript should return [], got {len(empty_result)} items")
    failed += 1

# Test 6: No matching keywords returns empty list
no_match = generate_simple_suggestions("asdfghjkl qwertyuiop zxcvbnm", 30.0)
if len(no_match) == 0:
    print("[PASS] No matching keywords returns empty list")
    passed += 1
else:
    print(f"[FAIL] Should return empty for non-matching text, got {len(no_match)}")
    failed += 1

# Test 7: Function signatures
import inspect
sig = inspect.signature(generate_broll_suggestions)
params_list = list(sig.parameters.keys())
expected_params = ["transcript", "clip_duration", "api_key", "num_suggestions"]
for p in expected_params:
    if p in params_list:
        print(f"[PASS] generate_broll_suggestions has '{p}' parameter")
        passed += 1
    else:
        print(f"[FAIL] Missing '{p}' parameter")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed > 0:
    sys.exit(1)
print("All B-Roll generator smoke tests passed!")
