"""
test_transcript_api.py — Smoke tests for transcript_api module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("Transcript API Smoke Tests")
print("=" * 60)

# Test 1: Import
try:
    from src.transcript_api import (
        generate_word_transcript,
        SUPPORTED_LANGUAGES,
        _transcribe_local,
        _transcribe_groq,
    )
    print(f"[PASS] transcript_api imported successfully")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

passed = 0
failed = 0

# Test 2: Supported languages
expected_langs = {"pt": "Português", "en": "English", "es": "Español"}
for code, name in expected_langs.items():
    if code in SUPPORTED_LANGUAGES and SUPPORTED_LANGUAGES[code] == name:
        print(f"[PASS] Language '{code}' -> '{name}' exists")
        passed += 1
    else:
        print(f"[FAIL] Language '{code}' missing or wrong")
        failed += 1

# Test 3: Function signatures
import inspect

sig = inspect.signature(generate_word_transcript)
params_list = list(sig.parameters.keys())
expected_params = ["video_path", "language", "model_size"]
for p in expected_params:
    if p in params_list:
        print(f"[PASS] generate_word_transcript has '{p}' parameter")
        passed += 1
    else:
        print(f"[FAIL] Missing '{p}' parameter. Actual: {params_list}")
        failed += 1

# Test 4: Groq transcription function exists and is callable
if callable(_transcribe_groq):
    print("[PASS] _transcribe_groq is callable")
    passed += 1
else:
    print("[FAIL] _transcribe_groq is not callable")
    failed += 1

# Test 5: Local transcription function exists and is callable  
if callable(_transcribe_local):
    print("[PASS] _transcribe_local is callable")
    passed += 1
else:
    print("[FAIL] _transcribe_local is not callable")
    failed += 1

# Test 6: Return type contract (validate with a mock)
# We can't easily test without a real video, but we can check the function handles
# missing files gracefully
try:
    generate_word_transcript("/nonexistent/path.mp4")
    print("[FAIL] Should raise error for nonexistent file")
    failed += 1
except (RuntimeError, Exception) as e:
    print(f"[PASS] Correctly raises error for nonexistent file: {type(e).__name__}")
    passed += 1

# Test 7: Default language parameter
sig = inspect.signature(generate_word_transcript)
default_lang = sig.parameters["language"].default
if default_lang == "pt":
    print(f"[PASS] Default language is 'pt'")
    passed += 1
else:
    print(f"[FAIL] Default language should be 'pt', got '{default_lang}'")
    failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed > 0:
    sys.exit(1)
print("All transcript API smoke tests passed!")
