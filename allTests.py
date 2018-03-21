from test import absOrientTest, historyTest, motilityTest

def testAbsOrient():
    print ("AbsOrient test...")
    absOrientTest.run()
    print ("")

def testHistory():
    print ("History test...")
    historyTest.run()
    print ("")

def testMotility():
    print ("Motility test...")
    motilityTest.run()
    print ("")

def run():
    testAbsOrient()
    testHistory()
    testMotility()

if __name__ == '__main__':
    run()
