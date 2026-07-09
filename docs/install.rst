Installation
============

Requirements
------------
* Python 3.10+
* `uv <https://docs.astral.sh/uv/>`_

If you don't have uv, install it with the command for your platform.

On macOS / Linux::

 $> curl -LsSf https://astral.sh/uv/install.sh | sh

On Windows (PowerShell)::

 PS> powershell -c "irm https://astral.sh/uv/install.ps1 | iex"


Installation
------------
Create a virtual environment and activate it.

On macOS / Linux::

 $> uv venv --python 3.10 dynamoEnv
 $> source dynamoEnv/bin/activate

On Windows (PowerShell)::

 PS> uv venv --python 3.10 dynamoEnv
 PS> dynamoEnv\Scripts\Activate.ps1

Then install from this repository (same on every platform)::

 $> uv pip install --upgrade "git+https://github.com/ubcbraincircuits/pyDynamo#egg=pydynamo_brain&subdirectory=pydynamo_brain"
 $> uv pip install pyNeuroTrace

This will install all dependencies and make a ``pydynamo_brain`` command available.

**GPU users:** uv installs CPU-only PyTorch by default. For CUDA support, install torch first::

 $> uv pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121

To run the program::

 $> pydynamo_brain (optional path to .dyn.gz file)

Running without a path will give a popup for how to start, but you may also provide the path to an existing file and it will open that to begin.

To update the installation, simply run the uv pip install command above again.


Manual
------

Manual options are also available. If you want to also develop the code, you can clone this repository, make any edits, and launch
dynamo from the `dynamo.py <https://github.com/padster/pyDynamo/blob/master/pydynamo_brain/pydynamo_brain/dynamo.py>`_ script.
