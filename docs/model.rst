Model objects
=============

Tree, Branch, and Point
-----------------------

This page documents the core data structures that represent a 3D neuronal reconstruction in Dynamo: **Tree**, **Branch**, and **Point**.  
These classes model soma-rooted trees, ordered branch point lists, and per-node metadata, and are used by the GUI and by programmatic workflows.

Tree Class
----------

The ``Tree`` class represents a 3D neuronal reconstruction, anchored at a soma (``rootPoint``) and composed of multiple ``Branch`` objects.  
It provides methods to query, edit, and traverse the dendritic/axonal tree, as well as utilities for distance calculations and cloning.

Attributes
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Name**
     - **Type**
     - **Description**
   * - ``rootPoint``
     - ``Optional[Point]``
     - Soma / root node of the tree.
   * - ``branches``
     - ``List[Branch]``
     - All branches in the tree. Each branch contains an ordered list of points.
   * - ``transform``
     - ``Transform``
     - Image-to-world transform (identity; scaling from ``FullState.projectOptions.pixelSizes``).
   * - ``_parentState``
     - ``Optional[UIState]``
     - Internal link back to the ``UIState``.

Core Methods
~~~~~~~~~~~~

**Lookup**

- ``getPointByID(pointID, includeDisconnected=False)`` → ``Optional[Point]``  
- ``getBranchByID(branchID)`` → ``Optional[Branch]``  
- ``flattenPoints(includeDisconnected=False)`` → ``List[Point]``  

**Editing**

- ``addBranch(branch)`` → ``int`` — Add branch, return index.  
- ``removeBranch(branch)`` → ``None`` — Remove branch (must be empty).  
- ``removePointByID(pointID)`` → ``Optional[Point]`` — Remove a point and cleanup.  
- ``reparentPoint(childPoint, newParent, newBranchID=None)`` → ``Optional[str]`` — Reparent a point and descendants.  
- ``movePoint(pointID, newLocation, downstream=False)`` → ``None`` — Move point (and optionally downstream).  

**Traversal & Tree Manipulation**

- ``nextPointFilteredWithCount(sourcePoint, filterFunc, delta)`` → ``(Optional[Point], int)``  
- ``continueParentBranchIfFirst(point)`` → ``None``  
- ``updateAllPrimaryBranches(point=None)`` → ``None``  
- ``updateAllBranchesMinimalAngle(point=None)`` → ``None``  

**Geometry & Distance**

- ``worldCoordPoints(points)`` → coordinates in world units.  
- ``spatialDist(p1, p2)`` → float, Euclidean distance.  
- ``spatialAndTreeDist(p1, p2)`` → (euclidean, path).  
- ``spatialRadius()`` → max Euclidean radius.  
- ``spatialAndTreeRadius()`` → max (euclidean, path) radius.  
- ``closestPointTo(location, zFilter=False)`` → ``Optional[Point]``.  
- ``closestPointToWorldLocation(worldLocation)`` → ``Optional[Point]``.  

**Cloning & Cleanup**

- ``clearAndCopyFrom(otherTree, idMaker)`` → ``None``.  
- ``cleanBranchIDs()`` → ``None``.  
- ``cleanEmptyBranches()`` → ``int`` (branches removed).  

Branch Class
------------

``Branch`` represents a single connected segment of a neuronal tree, starting at a ``parentPoint`` and containing an ordered list of ``Point`` objects.  
It provides indexing, editing, labeling queries, subtree traversal, and world-space length utilities.

Attributes
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Name**
     - **Type**
     - **Description**
   * - ``id``
     - ``str``
     - Branch identifier.
   * - ``_parentTree``
     - ``Tree``
     - Owning tree (set by ``Tree.addBranch``).
   * - ``parentPoint``
     - ``Optional[Point]``
     - Node where this branch originates.
   * - ``points``
     - ``List[Point]``
     - Ordered list of points.
   * - ``isEnded``, ``colorData``
     - —
     - Reserved placeholders.
   * - ``reparentTo``
     - ``Optional[Point]``
     - Temporary hook for reparenting.

Core Methods
~~~~~~~~~~~~

**Indexing & Queries**

- ``indexInParent()`` → index in ``tree.branches``.  
- ``indexForPointID(pointID)`` / ``indexForPoint(point)`` → position or -1.  
- ``isEmpty()`` → bool.  
- ``hasChildren()`` → bool.  
- ``hasPointWithAnnotation(annotation, recurseUp=False)`` → bool.  
- ``isAxon(axonLabel='axon', recurseUp=True)`` → bool.  
- ``isBasal(basalLabel='basal', recurseUp=True)`` → bool.  
- ``isFilo(maxLength)`` → (bool, length).  
- ``getOrder(centrifugal=False)`` → int.  

**Editing**

- ``addPoint(point)`` → index.  
- ``insertPointBefore(point, index)`` → index.  
- ``removePointLocally(point)`` → Optional[Point].  
- ``setParentPoint(parentPoint)`` → None.  

**Traversal & Subtree**

- ``flattenSubtreePoints(startIdx=0)`` → list of points.  
- ``subtreeContainsID(pointID)`` → bool.  

**Lengths (world space)**

- ``worldLengths(fromIdx=0)`` → (total, toLastBranchPoint).  
- ``cumulativeWorldLengths()`` → list of distances.  
- ``pointsWithParentIfExists()`` → list of points.  

Utilities
~~~~~~~~~

- ``_lastPointWithChildren(points)`` → index or -1.  
- ``_lastPointWithLabel(points, label)`` → index or -1.  

Point Class
-----------

``Point`` represents a node in 3D pixel space.  
It links to its owning branch, can have child branches, and carries optional radius and annotations.  
World-space methods require access to ``FullState`` for scaling.

Attributes
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Name**
     - **Type**
     - **Description**
   * - ``id``
     - ``str``
     - Unique identifier.
   * - ``location``
     - ``Point3D``
     - (x, y, z) in pixels.
   * - ``radius``
     - ``Optional[float]``
     - Radius in pixels.
   * - ``parentBranch``
     - ``Optional[Branch]``
     - Owning branch.
   * - ``annotation``
     - ``str``
     - Free-text label.
   * - ``children``
     - ``List[Branch]``
     - Child branches.
   * - ``manuallyMarked``
     - ``Optional[bool]``
     - Flag for curation.
   * - ``hilighted``
     - ``Optional[bool]``
     - Deprecated.

Core Methods
~~~~~~~~~~~~

**Topology & Position**

- ``isRoot()`` → bool.  
- ``indexInParent()`` → int.  
- ``isLastInBranch()`` → bool.  
- ``removeChildrenByID(branchID)`` → None.  

**Traversal**

- ``nextPointInBranch(delta=1, noWrap=False)`` → Optional[Point].  
- ``pathFromRoot()`` → list of points.  

**Subtree**

- ``flattenSubtreePoints()`` → list of points.  
- ``subtreeContainsID(pointID)`` → bool.  

**Geometry**

- ``radiusFromAncestors()`` → float.  
- ``longestDistanceToLeaf()`` → float.  
- ``returnWorldRadius(fullState)`` → float.  
