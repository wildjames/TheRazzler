from .ping import PingCommandHandler
from .react import ReactCommandHandler
from .see_image import SeeImageCommandHandler
from .summon import SummonCommandHandler

COMMAND_REGISTRY = {
    "ping": PingCommandHandler,
    "react": ReactCommandHandler,
    "summon": SummonCommandHandler,
    "see_image": SeeImageCommandHandler,
}
