"""
OAuth provider configuration using Authlib.
"""

from __future__ import annotations

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
