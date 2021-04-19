"""Connection response handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from .....protocols.problem_report.v1_0.message import ProblemReport
from .....protocols.trustping.v1_0.messages.ping import Ping

from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.connection_response import ConnectionResponse


class ConnectionResponseHandler(BaseHandler):
    """Handler class for connection responses."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection response.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"ConnectionResponseHandler called with context {context}")
        assert isinstance(context.message, ConnectionResponse)

        session = await context.session()
        mgr = ConnectionManager(session)
        try:
            connection = await mgr.accept_response(
                context.message, context.message_receipt
            )
        except ConnectionManagerError as e:
            self._logger.exception("Error receiving connection response")
            if e.error_code:
                targets = None
                if context.message.connection and context.message.connection.did_doc:
                    try:
                        targets = mgr.diddoc_connection_targets(
                            context.message.connection.did_doc,
                            context.message_receipt.recipient_verkey,
                        )
                    except ConnectionManagerError:
                        self._logger.exception(
                            "Error parsing DIDDoc for problem report"
                        )
                await responder.send_reply(
                    ProblemReport(
                        explain_ltxt=e.message,
                        problem_items=[{e.error_code: e.message}],
                    ),
                    target_list=targets,
                )
            return

        # send trust ping in response
        if context.settings.get("auto_ping_connection"):
            await responder.send(Ping(), connection_id=connection.connection_id)
