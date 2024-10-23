"""ActionNetwork target sink class, which handles writing streams."""

from __future__ import annotations

import backoff
import requests
from singer_sdk.exceptions import RetriableAPIError

from target_hotglue.client import HotglueSink

from target_actionnetwork.auth import ActionNetworkAuthenticator


class ActionNetworkSink(HotglueSink):
    """ActionNetwork target sink class."""

    @backoff.on_exception(
        backoff.expo,
        (RetriableAPIError, requests.exceptions.ReadTimeout),
        max_tries=5,
        factor=2,
    )
    def _request(
        self, http_method: str, endpoint: str, params: dict=None, request_data: dict = None, headers: dict = None
    ) -> requests.PreparedRequest:
        """Prepare a request object."""
        url = self.url(endpoint)
        headers = self.http_headers
        headers.update(self.authenticator.auth_headers)

        response = requests.request(
            method=http_method,
            url=url,
            params=params,
            headers=headers,
            json=request_data,
        )
        self.validate_response(response)
        return response
    
    @property
    def base_url(self) -> str:
        return "https://actionnetwork.org/api/v2/"

    @property
    def authenticator(self):
        return ActionNetworkAuthenticator(self._config.get("token"))
