from test import historyTest, motilityTest

def testHistory():
    print ("History test...")
    historyTest.run()

def testMotility():
    print ("\nMotility test...")
    motilityTest.run()

def run():
    testHistory()
    # testMotility()

if __name__ == '__main__':
    run()
