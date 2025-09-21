Installation
============

Requirements
------------
* Python 3.6+
* pip
* git

If you don't have these set up, one good way is to install something like the latest python3+ from [Miniconda](https://docs.conda.io/en/latest/miniconda.html),
then create your own environment: ::

 $> conda create -n dynamo pip git


Installation
------------
For a system with the requirements set up, installation will just be a pip install from this repository: ::

 $> pip install --upgrade "git+https://github.com/padster/pyDynamo#egg=pydynamo_brain&subdirectory=pydynamo_brain"

This will install any missing dependencies, pull the python code locally, and make a 'pydynamo_brain' target that starts dynamo.
To run the program, you can then execute: ::

 $> pydynamo_brain (optional path to .dyn.gz file)

Running without a path will give a popup for how to start, but you may also provide the path to an existing file and it will open that to begin.

To update the installation, simply run the pip command above again, and the new version will be fetched and installed.


Manual
------

Manual options are also available. If you want to also develop the code, you can clone this repository, make any edits, and launch
dynamo from the [dynamo.py](https://github.com/padster/pyDynamo/blob/master/pydynamo_brain/pydynamo_brain/dynamo.py) script.

It is possible to do likewise by downloading a zip of this repository, providing python and all dependencies are installed manually, however that is not recommended.
