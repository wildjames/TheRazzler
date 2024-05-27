from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReceiptMessage:
    when: int
    isDelivery: bool
    isRead: bool
    isViewed: bool
    timestamps: List[int]


@dataclass
class TypingMessage:
    action: str
    timestamp: int


@dataclass
class Reaction:
    emoji: str
    targetAuthor: str
    targetAuthorNumber: str
    targetAuthorUuid: str
    targetSentTimestamp: int
    isRemove: bool


@dataclass
class Mention:
    name: str
    number: str
    uuid: str
    start: int
    length: int


@dataclass
class GroupInfo:
    groupId: str
    type: str


@dataclass
class Attachment:
    contentType: str
    fileName: str
    id: str
    size: int
    width: int
    height: int
    caption: Optional[str] = None
    uploadTimestamp: Optional[int] = None


@dataclass
class DataMessage:
    timestamp: int
    message: Optional[str]
    expiresInSeconds: int
    viewOnce: bool
    attachments: Optional[List[Attachment]] = None
    reaction: Optional[Reaction] = None
    mentions: Optional[List[Mention]] = None
    groupInfo: Optional[GroupInfo] = None


@dataclass
class Envelope:
    source: str
    sourceNumber: str
    sourceUuid: str
    sourceName: str
    sourceDevice: int
    timestamp: int
    receiptMessage: Optional[ReceiptMessage] = None
    typingMessage: Optional[TypingMessage] = None
    dataMessage: Optional[DataMessage] = None


@dataclass
class MessagePayload:
    envelope: Envelope
    account: str


@dataclass
class IncomingMessage:
    label: str
    payload: MessagePayload


@dataclass
class OutgoingMessage:
    recipient: str
    message: str
    base64_attachments: List[str] = field(default_factory=list)
