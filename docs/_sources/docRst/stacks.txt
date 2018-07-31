Stacks
================

Initial options
---------------

When you first start Dynamo, you have the following options:

.. figure:: ../img/initialOptions.png
  :align: center

**New from Stacks** (Ctrl-N)
  Choose this to start a new Dynamo project. Use this to load one or more .tif stacks,
  to which you can later draw on the dendritic structure.

**Open from File** (Ctrl-O)
  This option is used to reload an existing ``.dyn.gz`` file with .tif stacks and drawn tree structures.

**Import from Matlab .mat** (Ctrl-I)
  Use this to load a ``.mat`` matlab file created with an older version of Dynamo.

Note: when loading an existing file (either Ctrl-O or Ctrl-I), if the tif files cannot be found
at their old location, you will be asked to find the new location of each file.

Stack list
----------

After selecting the initial project option, a window containing a list of all stacks will be visible:

.. figure:: ../img/stackListView.png
  :align: center

This will contain a list of all the stacks loaded in the project. From here, stacks can be
hidden and made visible again. Additionally, if the data for a stack is incorrect,
an entire stack can be deleted from the project.

Pressing 'T' will bring all visible stacks to the screen and tile them for simple viewing.
