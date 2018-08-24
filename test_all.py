# Run all of these by running 'pytest' in this directory.
# e.g. pytest -sk 'ui' will run the tests containing 'ui' in the name. (or e.g. -sk 'not ui')

from test import absOrientTest, dendrogramTest, historyTest, motilityTest, recursiveAdjustTest, swcTest, uiFileActionsTest

def test_absOrient():
    print ("AbsOrient test...")
    assert absOrientTest.run()
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

def test_SWC():
    print ("SWC test...")
    assert swcTest.run()
    print ("")

def test_ui(qtbot):
    print ("UI test...")
    assert uiFileActionsTest.run(qtbot)
    print ("")

def test_dendrogram():
    print ("Dendrogram test...")
    assert dendrogramTest.run()
    print ("")

if __name__ == '__main__':
    test_absOrient()
    test_history()
    test_motility()
    test_recursiveAdjust()
    test_SWC()
    test_dendrogram()
    print ("\n 🙌🙌🙌 ALL NON-UI TESTS PASSED 🙌🙌🙌\n")
