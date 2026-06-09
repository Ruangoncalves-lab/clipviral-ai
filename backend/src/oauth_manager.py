"""
oauth_manager.py — OAuth2 flow management for social platform connections.
Handles authorization URL generation, token exchange, and token refresh
for YouTube (Google), TikTok, and Instagram (Meta) APIs.
"""
import os
import time
import logging
import urllib.parse
import requests

logger = logging.getLogger("oauth_manager")


# ──────────────────────────────────────────────────────────────
#  PROVIDER CONFIGURATIONS
# ──────────────────────────────────────────────────────────────

def get_provider_config(provider: str) -> dict:
    """Get OAuth configuration for a provider from environment variables."""
    configs = {
        "youtube": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": [
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
            "redirect_uri": os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:8000/api/oauth/callback/youtube"),
            "profile_url": "https://www.googleapis.com/oauth2/v1/userinfo",
        },
        "tiktok": {
            "client_key": os.environ.get("TIKTOK_CLIENT_KEY", ""),
            "client_secret": os.environ.get("TIKTOK_CLIENT_SECRET", ""),
            "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
            "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
            "scopes": ["user.info.basic", "video.publish", "video.upload"],
            "redirect_uri": os.environ.get("OAUTH_REDIRECT_URI_TIKTOK", "http://localhost:8000/api/oauth/callback/tiktok"),
            "profile_url": "https://open.tiktokapis.com/v2/user/info/",
        },
        "instagram": {
            "client_id": os.environ.get("INSTAGRAM_CLIENT_ID", ""),
            "client_secret": os.environ.get("INSTAGRAM_CLIENT_SECRET", ""),
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "scopes": [
                "instagram_basic",
                "instagram_content_publish",
                "pages_show_list",
                "pages_read_engagement",
            ],
            "redirect_uri": os.environ.get("OAUTH_REDIRECT_URI_INSTAGRAM", "http://localhost:8000/api/oauth/callback/instagram"),
            "profile_url": "https://graph.instagram.com/me",
        },
    }
    
    if provider not in configs:
        raise ValueError(f"Provider inválido: {provider}. Opções: {list(configs.keys())}")
    
    return configs[provider]


SUPPORTED_PROVIDERS = ["youtube", "tiktok", "instagram"]


# ──────────────────────────────────────────────────────────────
#  AUTHORIZATION URL GENERATION
# ──────────────────────────────────────────────────────────────

def generate_auth_url(provider: str, user_id: str) -> str:
    """
    Generate the OAuth2 authorization URL for a provider.
    
    Returns:
        The URL to redirect the user to for authorization.
    """
    config = get_provider_config(provider)
    
    # Build state parameter (user_id encoded for callback)
    state = f"{user_id}:{provider}:{int(time.time())}"
    
    if provider == "youtube":
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    
    elif provider == "tiktok":
        params = {
            "client_key": config["client_key"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": ",".join(config["scopes"]),
            "state": state,
        }
        return f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    
    elif provider == "instagram":
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": ",".join(config["scopes"]),
            "state": state,
        }
        return f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    
    raise ValueError(f"Unsupported provider: {provider}")


# ──────────────────────────────────────────────────────────────
#  TOKEN EXCHANGE
# ──────────────────────────────────────────────────────────────

def exchange_code_for_tokens(provider: str, code: str) -> dict:
    """
    Exchange an authorization code for access/refresh tokens.
    
    Returns:
        { "access_token": str, "refresh_token": str, "expires_in": int, "token_type": str }
    """
    config = get_provider_config(provider)
    
    if provider == "youtube":
        data = {
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
        }
        response = requests.post(config["token_url"], data=data, timeout=30)
    
    elif provider == "tiktok":
        data = {
            "client_key": config["client_key"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config["redirect_uri"],
        }
        response = requests.post(config["token_url"], json=data, timeout=30)
    
    elif provider == "instagram":
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "code": code,
            "grant_type": "authorization_code",
        }
        response = requests.post(config["token_url"], data=data, timeout=30)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    if response.status_code != 200:
        logger.error(f"Token exchange failed for {provider}: {response.text}")
        raise RuntimeError(f"Erro ao trocar código OAuth: {response.text}")
    
    token_data = response.json()
    
    # Normalize response
    return {
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_in": token_data.get("expires_in", 3600),
        "token_type": token_data.get("token_type", "Bearer"),
        "scope": token_data.get("scope", ""),
    }


# ──────────────────────────────────────────────────────────────
#  USER PROFILE FETCH
# ──────────────────────────────────────────────────────────────

def fetch_user_profile(provider: str, access_token: str) -> dict:
    """
    Fetch the user profile from the provider using the access token.
    
    Returns:
        { "provider_user_id": str, "account_name": str, "avatar_url": str }
    """
    config = get_provider_config(provider)
    
    if provider == "youtube":
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(config["profile_url"], headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {
                "provider_user_id": data.get("id", ""),
                "account_name": data.get("name", "YouTube User"),
                "avatar_url": data.get("picture", ""),
            }
    
    elif provider == "tiktok":
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": "open_id,union_id,avatar_url,display_name"}
        response = requests.get(config["profile_url"], headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json().get("data", {}).get("user", {})
            return {
                "provider_user_id": data.get("open_id", ""),
                "account_name": data.get("display_name", "TikTok User"),
                "avatar_url": data.get("avatar_url", ""),
            }
    
    elif provider == "instagram":
        params = {"fields": "id,username,account_type", "access_token": access_token}
        response = requests.get(config["profile_url"], params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {
                "provider_user_id": data.get("id", ""),
                "account_name": f"@{data.get('username', 'instagram_user')}",
                "avatar_url": "",
            }
    
    raise RuntimeError(f"Erro ao buscar perfil do {provider}.")


# ──────────────────────────────────────────────────────────────
#  TOKEN REFRESH
# ──────────────────────────────────────────────────────────────

def refresh_access_token(provider: str, refresh_token: str) -> dict:
    """
    Refresh an expired access token using the refresh token.
    
    Returns:
        { "access_token": str, "expires_in": int }
    """
    config = get_provider_config(provider)
    
    if provider == "youtube":
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        response = requests.post(config["token_url"], data=data, timeout=30)
    
    elif provider == "tiktok":
        data = {
            "client_key": config["client_key"],
            "client_secret": config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        response = requests.post(config["token_url"], json=data, timeout=30)
    
    elif provider == "instagram":
        # Instagram long-lived tokens use a different endpoint
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": config["client_secret"],
            "access_token": refresh_token,
        }
        response = requests.get(
            "https://graph.instagram.com/refresh_access_token",
            params=params,
            timeout=30
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    if response.status_code != 200:
        raise RuntimeError(f"Erro ao renovar token: {response.text}")
    
    data = response.json()
    return {
        "access_token": data.get("access_token", ""),
        "expires_in": data.get("expires_in", 3600),
    }
