"""Indy SDK verifier implementation."""

import json
import logging

import indy.anoncreds
from indy.error import IndyError

from ...core.profile import Profile

from ..verifier import IndyVerifier

LOGGER = logging.getLogger(__name__)


class IndySdkVerifier(IndyVerifier):
    """Indy-SDK verifier implementation."""

    def __init__(self, profile: Profile):
        """
        Initialize an IndyVerifier instance.

        Args:
            profile: Active Profile instance

        """
        self.profile = profile

    async def verify_presentation(
        self,
        pres_req,
        pres,
        schemas,
        credential_definitions,
        rev_reg_defs,
        rev_reg_entries,
    ) -> bool:
        """
        Verify a presentation.

        Args:
            pres_req: Presentation request data
            pres: Presentation data
            schemas: Schema data
            credential_definitions: credential definition data
            rev_reg_defs: revocation registry definitions
            rev_reg_entries: revocation registry entries
        """

        #LOGGER.debug(f">>> received presentation: {pres}")
        #LOGGER.debug(f">>> for pres_req: {pres_req}")
        #try:
        #    self.non_revoc_intervals(pres_req, pres, credential_definitions)
        #    await self.check_timestamps(self.profile, pres_req, pres, rev_reg_defs)
        #    await self.pre_verify(pres_req, pres)
        #except ValueError as err:
        #    LOGGER.error(
        #        f"Presentation on nonce={pres_req['nonce']} "
        #        f"cannot be validated: {str(err)}"
        #    )
        #    return False

        LOGGER.debug(f">>> verifying presentation: {pres}")
        LOGGER.debug(f">>> for pres_req: {pres_req}")
        try:
            verified = await indy.anoncreds.verifier_verify_proof(
                json.dumps(pres_req),
                json.dumps(pres),
                json.dumps(schemas),
                json.dumps(credential_definitions),
                json.dumps(rev_reg_defs),
                json.dumps(rev_reg_entries),
            )
        except IndyError:
            LOGGER.exception(
                f"Validation of presentation on nonce={pres_req['nonce']} "
                "failed with error"
            )
            verified = False

        return verified
