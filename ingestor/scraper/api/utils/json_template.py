from datetime import datetime
from typing import Dict, Any
import json


class JsonTemplate:

    def __init__(self):
        pass

    def create_json(self,
                    message: str,
                    service: str,
                    status: int,) -> Dict[str, Any]:

        """

        Args:
            message: Json message (error, or success for example)

            status: Error code or success for status (ex: 200, 404, etc...)
            service: Service that execute the call

        Returns:
            Dict with a quick recap of the executed API call


        timeStamp: When the request has been executed (and is set automatically)
        """

        json_entry = {
            "service": service,
            "message": message,
            "timeStamp": datetime.now().isoformat() + "Z",
            "status": status,
        }

        return json_entry