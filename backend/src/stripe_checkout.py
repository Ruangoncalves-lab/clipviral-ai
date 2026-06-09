"""
stripe_checkout.py — Stripe Checkout Session creation and webhook handling.
Creates Stripe Checkout Sessions for credit package purchases and handles 
webhook events to credit user accounts after successful payment.
"""
import os
import logging

logger = logging.getLogger("stripe_checkout")

try:
    import stripe
except ImportError:
    stripe = None
    logger.warning("stripe package not installed. Stripe payments will not be available.")


# ──────────────────────────────────────────────────────────────
#  PLAN DEFINITIONS
# ──────────────────────────────────────────────────────────────

PLANS = {
    "starter": {
        "name": "Starter Pack",
        "credits": 10,
        "price_cents": 0,  # Free
        "price_display": "Grátis",
        "description": "Ideal para testar a renderização com legendas IA automáticas.",
        "features": [
            "10 créditos de vídeo",
            "Legendas automáticas",
            "Exportação 720p",
        ]
    },
    "creator": {
        "name": "Creator Pro",
        "credits": 100,
        "price_cents": 4990,  # R$ 49,90
        "price_display": "R$ 49,90",
        "currency": "brl",
        "description": "Processamento prioritário, renderização livre e suporte de Brand Kit.",
        "features": [
            "100 créditos de vídeo",
            "Processamento prioritário",
            "Brand Kit customizado",
            "Exportação 1080p",
            "Copilot Editor IA",
        ]
    },
    "agency": {
        "name": "Agency Prime",
        "credits": 500,
        "price_cents": 14990,  # R$ 149,90
        "price_display": "R$ 149,90",
        "currency": "brl",
        "description": "Multi-contas, renderização HD e créditos ilimitados para equipe.",
        "features": [
            "500 créditos de vídeo",
            "Multi-contas (até 5)",
            "Renderização 4K",
            "Suporte prioritário",
            "API Access",
            "Copilot + B-Rolls IA",
        ]
    }
}


def configure_stripe():
    """Configure Stripe with the API key from environment."""
    if stripe is None:
        raise RuntimeError("stripe package is not installed. Run: pip install stripe")
    
    api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not api_key:
        raise RuntimeError("STRIPE_SECRET_KEY environment variable is not set.")
    
    stripe.api_key = api_key
    return stripe


def create_checkout_session(
    plan_id: str,
    user_id: str,
    user_email: str,
    success_url: str = "http://localhost:3000?checkout=success",
    cancel_url: str = "http://localhost:3000?checkout=cancelled"
) -> dict:
    """
    Creates a Stripe Checkout Session for a credit package purchase.
    
    Returns:
        { "checkout_url": str, "session_id": str }
    """
    plan = PLANS.get(plan_id)
    if not plan:
        raise ValueError(f"Plano inválido: {plan_id}. Opções: {list(PLANS.keys())}")
    
    if plan["price_cents"] == 0:
        # Free plan - no payment needed, no Stripe key required
        return {
            "checkout_url": None,
            "session_id": None,
            "plan": plan_id,
            "credits": plan["credits"],
            "free": True,
        }
    
    s = configure_stripe()
    try:
        session = s.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=user_email,
            line_items=[{
                "price_data": {
                    "currency": plan.get("currency", "brl"),
                    "product_data": {
                        "name": f"ClipViral AI — {plan['name']}",
                        "description": plan["description"],
                    },
                    "unit_amount": plan["price_cents"],
                },
                "quantity": 1,
            }],
            metadata={
                "user_id": user_id,
                "plan_id": plan_id,
                "credits": str(plan["credits"]),
            },
            success_url=success_url + "&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
        )
        
        logger.info(f"Stripe Checkout session created: {session.id} for user {user_id}")
        
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "plan": plan_id,
            "credits": plan["credits"],
            "free": False,
        }
        
    except Exception as e:
        logger.error(f"Stripe session creation failed: {e}")
        raise RuntimeError(f"Erro ao criar sessão de checkout: {e}")


def handle_checkout_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Handles Stripe webhook for checkout.session.completed events.
    
    Returns:
        { "event_type": str, "user_id": str, "plan_id": str, "credits": int } or None
    """
    s = configure_stripe()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    
    if not webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not set.")
    
    try:
        event = s.Webhook.construct_event(payload, sig_header, webhook_secret)
    except s.error.SignatureVerificationError:
        raise ValueError("Assinatura do webhook inválida.")
    except Exception as e:
        raise RuntimeError(f"Erro ao processar webhook: {e}")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        
        user_id = metadata.get("user_id", "")
        plan_id = metadata.get("plan_id", "")
        credits = int(metadata.get("credits", 0))
        
        logger.info(f"Payment completed: user={user_id}, plan={plan_id}, credits={credits}")
        
        return {
            "event_type": "checkout.session.completed",
            "user_id": user_id,
            "plan_id": plan_id,
            "credits": credits,
            "payment_status": session.get("payment_status", ""),
            "amount_total": session.get("amount_total", 0),
        }
    
    return {"event_type": event["type"], "handled": False}


def get_plans() -> dict:
    """Returns all available plans."""
    return PLANS
