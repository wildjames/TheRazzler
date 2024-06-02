from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from utils.storage import load_phonebook

MENTION_CHAR = "￼"


class SignalCredentials(BaseModel):
    # URL of the signal API server
    signal_service: str
    # My phone number
    phone_number: str
    # This is the administrator's phone number. They have special privileges,
    # and receive status updates when appropriate.
    admin_number: str
    # How many messages in the message history to preserve in the cache
    message_history_length: int = 100


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
    # Corresponds to the timestamp of the message that the reaction is to
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
    # The internal ID used for retrieving the attachment from the Signal API
    id: str
    # MIME type of the attachment
    # e.g. "image/jpeg", "video/mp4", "audio/aac", ...
    contentType: str
    filename: Optional[str]
    size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None
    uploadTimestamp: Optional[int] = None
    # The data is fetched, and the incoming bytes are converted to a base64
    # encoded string.
    data: Optional[str] = None


class QuoteAttachment(BaseModel):
    contentType: str
    filename: str
    thumbnail: Attachment
    # This is the data extracted from the attachment thumbnail
    data: Optional[str] = None


class QuoteMessage(BaseModel):
    id: int
    author: str
    authorNumber: str
    authorUuid: str
    text: str
    attachments: List[QuoteAttachment] = Field(default_factory=list)


class DataMessage(BaseModel):
    timestamp: int
    message: Optional[str] = None
    expiresInSeconds: int
    viewOnce: bool
    attachments: Optional[List[Attachment]] = None
    reaction: Optional[Reaction] = None
    mentions: Optional[List[Mention]] = None
    quote: Optional[QuoteMessage] = None
    groupInfo: Optional[GroupInfo] = None


class Envelope(BaseModel):
    source: str
    sourceNumber: str
    sourceUuid: str
    sourceName: str
    sourceDevice: int
    # UNIX timestamp, in milliseconds
    timestamp: int
    receiptMessage: Optional[ReceiptMessage] = None
    typingMessage: Optional[TypingMessage] = None
    dataMessage: Optional[DataMessage] = None


class IncomingMessage(BaseModel):
    envelope: Envelope
    account: str

    def get_recipient(self) -> str:
        """Get the ID needed to target a return message. For phone numbers,
        this is the phone number. For groups, this is the internal ID of the
        group. *NOT* the ID attached to the message!
        """
        if self.envelope.dataMessage:
            if self.envelope.dataMessage.groupInfo:
                gid = self.envelope.dataMessage.groupInfo.groupId
                phonebook = load_phonebook()
                return phonebook.get_group_internal_id(gid)

        return self.envelope.source


class OutgoingMessage(BaseModel):
    recipient: str
    message: str
    base64_attachments: List[str] = Field(default_factory=list, repr=False)
    edit_timestamp: Optional[int] = None
    mentions: Optional[str] = None
    quote_author: Optional[str] = None
    quote_mentions: Optional[str] = None
    quote_message: Optional[str] = None
    quote_timestamp: Optional[int] = None
    sticker: Optional[str] = None
    text_mode: Optional[Literal["normal", "styled"]] = "normal"


class OutgoingReaction(BaseModel):
    recipient: str
    reaction: str
    target_uuid: str
    timestamp: int


class OutgoingReceipt(BaseModel):
    receipt_type: Literal["read", "viewed"]
    recipient: str
    # Timestamp of the message that the receipt is for
    timestamp: int
