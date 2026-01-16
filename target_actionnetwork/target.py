"""ActionNetwork target class."""

from target_hotglue.target import TargetHotglue

from target_actionnetwork.sinks import (
    ContactsSink,
)

class TargetActionNetwork(TargetHotglue):
    """Sample target for ActionNetwork."""

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
