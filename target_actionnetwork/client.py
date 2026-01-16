"""ActionNetwork target sink class, which handles writing streams."""

from __future__ import annotations

import backoff
import requests

from hotglue_singer_sdk.plugin_base import PluginBase
from hotglue_singer_sdk.target_sdk.client import HotglueSink
from hotglue_etl_exceptions import InvalidCredentialsError, InvalidPayloadError
from hotglue_singer_sdk.exceptions import FatalAPIError, RetriableAPIError
import json

from target_actionnetwork.auth import ActionNetworkAuthenticator

class RetriableInvalidPayloadError(InvalidPayloadError, RetriableAPIError):
    pass

class ActionNetworkSink(HotglueSink):
    """ActionNetwork target sink class."""

    @backoff.on_exception(
        backoff.expo,   
        (RetriableAPIError, requests.exceptions.ReadTimeout),
        max_tries=7,
        factor=2,
    )
    def _request(
        self, http_method: str, endpoint: str, params: dict=None, request_data: dict = None, headers: dict = None, verify = True
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


    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response."""
        msg = response.text

        # 403 was observed, going to put 401 here so we don't accidentally expose the key
        if response.status_code == 403 or response.status_code == 401:
            # Response includes the API key, which should NOT be exposed
            if "API Key" in msg:
                raise InvalidCredentialsError("API Key invalid or not present.")
            raise InvalidCredentialsError(msg)

        # Case where "at least an email address or phone number is required", for advocacy campaigns: origin_system and title are required fields
        if response.status_code == 400:
            raise InvalidPayloadError(msg)

        # Either bad request or internal server error, unknown which
        if response.status_code == 500:
            raise RetriableInvalidPayloadError(msg)

        super().validate_response(response)
    
    @property
    def base_url(self) -> str:
        return "https://actionnetwork.org/api/v2/"

    @property
    def authenticator(self):
        return ActionNetworkAuthenticator(self._config.get("token"))
