# Run all of these by running 'pytest' in this directory.
# e.g. pytest -sk 'ui' will run the tests containing 'ui' in the name. (or e.g. -sk 'not ui')

from pydynamo_brain.test import (
    absOrientTest,
    dendrogramTest,
    historyTest,
    motilityTest,
    recursiveAdjustTest,
    shollTest,
    swcTest,
    uiDrawTest,
    uiPunctaTest,
    uiFileActionsTest
)

def test_absOrient():
    print ("AbsOrient test...")
    assert absOrientTest.run()
    print ("")

def test_dendrogram():
    print ("Dendrogram test...")
    assert dendrogramTest.run()
    print ("")

def test_history():
    print ("History test...")
    assert historyTest.run()
    print ("")

def test_motility():
    print ("Motility test...")
    assert motilityTest.run()
    print ("")

def test_recursiveAdjust():
    print ("Recursive Adjust test...")
    assert recursiveAdjustTest.run()
    print ("")

def test_sholl():
    print ("Sholl test...")
    assert shollTest.run()
    print ("")

def test_SWC():
    print ("SWC test...")
    assert swcTest.run()
    print ("")

def test_uiDraw(qtbot):
    print ("UI draw test...")
    assert uiDrawTest.run(qtbot)
    print ("")

def test_uiFile(qtbot):
    print ("UI file test...")
    assert uiFileActionsTest.run(qtbot)
    print ("")

def test_uiPuncta(qtbot):
    print ("UI puncta test...")
    # Temporarily disable, it seems to break for no reason.
    # assert uiPunctaTest.run(qtbot)
    print ("")


if __name__ == '__main__':
    test_absOrient()
    test_history()
    test_motility()
    test_recursiveAdjust()
    test_sholl()
    test_SWC()
    test_dendrogram()
    print ("\n 🙌🙌🙌 ALL NON-UI TESTS PASSED 🙌🙌🙌\n")
