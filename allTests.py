from test import testHistory, motilityTest

def run():
    print ("History test...")
    testHistory.testTree()
    print ("\nMotility test...")
    motilityTest.run()

if __name__ == '__main__':
    run()
