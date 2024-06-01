from .create_image import CreateImageCommandHandler
from .ping import PingCommandHandler
from .react import ReactCommandHandler
from .reply import ReplyCommandHandler
from .see_image import SeeImageCommandHandler
from .summon import SummonCommandHandler
from .see_quoted_image import SeeQuotedImageCommandHandler

COMMAND_REGISTRY = {
    "ping": PingCommandHandler,
    "react": ReactCommandHandler,
    "summon": SummonCommandHandler,
    "see_image": SeeImageCommandHandler,
    "see_quoted_image": SeeQuotedImageCommandHandler,
    "create_image": CreateImageCommandHandler,
    "reply": ReplyCommandHandler,
}
