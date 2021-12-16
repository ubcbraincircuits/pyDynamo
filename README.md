# pyDynamo
![pyDynamo logo](https://ubcbraincircuits.github.io/pyDynamo/tmpLogo.png)

Application for the UI and analysis of neurons via **Dyna**mic **Mo**rphometrics.

## Installation

Providing you have a version of python 3+, this library can be installed directly from github using pip:
```
conda create --name dynamoEnv
conda activate dynamoEnv
conda install pip git
pip install --upgrade "git+https://github.com/ubcbraincircuits/pyDynamo#egg=pydynamo_brain&subdirectory=pydynamo_brain"
pip install --upgrade "git+https://github.com/padster/pyNeuroTrace#egg=pyneurotrace&subdirectory=pyneurotrace"
```
Once installed, it can be run by the following command, and optionally given a file to open:
```
pydynamo_brain
```
or
```
pydynamo_brain path/to/my/file.dyn.gz
```

## Usage
Documentation is available at https://ubcbraincircuits.github.io/pyDynamo/ . For an overview:

After opening Dynamo, two windows will show.
1)  One will contain the dynamo logo (see above), and a close button. This window should always stay open until you want to stop - then pressing the button will close dynamo completely.
2) The other will give three options:
    * *New from Stack(s)* (Ctrl-N) will let you create a new dynamo project by opening one or more unlabelled 3D .tif files, containing the neuron volumes. This can then be saved via Ctrl-S to a .dyn.gz file
    * *Open from File* (Ctrl-O) is used to re-open an existing dynamo project from a .dyn.gz file.
    * *Import from Matlab .mat* (Ctrl-I) will attempt to load dynamo data created using the old matlab version.

Once stacks are loaded, see the help dialog (F1) for all the commands available.

The recommended approach is:
1) Load the first .tif stack in the series
2) Draw the full dendritic arbor (if you save early, it'll start auto-saving too)
3) Load the next .tif stack in the series
4) Generate points in this new stack, from either
    * Importing from the previous drawing (I)
    * Importing from an SWC file (**coming**)
5) Move/add/delete points as required to match the stack images.
6) Register (R) to make sure that old points are mapped to new points correctly.
7) Repeat from step 3 until all stacks are done.

## Analysis
Currently analysis is done purely visually (i.e. 'M' or '3'), but as requirements on getting data out are clearer, there'll be a way added to export per-stack and per-branch metrics to a csv (or similar).

## Errors
As pyDynamo is currently pre-release and under active development, it may also still crash occasionally.
If this happens, let me know and I should be able to fix it - more error details should also be visible from the commandline in which the original `python dynamo.py` was run.
