"""
test_stripe.py — Smoke tests for stripe_checkout module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

print("=" * 60)
print("Stripe Checkout Smoke Tests")
print("=" * 60)

# Test 1: Import
try:
    from src.stripe_checkout import (
        PLANS,
        create_checkout_session,
        handle_checkout_webhook,
        get_plans,
        configure_stripe,
    )
    print(f"[PASS] stripe_checkout imported successfully ({len(PLANS)} plans)")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

passed = 0
failed = 0

# Test 2: Verify all plans exist
expected_plans = ["starter", "creator", "agency"]
for plan_id in expected_plans:
    if plan_id in PLANS:
        plan = PLANS[plan_id]
        print(f"[PASS] Plan '{plan_id}' exists: {plan['name']} ({plan['price_display']})")
        passed += 1
    else:
        print(f"[FAIL] Plan '{plan_id}' missing")
        failed += 1

# Test 3: Plan structure validation
required_keys = ["name", "credits", "price_cents", "price_display", "description", "features"]
for plan_id, plan in PLANS.items():
    all_keys = all(k in plan for k in required_keys)
    if all_keys:
        print(f"[PASS] Plan '{plan_id}' has all required keys")
        passed += 1
    else:
        missing = [k for k in required_keys if k not in plan]
        print(f"[FAIL] Plan '{plan_id}' missing keys: {missing}")
        failed += 1

# Test 4: Price validation
if PLANS["starter"]["price_cents"] == 0:
    print("[PASS] Starter plan is free (0 cents)")
    passed += 1
else:
    print("[FAIL] Starter plan should be free")
    failed += 1

if PLANS["creator"]["price_cents"] == 4990:
    print("[PASS] Creator plan is R$ 49,90 (4990 cents)")
    passed += 1
else:
    print(f"[FAIL] Creator plan price wrong: {PLANS['creator']['price_cents']}")
    failed += 1

if PLANS["agency"]["price_cents"] == 14990:
    print("[PASS] Agency plan is R$ 149,90 (14990 cents)")
    passed += 1
else:
    print(f"[FAIL] Agency plan price wrong: {PLANS['agency']['price_cents']}")
    failed += 1

# Test 5: get_plans returns all plans
result = get_plans()
if len(result) == 3 and all(p in result for p in expected_plans):
    print(f"[PASS] get_plans() returns all {len(result)} plans")
    passed += 1
else:
    print(f"[FAIL] get_plans() returned {len(result)} plans")
    failed += 1

# Test 6: Free plan checkout (no Stripe API needed)
try:
    result = create_checkout_session(
        plan_id="starter",
        user_id="test-user-123",
        user_email="test@example.com"
    )
    if result.get("free") is True and result.get("credits") == 10:
        print(f"[PASS] Free plan checkout works without Stripe key")
        passed += 1
    else:
        print(f"[FAIL] Free plan result unexpected: {result}")
        failed += 1
except Exception as e:
    print(f"[FAIL] Free plan checkout failed: {e}")
    failed += 1

# Test 7: Invalid plan raises ValueError
try:
    create_checkout_session(
        plan_id="nonexistent",
        user_id="test",
        user_email="test@test.com"
    )
    print("[FAIL] Should raise ValueError for invalid plan")
    failed += 1
except ValueError as e:
    print(f"[PASS] Invalid plan raises ValueError: {e}")
    passed += 1
except RuntimeError:
    print("[PASS] Invalid plan raises error (RuntimeError)")
    passed += 1

# Test 8: Paid plan requires STRIPE_SECRET_KEY
old_key = os.environ.get("STRIPE_SECRET_KEY", "")
os.environ["STRIPE_SECRET_KEY"] = ""
try:
    create_checkout_session(
        plan_id="creator",
        user_id="test",
        user_email="test@test.com"
    )
    print("[FAIL] Should raise error without Stripe key")
    failed += 1
except RuntimeError as e:
    print(f"[PASS] Paid plan requires Stripe key: {type(e).__name__}")
    passed += 1
except Exception as e:
    print(f"[PASS] Paid plan fails without key: {type(e).__name__}")
    passed += 1
finally:
    if old_key:
        os.environ["STRIPE_SECRET_KEY"] = old_key

# Test 9: Function signatures
import inspect
for func_name in ['create_checkout_session', 'handle_checkout_webhook', 'get_plans', 'configure_stripe']:
    func = locals().get(func_name) or globals().get(func_name)
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
print("All Stripe checkout smoke tests passed!")
