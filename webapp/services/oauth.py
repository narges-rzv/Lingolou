"""
OAuth provider configuration using Authlib.
"""

import os
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

# Google — OpenID Connect with auto-discovery
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Facebook — manual endpoint URLs (Graph API v19.0)
oauth.register(
    name="facebook",
    client_id=os.getenv("FACEBOOK_CLIENT_ID", ""),
    client_secret=os.getenv("FACEBOOK_CLIENT_SECRET", ""),
    authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
    access_token_url="https://graph.facebook.com/v19.0/oauth/access_token",
    api_base_url="https://graph.facebook.com/v19.0/",
    client_kwargs={"scope": "email public_profile"},
)
