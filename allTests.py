from test import absOrientTest, historyTest, motilityTest

def testAbsOrient():
    print ("AbsOrient test...")
    absOrientTest.run()
    print ("")
    return True

def testHistory():
    print ("History test...")
    historyTest.run()
    print ("")
    return True


def testMotility():
    print ("Motility test...")
    motilityTest.run()
    print ("")
    return True

def run():
    passed = True
    passed = passed and testAbsOrient()
    passed = passed and testHistory()
    passed = passed and testMotility()
    if passed:
        print ("\n 🙌🙌🙌 ALL TESTS PASSED 🙌🙌🙌\n")


if __name__ == '__main__':
    run()
