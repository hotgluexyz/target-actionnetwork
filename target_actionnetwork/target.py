"""ActionNetwork target class."""

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.target_sdk.target import TargetHotglue
from hotglue_singer_sdk.helpers.capabilities import AlertingLevel

from target_actionnetwork.sinks import (
    ContactsSink,
)

class TargetActionNetwork(TargetHotglue):
    """Sample target for ActionNetwork."""

    config_jsonschema = th.PropertiesList(
        th.Property("token", th.StringType, required=True),
    ).to_dict()

    alerting_level = AlertingLevel.ERROR

    name = "target-actionnetwork"

    SINK_TYPES = [
        ContactsSink,
    ]
    
    MAX_PARALLELISM = 1

    def get_sink_class(self, stream_name: str):
        return next(
            (
                sink_class
                for sink_class in self.SINK_TYPES
                if sink_class.name.lower() == stream_name.lower()
            ),
            None,
        )

if __name__ == "__main__":
    TargetActionNetwork.cli()
