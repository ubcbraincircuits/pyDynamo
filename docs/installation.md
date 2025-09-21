# Installation
Providing you have a version of python 3+, this library can be installed directly from github using pip:

## Quick install (conda recommended)
```bash
conda create -n dynamoEnv python=3.10 anaconda
conda activate dynamoEnv
conda install pip git
pip install --upgrade -e "git+https://github.com/ubcbraincircuits/pyDynamo#egg=pydynamo_brain&subdirectory=pydynamo_brain"
pip install pyNeuroTrace


Once installed, it can be run by the following command, and optionally given a file to open:
```bash
pydynamo_brain

