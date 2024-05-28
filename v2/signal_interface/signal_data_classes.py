from typing import List, Optional

from pydantic import BaseModel, Field


class SignalCredentials(BaseModel):
    # URL of the signal API server
    signal_service: str
    # My phone number
    phone_number: str
    # This is the administrator's phone number. They have special privileges,
    # and receive status updates when appropriate.
    admin_number: str


class ReceiptMessage(BaseModel):
    when: int
    isDelivery: bool
    isRead: bool
    isViewed: bool
    timestamps: List[int]


class TypingMessage(BaseModel):
    action: str
    timestamp: int


class Reaction(BaseModel):
    emoji: str
    targetAuthor: str
    targetAuthorNumber: str
    targetAuthorUuid: str
    targetSentTimestamp: int
    isRemove: bool


class Mention(BaseModel):
    name: str
    number: str
    uuid: str
    start: int
    length: int


class GroupInfo(BaseModel):
    groupId: str
    type: str


class Attachment(BaseModel):
    contentType: str
    filename: str
    id: str
    size: int
    width: int
    height: int
    caption: Optional[str] = None
    uploadTimestamp: Optional[int] = None
    # The data is fetched, and the incoming bytes are converted to a base64
    # encoded string.
    data: Optional[str] = None


class DataMessage(BaseModel):
    timestamp: int
    message: Optional[str] = None
    expiresInSeconds: int
    viewOnce: bool
    attachments: Optional[List[Attachment]] = None
    reaction: Optional[Reaction] = None
    mentions: Optional[List[Mention]] = None
    groupInfo: Optional[GroupInfo] = None


class Envelope(BaseModel):
    source: str
    sourceNumber: str
    sourceUuid: str
    sourceName: str
    sourceDevice: int
    timestamp: int
    receiptMessage: Optional[ReceiptMessage] = None
    typingMessage: Optional[TypingMessage] = None
    dataMessage: Optional[DataMessage] = None


class IncomingMessage(BaseModel):
    envelope: Envelope
    account: str


class OutgoingMessage(BaseModel):
    recipient: str
    message: str
    base64_attachments: List[str] = Field(default_factory=list)


class OutgoingReaction(BaseModel):
    recipient: str
    reaction: str
    target_uuid: str
    timestamp: int
