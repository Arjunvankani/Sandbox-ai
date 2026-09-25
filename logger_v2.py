import json
import logging
import os
import sys
import time
from datetime import datetime, timezone


os.makedirs("logs", exist_ok=True)


class AgentLogger:

    def __init__(self, task_id):

        self.task_id = task_id

        self.log_file = f"logs/{task_id}.log"
        self.json_file = f"logs/{task_id}.jsonl"

        self.logger = logging.getLogger(task_id)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)

        file_handler = logging.FileHandler(
            self.log_file,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console)
        self.logger.addHandler(file_handler)

    def event(self, event, **data):

        record = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "task_id": self.task_id,

            "event": event,

            **data
        }

        with open(
            self.json_file,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                json.dumps(
                    record,
                    default=str
                )
                + "\n"
            )

        message = event

        if data:

            parts = []

            for key, value in data.items():

                if value is not None:

                    parts.append(
                        f"{key}={value}"
                    )

            if parts:

                message += " | " + " | ".join(parts)

        self.logger.info(message)

    def timer(self):

        return time.perf_counter()