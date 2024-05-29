from logging import getLogger
from typing import Dict, List, Optional

from pydantic import BaseModel

logger = getLogger(__name__)


class Contact(BaseModel):
    uuid: Optional[str] = None
    name: Optional[str] = None
    number: Optional[str] = None
    profile: Optional[str] = None


class Group(BaseModel):
    name: str
    id: str
    internal_id: str
    members: List[str]
    blocked: bool
    pending_invites: List[str]
    pending_requests: List[str]
    invite_link: str
    admins: List[str]


class PhoneBook(BaseModel):
    # Contacts and groups are keyed by UUID
    contacts: List[Contact] = []
    groups: Dict[str, Group] = {}

    def add_contact(self, contact: Contact):
        for existing_contact in self.contacts:
            if (
                (
                    contact.uuid is not None
                    and existing_contact.uuid == contact.uuid
                )
                or contact.number is not None
                and existing_contact.number == contact.number
            ):
                self.update_contact(
                    uuid=contact.uuid,
                    number=contact.number,
                    name=contact.name,
                    profile=contact.profile,
                )
                return

        self.contacts.append(contact)

    def update_contact(
        self,
        uuid: Optional[str] = None,
        number: Optional[str] = None,
        name: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> bool:
        """Search for any contacts that match the given UUID, or number, and
        update any matches with the name and profile, if given.

        If the UUID or number matches, but the number or UUID is not present,
        add the missing detail to the contact.

        Returns True if the contact information was updated, or if a new
        contact was created. Returns False if an existing contact was found,
        but was not updated.
        """
        for contact in self.contacts:
            if (uuid is not None and contact.uuid == uuid) or (
                number is not None and contact.number == number
            ):
                updated = False

                if name is not None and contact.name != name:
                    contact.name = name
                    updated = True

                if profile is not None and contact.profile != profile:
                    contact.profile = profile
                    updated = True

                if number is not None and contact.number != number:
                    contact.number = number
                    updated = True

                if uuid is not None and contact.uuid != uuid:
                    contact.uuid = uuid
                    updated = True

                return updated

        # If no contact matches by UUID or number, create a new one if name or
        # number is provided
        if name or number:
            new_contact = Contact(
                uuid=uuid, name=name, number=number, profile=profile
            )
            self.add_contact(new_contact)
            return True

        return False

    def get_contact(self, identifier: str) -> Contact:
        """Contacts have at least one of the following identifiers:
            - UUID
            - Phone number
            - Name
        But none are guaranteed. This function will return the first contact
        that matches any of its fields with the given identifier.
        """
        for contact in self.contacts:
            if identifier in [contact.uuid, contact.number]:
                return contact

    def add_group(self, group: Dict[str, str | List[str]]):
        logger.info(f"Creating group from {group}")

        # Gather the list of members from contacts. If a member is not in the
        # phonebook, add them.
        members: List[Contact] = []
        logger.info(f"Group members: {group['members']}")
        for member in group["members"]:
            if member in self.contacts:
                contact = self.get_contact(member)
            else:
                # Group chats identify their members by phone number, AFAIK
                contact = Contact(number=member)
                logger.info(
                    f"Created a new contact with phone number: {member}"
                )
                self.add_contact(contact)

            members.append(contact)

        parsed_group = Group(**group)

        self.groups[parsed_group.internal_id] = parsed_group

    def get_group_internal_id(self, group_id: str) -> str:
        return self.groups[group_id].id
