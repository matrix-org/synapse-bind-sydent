# Copyright 2022 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from typing import Any, Dict

import attr
from synapse.module_api import ModuleApi
from synapse.module_api.errors import ConfigError

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, frozen=True)
class SydentBinderConfig:
    sydent_host: str
    use_https: bool = False


class SydentBinder:
    def __init__(self, config: SydentBinderConfig, api: ModuleApi) -> None:
        # Keep a reference to the config and Module API
        self._api = api
        self._config = config

        self._http_client = api.http_client

        protocol = "https" if config.use_https else "http"
        self._sydent_bind_url = (
            f"{protocol}://{config.sydent_host}/_matrix/identity/internal/bind"
        )

        self._api.register_account_validity_callbacks(
            on_user_registration=self.on_register,
        )

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> SydentBinderConfig:
        if "sydent_host" not in config or not isinstance(config["sydent_host"], str):
            raise ConfigError("sydent_host needs to be a string")

        return SydentBinderConfig(**config)

    async def on_register(self, user_id: str) -> None:
        """Binds the 3PID on registration."""
        # Get the list of 3PIDs for this user.
        threepids = await self._api.get_threepids_for_user(user_id)

        for threepid in threepids:
            body = {
                "address": threepid["address"],
                "medium": threepid["medium"],
                "mxid": user_id,
            }

            # Bind the threepid
            try:
                await self._http_client.post_json_get_json(self._sydent_bind_url, body)
            except Exception as e:
                # If there was an error, the IS is likely unreachable, so don't try again.
                logger.exception(
                    "Failed to bind 3PID %s to identity server at %s: %s",
                    threepid,
                    self._sydent_bind_url,
                    e,
                )
                return

            # Store the association, so we can use this to unbind later.
            await self._api.store_remote_3pid_association(
                user_id,
                threepid["medium"],
                threepid["address"],
                self._config.sydent_host,
            )
