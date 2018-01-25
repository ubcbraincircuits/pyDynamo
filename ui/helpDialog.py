from PyQt5.QtWidgets import QMessageBox

HELP_MESSAGE = """
*Ctrl* or *Right* click deletes a point or initiates a branch point
*Shift* or *Center* click a point to move it, or add a point mid-branch
   -hold *Shift* when moving a point to move all downstream points

Reassign the parent of a branch by shift-clicking a point and clicking the new parent point

*Scrollwheel* to move in Z-position, or hold shift to zoom
*Backspace*: Undo
*1,2*: Z-position UP/DOWN
*4,5,7,8*: adjust lower(4,5), or upper(7,8) brightness limits
*6*: reset image brightness
*Z,X*: Zoom
*A,S,D,W*: Panning
*Q*: Annotate a point
*F*: Show/Hide annotations
*V*: Show/Hide entire dendritic tree
*R*: AutoRegister the current branch to the previous drawing
*L*: Select Landmarks to register drifted images
*O*: Open a new window
*T*: Tile windows on screen
*H*: Cycle line thicknesses
*Ctrl-M* to save drawing session
*3*: open a 3d wire model of the current stack
*M*: Show motility plot

To quickly end a session, you can type ''close all'' into
the matlab prompt and hit the enter key to close windows
"""

def showHelpDialog():
    popup = QMessageBox(
        QMessageBox.Information,
        "Dynamo hotkeys",
        HELP_MESSAGE,
        QMessageBox.Ok
    )
    popup.exec_()
