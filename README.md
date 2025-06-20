# target-actionnetwork

`target-actionnetwork` is a Singer target for ActionNetwork.

Build with the [Meltano Target SDK](https://sdk.meltano.com).

<!--

Developer TODO: Update the below as needed to correctly describe the install procedure. For instance, if you do not have a PyPi repo, or if you want users to directly install from your git repo, you can modify this step as appropriate.

## Installation

Install from PyPi:

```bash
pipx install target-actionnetwork
```

Install from GitHub:

```bash
pipx install git+https://github.com/ORG_NAME/target-actionnetwork.git@main
```

-->

## Configuration

### Accepted Config Options


| name | default | description| 
|--------|--------|------------|
| campaign_origin_system | `Hotglue` | The origin system to specified for advocacy campaigns created by the connector |

### Configure using environment variables

This Singer target will automatically import any environment variables within the working directory's
`.env` if the `--config=ENV` is provided, such that config values will be considered if a matching
environment variable is set either in the terminal context or in the `.env` file.

### Source Authentication and Authorization



### Executing the Target Directly

```bash
target-actionnetwork --version
target-actionnetwork --help
# Test using the "Carbon Intensity" sample:
tap-carbon-intensity | target-actionnetwork --config /path/to/target-actionnetwork-config.json
```


## Initialize your Development Environment

```bash
pip install -e .
```

