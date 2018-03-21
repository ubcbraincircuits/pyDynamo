from test import absOrientTest, historyTest, motilityTest

def testAbsOrient():
    print ("AbsOrient test...")
    absOrientTest.run()

def testHistory():
    print ("History test...")
    historyTest.run()

def testMotility():
    print ("\nMotility test...")
    motilityTest.run()

def run():
    # testAbsOrient()
    # testHistory()
    testMotility()

if __name__ == '__main__':
    run()
