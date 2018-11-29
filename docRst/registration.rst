Registration
============

Registration is the act of making sure that points and branches through time
will have the  same ID in each stack of drawing. This is required for correctly
tracking the dynamic changes.

Automatic registration
----------------------
This is the most powerful form of registration. By selecting a point on one stack,
and pressing 'R', this will attempt to automatically register that point and all points later in the tree.

Registration does the following:
 * Find the 3D x/y/z position in the new stack that looks the most like the position in the old stack.
 * If the position is similar enough, move the new point there and continue down the tree.
 * Otherwise, mark the new point and everything along the tree as unregistered (green).

If there are any green points after automatic registration, these can be registered manually,
and automatic registration can be performed futher down the tree by selecting those
points and pressing 'R'.

Manual registration
-------------------
The manual form of registration can be used to select multiple points across stacks
and force them to have the same ID. To perform manual registration:

#. Enter manual registration, either by the top menu or Ctrl-Shift-R
#. Click on a point to select it in just one stack (shift-click to select in all)
#. Once the correct point is selected in all stacks, Shift-Enter will force them all to have the same ID.

When registration is complete, it can be exited by again using Ctrl-Shift-R.
If changes had been made, this will also provide a way to save the changed IDs to a file.

To assist in the process, the following are available:
 * Shortcut 'f' can be used to show the IDs of all points.
 * Shortcuts '<'/'>'/'?' will move to the next / previous points, or down the first child branch respectively.

Location-based registration
---------------------------
This is not in dynamo currently, but python code exists that matches points purely by location,
not by image content around the location. If this registration would be useful, let me know and
it can be shared and/or worked into dynamo itself.
