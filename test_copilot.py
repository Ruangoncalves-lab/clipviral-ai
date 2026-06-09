"""
test_copilot.py — Smoke tests for copilot_engine module.
Validates that the copilot engine can:
  1. Import without errors
  2. Build FFmpeg filters for each supported operation
  3. Handle unsupported operations gracefully
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("Copilot Engine Smoke Tests")
print("=" * 60)

# Test 1: Import
try:
    from src.copilot_engine import (
        SUPPORTED_OPERATIONS,
        build_ffmpeg_filters,
        execute_edit,
        interpret_and_apply
    )
    print(f"[PASS] copilot_engine imported successfully ({len(SUPPORTED_OPERATIONS)} operations)")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Build filters for each operation
test_cases = [
    ("zoom", {"zoom_factor": 0.2, "start_time": 0, "end_time": 5}),
    ("trim_start", {"seconds": 3}),
    ("trim_end", {"seconds": 5}),
    ("speed", {"factor": 1.5}),
    ("slow_motion", {"factor": 2.0}),
    ("brightness", {"value": 0.1}),
    ("contrast", {"value": 1.3}),
    ("saturation", {"value": 1.5}),
    ("flip", {}),
    ("grayscale", {}),
    ("fade_in", {"duration": 1.0}),
    ("fade_out", {"duration": 1.0}),
]

clip_duration = 30.0
passed = 0
failed = 0

for op_name, params in test_cases:
    try:
        result = build_ffmpeg_filters(op_name, params, clip_duration)
        assert isinstance(result, dict), "Should return a dict"
        assert "filters" in result, "Should have 'filters' key"
        assert "input_args" in result, "Should have 'input_args' key"
        print(f"[PASS] {op_name}: filters={len(result['filters'])}, input_args={result['input_args']}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] {op_name}: {e}")
        failed += 1

# Test 3: Unsupported operation should raise
try:
    build_ffmpeg_filters("teleport_to_mars", {}, 30.0)
    print("[FAIL] unsupported: Should have raised ValueError")
    failed += 1
except ValueError as e:
    print(f"[PASS] unsupported: Correctly raised ValueError: {e}")
    passed += 1
except Exception as e:
    print(f"[FAIL] unsupported: Wrong exception type: {type(e).__name__}: {e}")
    failed += 1

# Test 4: Edge cases - extreme parameters clamped
try:
    result = build_ffmpeg_filters("brightness", {"value": 999}, 30.0)
    # Check the filter contains clamped value (max 0.5)
    assert "0.50" in result["filters"][0], "Brightness should be clamped to 0.50"
    print("[PASS] Parameter clamping works correctly")
    passed += 1
except Exception as e:
    print(f"[FAIL] Parameter clamping: {e}")
    failed += 1

# Test 5: Verify interpret_and_apply function signature
import inspect
sig = inspect.signature(interpret_and_apply)
params_list = list(sig.parameters.keys())
expected_params = ["user_command", "input_path", "clip_duration", "api_key"]
for p in expected_params:
    if p in params_list:
        print(f"[PASS] interpret_and_apply has '{p}' parameter")
        passed += 1
    else:
        print(f"[FAIL] Missing '{p}' parameter. Actual: {params_list}")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed > 0:
    sys.exit(1)
print("All copilot smoke tests passed!")
