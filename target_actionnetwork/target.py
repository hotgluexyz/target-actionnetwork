"""ActionNetwork target class."""

from __future__ import annotations

from singer_sdk import typing as th
from singer_sdk.target_base import Target
from target_hotglue.target import TargetHotglue

from target_actionnetwork.sinks import (
    ContactsSink,
)


class TargetActionNetwork(Target, TargetHotglue):
    """Sample target for ActionNetwork."""

    name = "target-actionnetwork"

    SINK_TYPES = []
    MAX_PARALLELISM = 1

    def __init__(
        self,
        config,
        parse_env_config: bool = False,
        validate_config: bool = True,
        state: str = None,
    ) -> None:
        self.config_file = config[0]
        super().__init__(config, parse_env_config, validate_config)

    def get_sink_class(self, stream_name: str):
        return ContactsSink


if __name__ == "__main__":
    TargetActionNetwork.cli()