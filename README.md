# pyDynamo
![pyDynamo logo](https://padster.github.io/pyDynamo/tmpLogo.png)

Application for the UI and analysis of neurons via **Dyna**mic **Mo**rphometrics.
...todo, write stuff

## Installation
Once this repo is public, installation will be via pip.
Until then:

1) Have python 3.6+ available (if you don't have it yet, see e.g. [Miniconda](https://conda.io/miniconda.html))
2) Requires recent versions of the following packages:
    * attrs
    * matplotlib
    * numpy
    * pandas
    * pyqt (version 5)
    * scikit-image
    * scipy
    * tifffile (from conda-forge, if using conda. will require a conda update --all after)
3) Once the repository is obtained locally (either checked out, or files downloaded), navigate to the root directory and run:
```
$> python dynamo.py
```

## Usage
Documentation coming eventually to https://padster.github.io/pyDynamo/ - until then:

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
4) Enter landmark mode (L), draw landmark locations, and exit (L again) to calculate between-image transform
5) Generate points in this new stack, from either
    * Importing from the previous drawing (I)
    * Importing from an SWC file (**coming**)
6) Move/add/delete points as required to match the stack images.
7) Register (R) to make sure that old points are mapped to new points correctly.
8) Repeat from step 3 until all stacks are done.

## Analysis
Currently analysis is done purely visually (i.e. 'M' or '3'), but as requirements on getting data out are clearer, there'll be a way added to export per-stack and per-branch metrics to a csv (or similar).

## Errors
As pyDynamo is currently pre-release and under active development, it may also still crash occasionally.
If this happens, let me know and I should be able to fix it - more error details should also be visible from the commandline in which the original `python dynamo.py` was run.
