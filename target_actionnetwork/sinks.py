"""ActionNetwork target sink class, which handles writing streams."""

from target_actionnetwork.client import ActionNetworkSink


class CreateAdvocacyCampaignException(Exception):
    pass


class CreateOutreachException(Exception):
    pass


class ContactsSink(ActionNetworkSink):
    """ActionNetwork target sink class for Contacts"""

    endpoint = "people"
    name = "Contacts"
    advocacy_campaigns = {}

    def __init__(self, target, stream_name, schema, key_properties):
        super().__init__(target, stream_name, schema, key_properties)
        self.get_advocacy_campaigns()

    def get_advocacy_campaigns(self):
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
                self.advocacy_campaigns[adv_camp["title"]] = adv_camp["identifiers"][0].split(':')[1]

    def create_advocacy_campaign(self, name):
        try:
            data = {
                "title": name,
                "origin_system": "hotglue",
                "type": "email"
            }
            response = self._request("POST", "advocacy_campaigns", request_data=data)
            res_json = response.json()
            id = res_json["_links"]["self"]["href"].split("/")[-1]
        except Exception as exc:
            raise CreateAdvocacyCampaignException(f"Error during creation of advocacy campaign {name}") from exc
        self.advocacy_campaigns[name] = id
        self.logger.info(f"advocacy_campaign_id created with id: {id}.")
        return id

    def create_outreach(self, advocacy_campaign_id, email_addresses, phone_numbers):
        try:
            data = {"person": {}}
            if email_addresses:
                data["person"]["email_addresses"] = [{"address": addr["address"]}for addr in email_addresses]
            if phone_numbers:
                data["person"]["phone_numbers"] = [{"number": addr["phone_number"]}for addr in phone_numbers]
            url = f"advocacy_campaigns/{advocacy_campaign_id}/outreaches/"
            response = self._request("POST", url, request_data=data)
            res_json = response.json()
            id = res_json["_links"]["self"]["href"].split("/")[-1]
        except Exception as exc:
            raise CreateOutreachException(f"Error during creation of outreach advocacy_campaign_id={advocacy_campaign_id} and person={data['person']}") from exc
        self.logger.info(f"Outreach created with id: {id}. advocacy_campaign_id={advocacy_campaign_id} and person={data['person']}")
        return id
    
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
                address_lines = []
                line1 = address.get("line1")
                if line1:
                    address_lines.append(line1)
                line2 = address.get("line2")
                if line2:
                    address_lines.append(line2)
                line3 = address.get("line3")
                if line3:
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
        subscribe_status = record.get("subscribe_status")
        if subscribe_status and subscribe_status in ['subscribed', 'unsubscribed', 'bouncing', 'previou bounce', 'spa complaint', 'previou spam complaint']:
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
                    "phone_number": phone_number.get("number"),
                    "type": phone_number.get("type")
                }
                for phone_number in phone_numbers
            ]

        custom_fields = record.get("custom_fields")
        if custom_fields:
            person["custom_fields"] = [
                {field.get("name"): field.get("value")}
                for field in custom_fields
                if field.get("name")
            ]
        
        tags = record.get("tags")
        if tags:
            person["add_tags"] = [
                tag for tag in tags
            ]

        payload = {"person": person}
        if "lists" in record:
            payload["lists"] = record["lists"]
        return payload
    
    def upsert_record(self, record: dict, context: dict):
        state_updates = dict()
        if record:
            if record.get("error"):
                raise Exception(record.get("error"))

            lists = record.pop("lists",None)

            response = self.request_api(
                "POST", endpoint=self.endpoint, request_data=record
            )
            res_json = response.json()

            if lists:
                email_addresses = record["person"]["email_addresses"]
                phone_numbers = record["person"]["phone_numbers"]
                if not email_addresses and not phone_numbers:
                    raise Exception("Email or Phone Number is required to create outreaches")
                elif lists:
                    for l in lists:
                        if l in self.advocacy_campaigns:
                            self.create_outreach(self.advocacy_campaigns[l], email_addresses, phone_numbers)
                        else:
                            adv_camp_id = self.create_advocacy_campaign(l)
                            self.create_outreach(adv_camp_id, email_addresses, phone_numbers)

            id = res_json["_links"]["self"]["href"].split("/")[-1]
            self.logger.info(f"{self.name} created with id: {id}")
            return id, True, state_updates
        