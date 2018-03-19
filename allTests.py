from test import testHistory, motilityTest

def testHistory():
    print ("History test...")
    testHistory.testTree()

def testMotility():
    print ("\nMotility test...")
    motilityTest.run()

def run():
    # testHistory()
    testMotility()

if __name__ == '__main__':
    run()
