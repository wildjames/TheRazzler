from .ping import PingCommandHandler
from .react import ReactCommandHandler


COMMAND_REGISTRY = {
    "ping": PingCommandHandler,
    "react": ReactCommandHandler,
}
