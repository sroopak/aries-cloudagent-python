import json
import time

from bdd_support.agent_backchannel_client import (
    agent_container_register_did,
    agent_container_GET,
    agent_container_POST,
    read_schema_data,
    async_sleep,
    read_json_data,
)
from behave import given, when, then
from runners.agent_container import AgentContainer
from time import sleep


# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


@when('"{agent_name}" has a DID with role "{did_role}"')
def step_impl(context, agent_name, did_role):
    agent = context.active_agents[agent_name]

    # create a new DID in the current wallet
    created_did = agent_container_POST(agent["agent"], "/wallet/did/create")

    # publish to the ledger with did_role
    registered_did = agent_container_register_did(
        agent["agent"],
        created_did["result"]["did"],
        created_did["result"]["verkey"],
        "ENDORSER" if did_role == "ENDORSER" else "",
    )

    # make the new did the wallet's public did
    created_did = agent_container_POST(
        agent["agent"],
        "/wallet/did/public",
        params={"did": created_did["result"]["did"]},
    )

    if not "public_dids" in context:
        context.public_dids = {}
    context.public_dids[did_role] = created_did["result"]["did"]


@when('"{agent_name}" connection has job role "{connection_job_role}"')
def step_impl(context, agent_name, connection_job_role):
    agent = context.active_agents[agent_name]

    # current connection_id for the selected agent
    connection_id = agent["agent"].agent.connection_id

    # set role for agent's connection
    print("Updating role for connection:", connection_id, connection_job_role)
    updated_connection = agent_container_POST(
        agent["agent"],
        "/transactions/" + connection_id + "/set-endorser-role",
        params={"transaction_my_job": connection_job_role},
    )

    # assert goodness
    assert updated_connection["transaction_my_job"] == connection_job_role
    async_sleep(1.0)


@when('"{agent_name}" connection sets endorser info')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # current connection_id for the selected agent
    connection_id = agent["agent"].agent.connection_id
    endorser_did = context.public_dids["ENDORSER"]

    updated_connection = agent_container_POST(
        agent["agent"],
        "/transactions/" + connection_id + "/set-endorser-info",
        params={"endorser_did": endorser_did},
    )

    # assert goodness
    assert updated_connection["endorser_did"] == endorser_did
    async_sleep(1.0)


@when('"{agent_name}" authors a schema transaction with {schema_name}')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)
    connection_id = agent["agent"].agent.connection_id

    created_txn = agent_container_POST(
        agent["agent"],
        "/schemas",
        data=schema_info["schema"],
        params={"conn_id": connection_id, "create_transaction_for_endorser": "true"},
    )

    # assert goodness
    assert created_txn["txn"]["state"] == "transaction_created"
    if not "txn_ids" in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


@when('"{agent_name}" requests endorsement for the transaction')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    async_sleep(1.0)
    txn_id = context.txn_ids["AUTHOR"]

    data = read_json_data("expires_time.json")

    requested_txn = agent_container_POST(
        agent["agent"],
        "/transactions/create-request",
        data=data,
        params={"tran_id": txn_id},
    )

    # assert goodness
    assert requested_txn["state"] == "request_sent"


@when('"{agent_name}" endorses the transaction')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # find the transaction with state "request_received"
    txns = {"results": []}
    i = 5
    while 0 == len(txns["results"]) and i > 0:
        async_sleep(1.0)
        txns_queued = agent_container_GET(agent["agent"], "/transactions")
        for j in range(len(txns_queued["results"])):
            if txns_queued["results"][j]["state"] == "request_received":
                txns["results"].append(txns_queued["results"][j])
        i = i - 1
    requested_txn = txns["results"][0]
    assert requested_txn["state"] == "request_received"
    txn_id = requested_txn["transaction_id"]

    endorsed_txn = agent_container_POST(
        agent["agent"], "/transactions/" + txn_id + "/endorse"
    )

    assert endorsed_txn["state"] == "transaction_endorsed"


@when('"{agent_name}" can write the transaction to the ledger')
@then('"{agent_name}" can write the transaction to the ledger')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]
    txn_id = context.txn_ids["AUTHOR"]

    async_sleep(1.0)
    txn = agent_container_GET(agent["agent"], "/transactions/" + txn_id)
    requested_txn = txn
    assert requested_txn["state"] == "transaction_endorsed"

    written_txn = agent_container_POST(
        agent["agent"], "/transactions/" + txn_id + "/write"
    )

    assert written_txn["state"] == "transaction_acked"


@when('"{agent_name}" has written the schema {schema_name} to the ledger')
@then('"{agent_name}" has written the schema {schema_name} to the ledger')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)

    schemas = agent_container_GET(agent["agent"], "/schemas/created")
    assert len(schemas["schema_ids"]) == 1

    schema_id = schemas["schema_ids"][0]
    schema = agent_container_GET(agent["agent"], "/schemas/" + schema_id)

    # TODO assert goodness


@when('"{agent_name}" authors a credential definition transaction with {schema_name}')
@then('"{agent_name}" authors a credential definition transaction with {schema_name}')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # TODO for now assume there is a single schema; should find the schema based on the supplied name
    schemas = agent_container_GET(agent["agent"], "/schemas/created")
    assert len(schemas["schema_ids"]) == 1

    schema_id = schemas["schema_ids"][0]
    created_txn = agent_container_POST(
        agent["agent"],
        "/credential-definitions",
        data={
            "schema_id": schema_id,
            "tag": "test_cred_def_with_endorsement",
            "support_revocation": True,
            "revocation_registry_size": 1000
        },
        params={"conn_id": connection_id, "create_transaction_for_endorser": "true"},
    )

    # assert goodness
    assert created_txn["txn"]["state"] == "transaction_created"
    if not "txn_ids" in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


@when('"{agent_name}" has written the credential definition for {schema_name} to the ledger')
@then('"{agent_name}" has written the credential definition for {schema_name} to the ledger')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)

    cred_defs = agent_container_GET(agent["agent"], "/credential-definitions/created")
    assert len(cred_defs["credential_definition_ids"]) == 1

    cred_def_id = cred_defs["credential_definition_ids"][0]
    cred_def = agent_container_GET(agent["agent"], "/credential-definitions/" + cred_def_id)

    # TODO assert goodness


