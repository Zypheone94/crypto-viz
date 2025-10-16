from http.client import responses
from typing import Literal, Optional, Any, TypedDict
from datetime import datetime, timezone

Services = Literal["api" , "scraper", "builder"]
Levels = Literal["debug", "info", "warning", "error", "critical"]

class LogEntry(TypedDict):
    """Structure du log retourné"""
    service: str
    ts: str
    level: str
    msg: str
    response : Any
    extra: Optional[dict[str, Any]]

class JsonApiTemplate:
    def __init__(self, service: Services):
        """
        Initialise le logger pour un service spécifique.

        Args:
            service: Le nom du service ("api", "scraper", ou "builder")
        """
        self.service = service

    def _create_response(
            self,
            level: Levels,
            msg: str,
            response: Any,
            extra: Optional[dict[str, Any]] = None,
    ) -> LogEntry:
        """Crée une entrée de log structurée"""
        return {
            "service": self.service,
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "msg": msg,
            "response": response,
            "extra": extra
        }

"""
Example of use : 

apiRes = JsonApiTemplate("api") -> You precise the service you use (the list is in Services)

myResponse = apiRes._create_response(
    level="debug", -> again the list is in Levels
    msg="my message", -> is a string if you need to add something (an error message for example)
    response={...} -> is a any type and will contain your api return
    extra={} -> is an additional an optional field if you need to add something
)

"""