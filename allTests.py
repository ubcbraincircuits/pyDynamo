from test import absOrientTest, historyTest, motilityTest, recursiveAdjustTest

def testAbsOrient():
    print ("AbsOrient test...")
    result = absOrientTest.run()
    print ("")
    return True

def testHistory():
    print ("History test...")
    result = historyTest.run()
    print ("")
    return True


def testMotility():
    print ("Motility test...")
    result = motilityTest.run()
    print ("")
    return True

def testRecursiveAdjust():
    print ("Recursive Adjust test...")
    result = recursiveAdjustTest.run()
    print ("")
    return True

def run():
    passed = True
    passed = passed and testAbsOrient()
    passed = passed and testHistory()
    passed = passed and testMotility()
    passed = passed and testRecursiveAdjust()
    if passed:
        print ("\n 🙌🙌🙌 ALL TESTS PASSED 🙌🙌🙌\n")


if __name__ == '__main__':
    run()
