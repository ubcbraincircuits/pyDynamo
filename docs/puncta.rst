Puncta
================

Dynamo allows drawing puncta on top of stack images.
Puncta are treated as single points with a 3D position and a size (radius).
They are useful for marking synapses, boutons, or other discrete structures.

Drawing
---------------

**Entering puncta mode (P)**
  Press ``P`` to enter and exit puncta mode.
  While in puncta mode, the bottom of each stack window will show a puncta toolbar.

**Selecting puncta**
  Click on an existing puncta to select it. Selected puncta are highlighted.
  Puncta can appear in the following states:

  * **Normal** — unselected puncta at the current Z-slice.
  * **Selected** — the currently active puncta (shown highlighted).
  * **Out-of-plane** — puncta from other Z-slices, shown faded if ``V`` is enabled.

**Adding puncta**
  Click on empty space to add a new puncta at that X/Y position on the current Z-slice.
  The puncta will also be propagated forward to later stacks.

**Moving puncta**
  Each puncta has two properties that can be changed:

  * **Center position** — Shift-click a selected puncta, then click the new position to move it.
  * **Radius** — use ``[`` and ``]`` to decrease and increase the radius of the selected puncta.

**Deleting puncta**
  Select a puncta by clicking it, then press ``Delete`` (or ``Backspace``) to remove it.
  Deleting a puncta from one stack will remove it from all stacks.

Analysis
----------

Puncta analysis quantifies the presence, size, and change of puncta across timepoints.

**Puncta count**
  The total number of puncta per stack can be viewed in the analysis window (``M``).

**Motility**
  Puncta that appear, disappear, or move between timepoints are classified as dynamic.
  This is computed using the same added/subtracted/transitioned framework as branch analysis.

**Export**
  Puncta positions and radii can be exported to CSV via the analysis panel.
  Each row corresponds to a single puncta instance (stack, X, Y, Z, radius).
