from .ping import PingCommandHandler
from .react import ReactCommandHandler
from .summon import SummonCommandHandler

COMMAND_REGISTRY = {
    "ping": PingCommandHandler,
    "react": ReactCommandHandler,
    "summon": SummonCommandHandler,
}
