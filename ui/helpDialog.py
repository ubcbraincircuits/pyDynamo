from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QLabel, QMessageBox, QVBoxLayout

HELP_MSG = """
<table><tr><td>

<h1>Mouse</h1>
<h3>Clicking on a point...</h3>
<ul>
  <li><b>Click</b> to select the point</li>
  <li><b>Right-/Ctrl-click</b> to delete the point</li>
  <li><b>Mid-/Shift-click</b> to move a point, then...
    <ul>
      <li>Click to move just that point in the current stack</li>
      <li>Shift-click to move that point and all points later in the tree</li>
      <li>Ctrl-click to move that point in the current and all later stacks</li>
      <li>Ctrl-Shift-click to move all points down the tree in all later stacks</li>
    </ul>
  </li>
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

</td><td>

<h1>Shortcuts</h1>
<h3>Drawing</h3>
<ul>
  <li><b>Q</b> to annotate a point</li>
  <li><b>Ctrl-R</b> to replace the parent of a point (click next on the new parent)</li>
  <li><b>Ctrl-B</b> on a branch start will make that branch continue its parent's branch</li>
  <li><b>L</b> to set landmarks that allow for aligning volumes</li>
</ul>
<h3>Analysis</h3>
<ul>
  <li><b>3</b> to open a 3d wire model of the current volume</li>
  <li><b>M</b> to show motility plots for all volumes</li>
</ul>
<h3>Registration</h3>
<ul>
<li><b>R</b> for automatic registration: adjust point locations based the previous stack</li>
<li><b>Ctrl-Shift-R</b> to enter/leave manual registration mode.
  <ul>
    <li>Click on points, and <b>Shift-Enter</b> to set all to the same ID</li>
    <li>Optionally save the ID changes on exit</li>
  </ul>
</li>
</ul>
<h3>Navigation</h3>
<ul>
  <li><b>1</b> and <b>2</b> to move through the Z stacks</li>
  <li><b>W, A, S</b> and <b>D</b> to pan around the image</li>
  <li><b>X</b> and <b>Z</b> to zoom in and out respectively</li>
  <li><b>&lt;</b> and <b>&gt;</b> to move to next/previous point in branch</li>
  <li><b>?</b> to move to the child of the first branch off the current point</li>
</ul>
<h3>Contrast</h3>
<ul>
  <li><b>4</b> and <b>5</b> to change the lower brightness limit</li>
  <li><b>6</b> to reset brightness to default</li>
  <li><b>7</b> and <b>8</b> to change the upper brightness limit</li>
</ul>

</td><td>

<h1>Shortcuts</h1>
<h3>View options</h3>
<ul>
  <li><b>J</b> to cycle different line thicknesses</li>
  <li><b>Shift-J</b> to cycle different dot thicknesses</li>
  <li><b>C</b> to change the displayed channel (if available)</li>
  <li><b>F</b> to toggle showing annotations / IDs / nothing.</li>
  <li><b>V</b> to show/hide points away from the current Z plane</li>
  <li><b>H</b> to show/hide hilighted points</li>
  <li><b>Shift-H</b> to show/hide hide the entire tree</li>
  <li><b>= (equals)</b> to toggle the Z-stack being relative to selected point.</li>
  <li><b>_ (underscore)</b> to flatten all Z-stacks to one image.</li>
  <li><b>T</b> to tile all the open images on screen</li>
</ul>
<h3>Project</h3>
<ul>
  <li><b>Ctrl-S</b> to save the current data over its current file</li>
  <li><b>Ctrl-Shift-S</b> to save the current data to a new file</li>
  <li><b>N</b> to add a new image stack</li>
  <li><b>I</b> to import tree structure and locations from the previous stack to the current one</li>
  <li><b>Ctrl-I</b> to import tree structure and locations from an .SWC file</li>
  <li><b>Ctrl-W</b> to close the current stack window</li>
  <li><b>Ctrl-Shift-W</b> to close all of dynamo.</li>
</ul>

</td></tr></table>
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

    #app = QtWidgets.QApplication.instance()
    #geom = app.desktop().screenGeometry()
    self.showMaximized()

def showHelpDialog():
    HelpDialog().exec_()

"""

TODO: Dynomito keys?
'Hold *SPACE* while clicking to place the start of a MITO';
'  Continue to hold *SPACE* while adding points to the MITO';
'  To extend an existing MITO, hold space and click on it, ...';
'  then click to add new points. Release space when done.';
'*Y*: SHOW/HIDE mitos';
"""
