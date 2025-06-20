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

<!--
Developer TODO: Provide a list of config options accepted by the target.

This section can be created by copy-pasting the CLI output from:

```
target-actionnetwork --about --format=markdown
```
-->

A full list of supported settings and capabilities for this
target is available by running:

```bash
target-actionnetwork --about
```

### Configure using environment variables

This Singer target will automatically import any environment variables within the working directory's
`.env` if the `--config=ENV` is provided, such that config values will be considered if a matching
environment variable is set either in the terminal context or in the `.env` file.

Optional config flags include:

| name | default | description |
| -----| ------- | ----------- |
| `only_upsert_empty_fields` | `false` | If true, will not overwrite existing Contact fields in NationBuilder |

### Source Authentication and Authorization

<!--
Developer TODO: If your target requires special access on the destination system, or any special authentication requirements, provide those here.
-->

## Usage

You can easily run `target-actionnetwork` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Target Directly

```bash
target-actionnetwork --version
target-actionnetwork --help
# Test using the "Carbon Intensity" sample:
tap-carbon-intensity | target-actionnetwork --config /path/to/target-actionnetwork-config.json
```

## Developer Resources

Follow these instructions to contribute to this project.

### Initialize your Development Environment

```bash
pipx install poetry
poetry install
```