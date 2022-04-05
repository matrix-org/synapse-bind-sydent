from asyncio import Future
from typing import Awaitable, Dict, Optional, TypeVar
from unittest.mock import Mock

from synapse.module_api import ModuleApi

from synapse_bind_sydent import SydentBinder

TV = TypeVar("TV")


def make_awaitable(result: TV) -> Awaitable[TV]:
    """
    Makes an awaitable, suitable for mocking an `async` function.
    This function is copied from Synapse's test code.
    """
    future = Future()  # type: ignore
    future.set_result(result)
    return future


def create_module(
    http_mock: Mock, config_override: Optional[Dict[str, str]] = None
) -> SydentBinder:
    # Create a mock based on the ModuleApi spec, but override some mocked functions
    # because some capabilities are needed for running the tests.
    module_api = Mock(spec=ModuleApi)
    module_api.store_remote_3pid_association = Mock(return_value=make_awaitable(None))
    module_api.http_client = http_mock

    # If necessary, give parse_config some configuration to parse.
    if config_override is None:
        config_override = {}

    config_override.setdefault("sydent_base_url", "https://test")
    config = SydentBinder.parse_config(config_override)

    return SydentBinder(config, module_api)
