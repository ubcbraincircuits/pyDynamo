# Run all of these by running 'pytest' in this directory.

from test import absOrientTest, historyTest, motilityTest, recursiveAdjustTest, swcTest

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

if __name__ == '__main__':
    test_absOrient()
    test_history()
    test_motility()
    test_recursiveAdjust()
    test_SWC()
    print ("\n 🙌🙌🙌 ALL TESTS PASSED 🙌🙌🙌\n")
