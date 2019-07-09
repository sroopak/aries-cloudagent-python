import asyncio
import json
import logging
import os
import random
import sys

from .agent import DemoAgent, default_genesis_txns
from .utils import log_json, log_msg, log_status, log_timer, prompt, prompt_loop

LOGGER = logging.getLogger(__name__)

AGENT_PORT = int(sys.argv[1])

TIMING = False


class AcmeAgent(DemoAgent):
    def __init__(self, http_port: int, admin_port: int, **kwargs):
        super().__init__("Acme Agent", http_port, admin_port, prefix="Acme", **kwargs)
        self.connection_id = None
        self._connection_active = asyncio.Future()
        self.cred_state = {}

    async def detect_connection(self):
        await self._connection_active

    @property
    def connection_active(self):
        return self._connection_active.done() and self._connection_active.result()

    async def handle_connections(self, message):
        if message["connection_id"] == self.connection_id:
            if message["state"] == "active" and not self._connection_active.done():
                self.log("Connected")
                self._connection_active.set_result(True)

    async def handle_credentials(self, message):
        state = message["state"]
        credential_exchange_id = message["credential_exchange_id"]
        prev_state = self.cred_state.get(credential_exchange_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[credential_exchange_id] = state

        self.log(
            "Credential: state =",
            state,
            ", credential_exchange_id =",
            credential_exchange_id,
        )

        if state == "request_received":
            # TODO handle received credential requests
            # TODO issue credentials based on the credential_definition_id
            cred_attrs = self.cred_attrs[message["credential_definition_id"]]
            await self.admin_POST(
                f"/credential_exchange/{credential_exchange_id}/issue",
                {"credential_values": cred_attrs},
            )

    async def handle_presentations(self, message):
        state = message["state"]

        presentation_exchange_id = message["presentation_exchange_id"]
        self.log(
            "Presentation: state =",
            state,
            ", presentation_exchange_id =",
            presentation_exchange_id,
        )

        if state == "presentation_received":
            # TODO handle received presentations
            print("Proof:", message)

            # TODO if presentation is a degree schema (proof of education), also ask for proof of student id
            X = False
            if X:
                proof_attrs = [
                    {"name": "name", "restrictions": [{"schema_name": ""}, {}]},
                    {"name": "date", "restrictions": [{"schema_name": ""}, {}]},
                    {"name": "degree", "restrictions": [{"schema_name": ""}, {}]},
                ]
                proof_predicates = []
                proof_request = {
                }
                await agent.admin_POST(
                    "/presentation_exchange/send_request", proof_request
                )

            # TODO if proof of student if, then validate

            pass

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])


async def main():

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    agent = None
    start_port = AGENT_PORT

    try:
        log_status("#1 Provision an agent and wallet, get back configuration details")
        agent = AcmeAgent(start_port, start_port + 1, genesis_data=genesis)
        await agent.listen_webhooks(start_port + 2)
        await agent.register_did()

        with log_timer("Startup duration:"):
            await agent.start_process()
        log_msg("Admin url is at:", agent.admin_url)
        log_msg("Endpoint url is at:", agent.endpoint)

        # Create a schema
        log_status("#3 Create a new schema on the ledger")
        with log_timer("Publish schema duration:"):
            version = format(
                "%d.%d.%d"
                % (
                    random.randint(1, 101),
                    random.randint(1, 101),
                    random.randint(1, 101),
                )
            )
            # TODO define schema
            (schema_id, credential_definition_id) = await agent.register_schema_and_creddef(
                "employee id schema", version, ["employee_id", "name", "date", "position"]
                )

        log_status("#3 Create a new schema on the ledger")
        with log_timer("Publish schema duration:"):
            version_2 = format(
                "%d.%d.%d"
                % (
                    random.randint(1, 101),
                    random.randint(1, 101),
                    random.randint(1, 101),
                )
            )
            # TODO define schema
            (schema_id_2, credential_definition_id_2) = await agent.register_schema_and_creddef(
                "income schema", version_2, ["employee_id", "name", "date", "salary"]
                )

        with log_timer("Generate invitation duration:"):
            # Generate an invitation
            log_status(
                "#5 Create a connection to alice and print out the invite details"
            )
            connection = await agent.admin_POST("/connections/create-invitation")

        agent.connection_id = connection["connection_id"]
        log_json(connection, label="Invitation response:")
        log_msg("*****************")
        log_msg(json.dumps(connection["invitation"]), label="Invitation:", color=None)
        log_msg("*****************")

        log_msg("Waiting for connection...")
        await agent.detect_connection()

        async for option in prompt_loop(
            "(1) Issue Credential, (2) Send Proof Request, "
            + "(3) Send Message (X) Exit? [1/2/3/X] "
        ):
            if option in "xX":
                break

            elif option == "1":
                log_status("#13 Issue credential offer to X")
                # TODO credential offers
                offer = {
                    "credential_definition_id": credential_definition_id,
                    "connection_id": agent.connection_id,
                }
                agent.cred_attrs[credential_definition_id] = {
                    "employee_id": "ACME0009",
                    "name": "Alice Smith",
                    "date": "2019-06-30",
                    "position": "CEO",
                }
                await agent.admin_POST("/credential_exchange/send-offer", offer)

                log_status("#13 Issue credential offer 2 to X")
                # TODO credential offers
                offer_2 = {
                    "credential_definition_id": credential_definition_id_2,
                    "connection_id": agent.connection_id,
                }
                agent.cred_attrs[credential_definition_id_2] = {
                    "employee_id": "ACME0009",
                    "name": "Alice Smith",
                    "date": "2019-06-30",
                    "salary": "120000",
                }
                await agent.admin_POST("/credential_exchange/send-offer", offer_2)

            elif option == "2":
                log_status("#20 Request proof of degree from alice")
                # TODO presentation requests
                proof_attrs = [
                    {"name": "student_id", "restrictions": [{"schema_name": "degree schema"}, {"attr::name::value": {"$eq": "Alice Smith"}}]},
                    {"name": "date", "restrictions": [{"schema_name": "degree schema"}, {"attr::name::value": {"$eq": "Alice Smith"}}]},
                    {"name": "degree", "restrictions": [{"schema_name": "degree schema"}, {"attr::name::value": {"$eq": "Alice Smith"}}]},
                ]
                proof_predicates = []
                proof_request = {
                    "name": "Proof of Education",
                    "version": "1.0",
                    "connection_id": agent.connection_id,
                    "requested_attributes": proof_attrs,
                    "requested_predicates": proof_predicates,
                }
                await agent.admin_POST(
                    "/presentation_exchange/send_request", proof_request
                )

            elif option == "3":
                msg = await prompt("Enter message: ")
                await agent.admin_POST(
                    f"/connections/{agent.connection_id}/send-message", {"content": msg}
                )

        if TIMING:
            timing = await agent.fetch_timing()
            if timing:
                for line in agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = True
        try:
            if agent:
                await agent.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        os._exit(1)
