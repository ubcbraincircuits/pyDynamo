from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QLabel, QMessageBox, QVBoxLayout

HELP_MSG = """
<h1>Mouse</h1>
<h3>Clicking on a point...</h3>
<ul>
  <li><b>Click</b> to select the point</li>
  <li><b>Right-/Ctrl-click</b> to delete the point</li>
  <li><b>Mid-/Shift-click</b> to move a point
</ul>
<h3>Clicking in empty space...</h3>
<ul>
  <li><b>Click</b> to add a new point at the end of the current branch</li>
  <li><b>Right-/Ctrl-click</b> to add a new point to a new branch</li>
  <li><b>Mid-/Shift-click</b> to add a new point mid-branch.
</ul>
<h3>Scroll wheel</h3>
<ul>
  <li><b>Scroll</b> to move through the Z stacks</li>
  <li><b>Shift-Scroll</b> to zoom in and out.</li>
</ul>

<h1>Shortcuts</h1>
<h3>Navigation</h3>
<ul>
  <li><b>1</b> and <b>2</b> to move through the Z stacks</li>
  <li><b>W, A, S</b> and <b>D</b> to pan around the image</li>
  <li><b>Z</b> and <b>X</b> to zoom in and out</li>
</ul>
<h3>Contrast</h3>
<ul>
  <li><b>4</b> and <b>5</b> to change the lower brightness limit</li>
  <li><b>6</b> to reset brightness to default</li>
  <li><b>7</b> and <b>8</b> to change the upper brightness limit</li>
</ul>
<h3>Analysis</h3>
<ul>
  <li><b>3</b> to open a 3d wire model of the current volume</li>
  <li><b>B</b> to show motility plots for all volumes</li>
  <li><b>Q</b> to annotate a point
  <li><b>L</b> to set landmarks that allow for aligning volumes</li>
</ul>
<h3>View options</h3>
<ul>
  <li><b>C</b> to change the displayed channel (if available)</li>
  <li><b>F</b> to show/hide annotations</li>
  <li><b>V</b> to show/hide points away from the current Z plane</li>
  <li><b>H</b> to cycle different line thicknesses</li>
</ul>
<h3>Project</h3>
<ul>
  <li><b>Ctrl-S</b> to save the current data to file</li>
  <li><b>O</b> to add a new image stack</li>
  <li><b>T</b> to tile all the open images on screen</li>
</ul>

<h3>Coming soon...</h3>
<ul>
  <li><b>R</b> to auto-register the current branch to the previous drawing.
</ul>
"""

class HelpDialog(QDialog):
  def __init__(self, parent=None):
    QDialog.__init__(self, parent, QtCore.Qt.WindowCloseButtonHint);
    self.setWindowTitle("Dynamo help")
    self.setModal(True)
    self.setMinimumWidth(480)

    vLayout = QVBoxLayout()
    label = QLabel(HELP_MSG, self)
    label.setTextFormat(QtCore.Qt.RichText)
    vLayout.addWidget(label, 0, QtCore.Qt.AlignHCenter)
    self.setLayout(vLayout) 

def showHelpDialog():
    HelpDialog().exec_()

"""
TODO: Keep these?
Reassign the parent of a branch by shift-clicking a point and clicking the new parent point
*Backspace*: Undo


TODO: Dynomito keys?
'*C*: Change the channel of the image being shown; GREEN/RED';
'Hold *SPACE* while clicking to place the start of a MITO';
'  Continue to hold *SPACE* while adding points to the MITO';
'  To extend an existing MITO, hold space and click on it, ...';
'  then click to add new points. Release space when done.';
'*Y*: SHOW/HIDE mitos';
'*U*: SHOW/HIDE dendritic tree';
'';
'To quickly end a session, you can type ''close all'' into';
'the matlab prompt and hit the enter key to close windows';
"""
