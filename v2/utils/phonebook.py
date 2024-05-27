from typing import Dict

from pydantic import BaseModel


class Contact(BaseModel):
    name: str
    uuid: str
    number: str = ""
    profile: str = ""


class Group(BaseModel):
    group_id: str
    type: str
    name: str = ""
    members: Dict[str, Contact] = {}


class PhoneBook(BaseModel):
    # Contacts and groups are keyed by UUID
    contacts: Dict[str, Contact] = {}
    groups: Dict[str, Group] = {}
