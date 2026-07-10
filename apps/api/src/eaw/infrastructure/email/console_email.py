"""Development email backend — logs messages."""

import logging

from eaw.application.ports.email import EmailPort

logger = logging.getLogger(__name__)


class ConsoleEmailAdapter(EmailPort):
    def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info(
            "EMAIL to=%s subject=%s\n%s",
            to,
            subject,
            body,
        )
