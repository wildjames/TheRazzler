from typing import Callable, Dict, List
from .create_image import CreateImageCommandHandler
from .ping import PingCommandHandler
from .react import ReactCommandHandler
from .reply import ReplyCommandHandler
from .see_image import SeeImageCommandHandler
from .summon import SummonCommandHandler

COMMAND_REGISTRY: Dict[str, Callable] = {
    "ping": PingCommandHandler,
    "react": ReactCommandHandler,
    "summon": SummonCommandHandler,
    "see_image": SeeImageCommandHandler,
    "create_image": CreateImageCommandHandler,
    "reply": ReplyCommandHandler,
}

COMMAND_PROCESSING_ORDER: List[str] = [
    "ping",
    "react",
    "summon",
    "see_image",
    "create_image",
    "reply",
]
