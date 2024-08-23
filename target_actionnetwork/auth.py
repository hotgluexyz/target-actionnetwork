class ActionNetworkAuthenticator:
    """API Authenticator for OAuth 2.0 flows."""

    def __init__(self, token) -> None:
        self._token = token
    
    @property
    def auth_headers(self) -> dict:
        result = {
            "OSDI-API-Token": self._token
        }
        return result