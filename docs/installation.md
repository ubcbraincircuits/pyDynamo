# Installation

This library can be installed using [uv](https://docs.astral.sh/uv/).

## Quick install

If you don't have uv, install it first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then create an environment and install:
```bash
uv venv --python 3.10 dynamoEnv
source dynamoEnv/bin/activate
uv pip install --upgrade -e "git+https://github.com/ubcbraincircuits/pyDynamo#egg=pydynamo_brain&subdirectory=pydynamo_brain"
uv pip install pyNeuroTrace
```

> **Note for GPU users:** uv installs the CPU-only build of PyTorch by default. To use a CUDA-enabled build, install torch manually before the above, e.g. for CUDA 12.1:
> ```bash
> uv pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121
> ```

Once installed, run with:
```bash
pydynamo_brain
```
or optionally pass a file to open directly:
```bash
pydynamo_brain path/to/my/file.dyn.gz
```

## Updating

To update to the latest version, re-run the install command:
```bash
uv pip install --upgrade -e "git+https://github.com/ubcbraincircuits/pyDynamo#egg=pydynamo_brain&subdirectory=pydynamo_brain"
```
