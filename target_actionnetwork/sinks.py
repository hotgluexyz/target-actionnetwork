"""ActionNetwork target sink class, which handles writing streams."""

import requests
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

    def create_advocacy_campaign(self, name):
        try:
            data = {
                "title": name,
                "origin_system": self.config.get("campaign_origin_system", "Hotglue"),
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

    def update_advocacy_campaign(self, campaign_id, origin_system):
        data = {
            "origin_system": origin_system
        }
        response = self._request("PUT", f"advocacy_campaigns/{campaign_id}", request_data=data)
        res_json = response.json()
        self.logger.info(f"advocacy_campaign_id {campaign_id} updated with origin_system: {origin_system}")
        return res_json

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
    
    def _merge_missing_simple_fields(self, target_person: dict, source_person: dict, field_names: list[str]) -> dict:
        """Merge simple field values from source to target, only if target field is empty."""
        for field_name in field_names:
            if not target_person.get(field_name) and source_person.get(field_name):
                target_person[field_name] = source_person[field_name]
        return target_person
    

    def _merge_person_data(self, existing_person: dict, new_person: dict) -> dict:
        """
        Merge nested person data from Action Network API.
        Only updates fields that are empty/missing in the existing person.
        """
        merged = existing_person.copy()
        
        merged = self._merge_missing_simple_fields(merged, new_person, ['given_name', 'family_name'])

        if new_person.get('email_addresses'):
            existing_emails = {email.get('address'): email for email in merged.get('email_addresses', [])}
            for new_email in new_person['email_addresses']:
                email_addr = new_email.get('address')
                if email_addr and email_addr not in existing_emails:
                    existing_emails[email_addr] = new_email
                elif email_addr in existing_emails:
                    existing_email = existing_emails[email_addr]
                    existing_emails[email_addr] = self._merge_missing_simple_fields(existing_email, new_email, ['status', 'primary'])
            merged['email_addresses'] = list(existing_emails.values())
        
        if new_person.get('phone_numbers'):
            existing_phones = {phone.get('number'): phone for phone in merged.get('phone_numbers', [])}
            for new_phone in new_person['phone_numbers']:
                phone_number = new_phone.get('number')
                if phone_number and phone_number not in existing_phones:
                    if 'phone_numbers' not in merged:
                        merged['phone_numbers'] = []
                    merged['phone_numbers'].append(new_phone)
                elif phone_number in existing_phones:
                    existing_phone = existing_phones[phone_number]
                    existing_phones[phone_number] = self._merge_missing_simple_fields(existing_phone, new_phone, ['status', 'primary', 'number_type'])
            merged['phone_numbers'] = list(existing_phones.values())
            
        if new_person.get('postal_addresses'):
            if not merged.get('postal_addresses'):
                merged['postal_addresses'] = new_person['postal_addresses']

        if new_person.get('custom_fields'):
            if not merged.get('custom_fields'):
                merged['custom_fields'] = {}
            if isinstance(new_person['custom_fields'], dict):
                for field_key, field_value in new_person['custom_fields'].items():
                    if field_key not in merged['custom_fields']:
                        merged['custom_fields'][field_key] = field_value
                    
        return merged
    
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
                    "phone_number": phone_number.get("number"),
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

        only_upsert_empty_fields = self.config.get("only_upsert_empty_fields", False)
        
        if only_upsert_empty_fields:
            matching_person = self.find_matching_object("email_address", record.get("email"))
            if matching_person:
                person = self._merge_person_data(matching_person, person)

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
            state_updates["error"] = response.text
            return None, False, state_updates
        
        if record.get('person', {}).get('created_date'):
            state_updates["is_updated"] = True

        res_json = response.json()
        record_id = res_json["_links"]["self"]["href"].split("/")[-1]

        if lists:
            self.get_advocacy_campaigns()
            email_addresses = record["person"].get("email_addresses", [])
            phone_numbers = record["person"].get("phone_numbers", [])
            if not email_addresses and not phone_numbers:
                raise Exception("Email or Phone Number is required to create outreaches. "
                                "Error during creation of {} record with id: {}".format(self.name, record_id))
            for list_name in lists:
                if list_name in self.advocacy_campaigns:
                    # Backfill origin system if set
                    if self.config.get("campaign_origin_system") and self.advocacy_campaigns[list_name].get("origin_system") == "hotglue":
                        self.update_advocacy_campaign(self.advocacy_campaigns[list_name]["id"], self.config.get("campaign_origin_system"))

                    self.create_outreach(self.advocacy_campaigns[list_name]["id"], email_addresses, phone_numbers)
                else:
                    adv_camp_id = self.create_advocacy_campaign(list_name)
                    self.create_outreach(adv_camp_id, email_addresses, phone_numbers)

        self.logger.info("{} created with id: {}".format(self.name, record_id))

        return record_id, True, state_updates
