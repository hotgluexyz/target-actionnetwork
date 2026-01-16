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
        max_tries=8,
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
            # Response includes the API key, which should NOT be exposed. DO NOT REMOVE.
            if "API Key" in msg:
                raise InvalidCredentialsError("API Key invalid or not present.")
            raise InvalidCredentialsError(msg)

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


    def find_matching_object(self, lookup_field: str, lookup_value: str):
        """Find a matching object by any lookup field.
        
        Args:
            lookup_field: The field to search on (e.g., 'email', 'id', etc.)
            lookup_value: The value to search for
            
        Returns:
            The full matching object if found, None otherwise
        """
        if not lookup_value:
            return None
            
        try:
            if lookup_field == "id":
                endpoint = f"{self.endpoint}/{lookup_value}"
            else: 
                filter_value = f"{lookup_field} eq '{lookup_value}'"
                endpoint = self.endpoint
                params = {
                    "filter": filter_value,
                }
            
            resp = self.request_api(
                "GET",
                endpoint=endpoint,
                params=params
            )
            
            if resp.status_code in [200, 201]:
                result = resp.json()
                if lookup_field == "id":
                    return result
                else:
                    # For filtered queries, check if we have results in the embedded collection
                    embedded_key = f"osdi:{self.endpoint}"
                    if result.get("_embedded") and result["_embedded"].get(embedded_key):
                        objects = result["_embedded"][embedded_key]
                        if objects:
                            # Return the first match
                            return objects[0]
            return None
        except Exception:
            return None

