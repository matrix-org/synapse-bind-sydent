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
from typing import Any
from unittest.mock import Mock

import aiounittest

from tests import create_module, make_awaitable


class SydentBinderTestCase(aiounittest.AsyncTestCase):
    async def test_new_assoc(self) -> None:
        """Tests that the right function calls are made when the newly registered user has
        a single 3PID associated.
        """
        http_client = Mock()
        http_client.post_json_get_json = Mock(return_value=make_awaitable(None))

        address = "jdoe@example.com"
        medium = "email"
        user_id = "@jdoe:example.com"

        module = create_module(http_mock=http_client)

        await module.on_threepid_bind(user_id, medium, address)

        self.assertEqual(http_client.post_json_get_json.call_count, 1)
        args = http_client.post_json_get_json.call_args[0]
        self.assertEqual(
            args[1], {"address": address, "medium": medium, "mxid": user_id}
        )

        store_remote_3pid_association: Mock = module._api.store_remote_3pid_association  # type: ignore[assignment]
        self.assertEqual(store_remote_3pid_association.call_count, 1)
        args = store_remote_3pid_association.call_args[0]
        self.assertEqual(args, (user_id, medium, address, "test"))

    async def test_network_error(self) -> None:
        """Tests that the process is aborted right away if an error was raised when trying
        to bind a 3PID."""

        async def post_json_get_json(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("oh no")

        http_client = Mock()
        http_client.post_json_get_json = Mock(side_effect=post_json_get_json)

        module = create_module(http_mock=http_client)

        await module.on_threepid_bind("@jdoe:matrix.org", "email", "jdoe@example.com")

        self.assertEqual(http_client.post_json_get_json.call_count, 1)

        store_remote_3pid_association: Mock = module._api.store_remote_3pid_association  # type: ignore[assignment]
        self.assertEqual(store_remote_3pid_association.call_count, 0)
