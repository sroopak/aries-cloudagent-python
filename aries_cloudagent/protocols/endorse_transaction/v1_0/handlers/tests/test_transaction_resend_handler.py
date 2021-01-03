import pytest
from asynctest import mock as async_mock

from ......messaging.request_context import RequestContext
from ......core.profile import Profile
from ......messaging.responder import MockResponder

from ...handlers import transaction_resend_handler as handler
from ...messages.transaction_resend import TransactionResend


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    yield ctx


@pytest.fixture()
async def profile(request_context) -> Profile:
    yield await request_context.profile


class TestTransactionResendHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "TransactionManager")
    async def test_called(self, mock_tran_mgr, request_context):
        mock_tran_mgr.return_value.receive_transaction_resend = (
            async_mock.CoroutineMock()
        )
        request_context.message = TransactionResend()
        handler_inst = handler.TransactionResendHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        mock_tran_mgr.return_value.receive_transaction_resend.assert_called_once_with(
            request_context.message
        )