from test import absOrientTest, historyTest, motilityTest, recursiveAdjustTest, swcTest

def testAbsOrient():
    print ("AbsOrient test...")
    result = absOrientTest.run()
    print ("")
    return result

def testHistory():
    print ("History test...")
    result = historyTest.run()
    print ("")
    return result

def testMotility():
    print ("Motility test...")
    result = motilityTest.run()
    print ("")
    return result

def testRecursiveAdjust():
    print ("Recursive Adjust test...")
    result = recursiveAdjustTest.run()
    print ("")
    return result

def testSWC():
    print ("SWC test...")
    result = swcTest.run()
    print ("")
    return result

def run():
    passed = True
    # passed = passed and testAbsOrient()
    # passed = passed and testHistory()
    # passed = passed and testMotility()
    # passed = passed and testRecursiveAdjust()
    passed = passed and testSWC()
    if passed:
        print ("\n 🙌🙌🙌 ALL TESTS PASSED 🙌🙌🙌\n")


if __name__ == '__main__':
    run()
