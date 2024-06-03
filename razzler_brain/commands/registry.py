from typing import Callable, Dict, List
from .create_image import CreateImageCommandHandler
from .ping import PingCommandHandler
from .react import ReactCommandHandler
from .reply import ReplyCommandHandler
from .reply_when_busy import ReplyWhenActiveChatCommandHandler
from .reply_razzle_target import ReplyRazzleTargetCommandHandler
from .see_image import SeeImageCommandHandler
from .summon import SummonCommandHandler

COMMAND_REGISTRY: Dict[str, Callable] = {
    "ping": PingCommandHandler,
    "react": ReactCommandHandler,
    "summon": SummonCommandHandler,
    "see_image": SeeImageCommandHandler,
    "create_image": CreateImageCommandHandler,
    "reply": ReplyCommandHandler,
    "reply_when_active_chat": ReplyWhenActiveChatCommandHandler,
    "reply_razzle_target": ReplyRazzleTargetCommandHandler,
}

COMMAND_PROCESSING_ORDER: List[str] = [
    "ping",
    "react",
    "summon",
    "see_image",
    "create_image",
    "reply_razzle_target",
    "reply",
    "reply_when_active_chat",
]
