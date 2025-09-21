FullState
=========

``FullState`` is the central container class for a project’s state.  
It stores paths, image data, neuronal reconstructions, puncta, traces, and associated UI state, and provides helper methods for manipulating them.  

Many of the methods for ``FullState`` are used for controlling the flow of information when interacting with Dynamo files through the GUI.  
The attributes of this object are also key for interacting with Dynamo programmatically.

Attributes
----------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - **Name**
     - **Type**
     - **Description**
   * - ``_rootPath``
     - ``Optional[str]``
     - Root path where this project is saved.
   * - ``filePaths``
     - ``List[str]``
     - Paths to ``.tif`` image stacks.
   * - ``trees``
     - ``List[Tree]``
     - Neuronal tree data (one per stack).
   * - ``puncta``
     - ``List[List[Point]]``
     - Puncta annotations (per stack).
   * - ``traces``
     - ``List[str]``
     - Paths to ``.nwb`` trace files (per stack).
   * - ``uiStates``
     - ``List[UIState]``
     - UI state objects, aligned with stacks.
   * - ``projectOptions``
     - ``ProjectOptions``
     - Global project options.
   * - ``volumeSize``
     - ``Optional[List[int]]``
     - ``[channels, x, y, z]`` volume dimensions. Must match across stacks.
   * - ``channel``
     - ``int``
     - Active channel index (default: ``0``).
   * - ``drawMode``
     - ``DrawMode``
     - Current drawing mode (``DEFAULT``, ``PUNCTA``, ``RADII``, ``REGISTRA
