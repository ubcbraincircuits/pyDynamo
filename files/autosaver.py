import os
import os.path
import time
import util

from .files import saveState

# Save every 3 minutes
MAX_UNSAVED_MS = 3 * 60 * 1000

# Append current time to autosave files, formatting copied from original matlab code.
DATETIME_SUFFIX_FORMAT = "%m-%d-%Y_%H-%M"

# Name of child directory to autosave to
AUTOSAVE_DIR = "autosave"

class AutoSaver():
    def __init__(self, fullState):
        self.fullState = fullState
        self.lastSaveMs = util.currentTimeMillis()

    def handleStateChange(self):
        msSinceLastSave = self._msSinceLastSave()
        if msSinceLastSave < MAX_UNSAVED_MS:
            return
        if self.fullState._rootPath is None:
            return

        pathToSave = self._buildAutoSavePath(self.fullState._rootPath)
        saveState(self.fullState, pathToSave)
        self.lastSaveMs = util.currentTimeMillis()
        print ("Autosaved to " + pathToSave)

    def _msSinceLastSave(self):
        return util.currentTimeMillis() - self.lastSaveMs

    def _buildAutoSavePath(self, rootPath):
        path, fullName = os.path.split(rootPath)
        autoSaveDir = os.path.join(path, AUTOSAVE_DIR)
        if not os.path.isdir(autoSaveDir):
            print ("Creating save directory.")
            os.makedirs(autoSaveDir)

        name, ext = os.path.splitext(fullName)
        return os.path.join(
            autoSaveDir,
            "%s_%s.dyn.gz" % (name, time.strftime(DATETIME_SUFFIX_FORMAT))
        )
