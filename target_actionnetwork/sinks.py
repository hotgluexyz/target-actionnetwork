"""ActionNetwork target sink class, which handles writing streams."""

from target_actionnetwork.client import ActionNetworkSink
from hotglue_etl_exceptions import InvalidPayloadError


class CreateAdvocacyCampaignException(InvalidPayloadError):
    pass


class CreateOutreachException(InvalidPayloadError):
    pass


class ContactsSink(ActionNetworkSink):
    """ActionNetwork target sink class for Contacts"""

    endpoint = "people"
    name = "Contacts"
    advocacy_campaigns = {}

    def get_advocacy_campaigns(self):
        if self.advocacy_campaigns:
            return
        response = self._request("GET", "advocacy_campaigns")
        res_json = response.json()
        total_pages = res_json.get("total_pages")
        for current_page in range(1, total_pages+1):
            response = self._request("GET", "advocacy_campaigns", {"page": current_page})
            res_json = response.json()
            advocacy_campaigns = res_json["_embedded"]["osdi:advocacy_campaigns"]
            for adv_camp in advocacy_campaigns:
                if adv_camp["title"] in self.advocacy_campaigns:
                    self.logger.warning(f"The campaign (title={adv_camp['title']}, id={adv_camp['identifiers']}) already exists, and it is mapped to id={self.advocacy_campaigns[adv_camp['title']]}")
                self.advocacy_campaigns[adv_camp["title"]] = {"id": adv_camp["identifiers"][0].split(':')[1], "origin_system": adv_camp.get("origin_system")}

    @property
    def default_origin_system(self):
        return self.config.get("campaign_origin_system", "Hotglue")

    def create_advocacy_campaign(self, name):
        origin_system = self.default_origin_system
        try:
            data = {
                "title": name,
                "origin_system": origin_system,
                "type": "email"
            }
            response = self._request("POST", "advocacy_campaigns", request_data=data)
            res_json = response.json()
            id = res_json["_links"]["self"]["href"].split("/")[-1]
        except Exception as exc:
            raise CreateAdvocacyCampaignException(f"Error during creation of advocacy campaign {name}") from exc
        self.advocacy_campaigns[name] = {
            "title": name,
            "id": id,
            "origin_system": origin_system,
        }
        self.logger.info(f"advocacy_campaign_id created with id: {id}.")
        return id

    def create_outreach(self, advocacy_campaign_id, email_addresses, phone_numbers):
        try:
            data = {"person": {}}
            if email_addresses:
                data["person"]["email_addresses"] = [{"address": addr["address"]}for addr in email_addresses]
            if phone_numbers:
                data["person"]["phone_numbers"] = [{"number": addr["number"]}for addr in phone_numbers]
            url = f"advocacy_campaigns/{advocacy_campaign_id}/outreaches/"
            response = self._request("POST", url, request_data=data)
            res_json = response.json()
            id = res_json["_links"]["self"]["href"].split("/")[-1]
        except Exception as exc:
            raise CreateOutreachException(f"Error during creation of outreach advocacy_campaign_id={advocacy_campaign_id} and person={data['person']}") from exc
        self.logger.info(f"Outreach created with id: {id}. advocacy_campaign_id={advocacy_campaign_id} and person={data['person']}")
        return id

    def _format_address_object(self, raw_address: dict) -> dict:
        address_lines = []
        line1 = raw_address.get("line1")
        if line1:
            address_lines.append(line1)
        line2 = raw_address.get("line2")
        if line2:
            address_lines.append(line2)
        line3 = raw_address.get("line3")
        if line3:
            address_lines.append(line3)
        
        return {
            "address_lines": address_lines,
            "locality": raw_address.get("city"),
            "postal_code": raw_address.get("postal_code"),
            "country": raw_address.get("country"),
            "region": raw_address.get("state"),
        }
    
    def preprocess_record(self, record: dict, context: dict) -> dict:
        person = {
            "family_name" : record.get("last_name"),
            "given_name" : record.get("first_name"),
            "postal_addresses": [],
            "email_addresses": [],
            "phone_numbers": [],
        }
        addresses = record.get("addresses")
        if addresses:
            for address in addresses:
                person["postal_addresses"].append(self._format_address_object(address))

        #One of ['subscribed', 'unsubscribed', 'bouncing', 'previou' bounce’, 'spa' complaint’, or 'previou' spam complaint’]
        status = None
        subscribe_status = record.get("subscribe_status")
        if subscribe_status in ['subscribed', 'unsubscribed']:
            status = subscribe_status
        elif record.get("unsubscribed"):
            status = "unsubscribed"

        email = record.get("email")
        if email:
            email_dict = {
                "address" : email,
                "primary": True,
            }
            if status:
                email_dict["status"] = status
            person["email_addresses"].append(email_dict)

        emails = record.get("additional_emails")
        if emails:
            person["email_addresses"] = [
                {"address": email, "primary": False}
                for email in emails
            ]

        phone_numbers = record.get("phone_numbers")
        if phone_numbers:
            person["phone_numbers"] = [
                {
                    "number": phone_number.get("number"),
                    "type": phone_number.get("type")
                }
                for phone_number in phone_numbers
            ]

        custom_fields = record.get("custom_fields")
        if custom_fields:
            person["custom_fields"] = {
                field.get("name"): field.get("value")
                for field in custom_fields
                if field.get("name")
            }
        
        payload = {"person": person}

        tags = record.get("tags")
        if tags:
            tags_list = [
                tag for tag in tags
            ]
            payload["add_tags"] = tags_list

        lists = record.get("lists")
        if lists:
            payload["lists"] = lists
        return payload

    def _handle_outreach_upserts(self, list_name: str, email_addresses: list, phone_numbers: list):
        if list_name in self.advocacy_campaigns:
            self.create_outreach(self.advocacy_campaigns[list_name]["id"], email_addresses, phone_numbers)
        else:
            adv_camp_id = self.create_advocacy_campaign(list_name)
            self.create_outreach(adv_camp_id, email_addresses, phone_numbers)

    
    def upsert_record(self, record: dict, context: dict):
        state_updates = {}
        if not record:
            return None, True, state_updates
        
        error = record.get("error")
        if error:
            raise Exception(error)

        lists = record.pop("lists", None)

        response = self.request_api("POST", endpoint=self.endpoint, request_data=record)
        
        if not response.ok:
            raise Exception(response.text)

        res_json = response.json()
        record_id = res_json["_links"]["self"]["href"].split("/")[-1]

        if lists:
            self.get_advocacy_campaigns()
            email_addresses = record["person"].get("email_addresses", [])
            phone_numbers = record["person"].get("phone_numbers", [])
            if not email_addresses and not phone_numbers:
                raise InvalidPayloadError("Email or Phone Number is required to create outreaches. "
                                "Error during creation of {} record with id: {}".format(self.name, record_id))
            for list_name in lists:
                self._handle_outreach_upserts(list_name, email_addresses, phone_numbers)

        self.logger.info("{} created with id: {}".format(self.name, record_id))

        return record_id, True, state_updates
