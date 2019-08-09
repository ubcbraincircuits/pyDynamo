"""
Common collection of methods that can be applied to style the UI in a user-friendly way.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDesktopWidget, QMessageBox

# Given a widget, make the cursor look like a hand over it.
#   Same as CSS's cursor:pointer, should be used for clickable things.
def cursorPointer(widget):
  widget.setCursor(QCursor(Qt.PointingHandCursor))
  return widget

# Convert an edit box into a float value, using a default if it's invalid.
def floatOrDefault(lineEdit, value):
    try:
        return float(lineEdit.text())
    except ValueError:
        return value

# Given a window, position it on the middle of the screen
def centerWindow(window):
    frameGm = window.frameGeometry()
    frameGm.moveCenter(QDesktopWidget().availableGeometry().center())
    window.move(frameGm.topLeft())

# Clear all children from a layout
def clearChildWidgets(layout):
    while layout.count() > 0:
        item = layout.itemAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        layout.removeItem(item)
    layout.update()
    layout.parentWidget().repaint()

# Create and pop up a message window, to grab access while slow stuff is happening
def createAndShowInfo(msg):
    infoBox = QMessageBox(QMessageBox.Information, msg, "")
    infoBox.setWindowModality(Qt.NonModal)
    infoBox.show()
    return infoBox
