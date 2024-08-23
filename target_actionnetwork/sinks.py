"""ActionNetwork target sink class, which handles writing streams."""
from __future__ import annotations

from target_actionnetwork.client import ActionNetworkSink


class ContactsSink(ActionNetworkSink):
    """ActionNetwork target sink class for Contacts"""

    endpoint = "people"
    name = "Contacts"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        person = {
            "family_name" : record.get("last_name"),
            "given_name" : record.get("first_name"),
            "postal_addresses": [],
            "email_addresses": [],
            "phone_numbers": [],
        }
        if addresses := record.get("addresses"):
            for address in addresses:
                address_lines = []
                if line1 := address.get("line1"):
                    address_lines.append(line1)
                if line2 := address.get("line2"):
                    address_lines.append(line2)
                if line3 := address.get("line3"):
                    address_lines.append(line3)

                person["postal_addresses"].append({
                    "address_lines": address_lines,
                    "locality": address.get("city"),
                    "postal_code": address.get("postal_code"),
                    "country": address.get("country"),
                    "region": address.get("state"),
                })

        #One of ['subscribed', 'unsubscribed', 'bouncing', 'previou' bounce’, 'spa' complaint’, or 'previou' spam complaint’]
        status = None
        if (subscribe_status := record.get("subscribe_status")) in ['subscribed', 'unsubscribed', 'bouncing', 'previou bounce', 'spa complaint', 'previou spam complaint']:
            status = subscribe_status
        elif record.get("unsubscribed"):
            status = "unsubscribed"

        if email := record.get("email"):
            email_dict = {
                "address" : email,
                "primary": True,
            }
            if status:
                email_dict["status"] = status
            person["email_addresses"].append(email_dict)

        if emails := record.get("additional_emails"):
            person["email_addresses"] = [
                {"address": email, "primary": False}
                for email in emails
            ]
        if email := record.get("email"):
            email_dict = {
                "address" : email,
                "primary": True,
            }
            if status:
                email_dict["status"] = status
            person["email_addresses"].append(email_dict)

        if phone_numbers := record.get("phone_numbers"):
            person["phone_numbers"] = [
                {
                    "phone_number": phone_number.get("number"),
                    "type": phone_number.get("type")
                }
                for phone_number in phone_numbers
            ]

        if custom_fields := record.get("custom_fields"):
            person["custom_fields"] = [
                {field.get("name"): field.get("value")}
                for field in custom_fields
                if field.get("name")
            ]
        
        if tags := record.get("tags"):
            person["add_tags"] = [
                tag for tag in tags
            ]
        
        payload = {"person": person}
        return payload
    
    def upsert_record(self, record: dict, context: dict):
        state_updates = dict()
        if record:
            response = self.request_api(
                "POST", endpoint=self.endpoint, request_data=record
            )
            res_json = response.json()
            id = res_json["_links"]["self"]["href"].split("/")[-1]
            self.logger.info(f"{self.name} created with id: {id}")
            return id, True, state_updates
        