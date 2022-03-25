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
from urllib.parse import urlparse

import attr
from synapse.module_api import ModuleApi
from synapse.module_api.errors import ConfigError

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, frozen=True)
class SydentBinderConfig:
    sydent_base_url: str


class SydentBinder:
    def __init__(self, config: SydentBinderConfig, api: ModuleApi) -> None:
        # Keep a reference to the config and Module API
        self._api = api
        self._config = config

        self._http_client = api.http_client

        self._sydent_bind_url = (
            f"{config.sydent_base_url}/_matrix/identity/internal/bind"
        )

        scheme = urlparse(config.sydent_base_url).scheme
        self._sydent_host = config.sydent_base_url.replace(f"{scheme}://", "")

        self._api.register_third_party_rules_callbacks(
            on_threepid_bind=self.on_threepid_bind,
        )

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> SydentBinderConfig:
        if (
            "sydent_base_url" not in config
            or not isinstance(config["sydent_base_url"], str)
        ):
            raise ConfigError("sydent_base_url needs to be a string")

        if (
            not config["sydent_base_url"].startswith("http://")
            and not config["sydent_base_url"].startswith("https://")
        ):
            raise ConfigError(
                "sydent_base_url needs to include an HTTP(S) protocol scheme"
            )

        return SydentBinderConfig(**config)

    async def on_threepid_bind(self, user_id: str, medium: str, address: str) -> None:
        """Binds the 3PID to Sydent once it's been associated locally."""
        # Get the list of 3PIDs for this user.
        body = {
            "medium": medium,
            "address": address,
            "mxid": user_id,
        }

        # Bind the threepid
        try:
            await self._http_client.post_json_get_json(self._sydent_bind_url, body)
        except Exception as e:
            # If there was an error, the IS is likely unreachable, so don't try again.
            logger.exception(
                "Failed to bind %s 3PID %s to identity server at %s: %s",
                medium,
                address,
                self._sydent_bind_url,
                e,
            )
            return

        # Store the association, so we can use this to unbind later.
        await self._api.store_remote_3pid_association(
            user_id,
            medium,
            address,
            self._sydent_host,
        )
