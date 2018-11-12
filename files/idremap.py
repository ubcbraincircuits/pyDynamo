import csv
import os

# ID Remappings. TSV file format, each row:
#   stackID \t fromID \t toID
# showing a change from fromID to toID in the given stack.

# Given path, load TSV into ID remap.
# Result is an array: maps stack ID (number) to list of (fromID, toID) pairs
def loadRemap(path):
    remap = []
    with open(path) as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for row in reader:
            stackID, fromID, toID = int(row[0]), row[1], row[2]
            while len(remap) <= stackID:
                remap.append([])
            remap[stackID].append((fromID, toID))
    return remap

# Write results back to file, first merging with any prior rewrites
def saveRemapWithMerge(path, newRemap):
    if os.path.isfile(path):
        oldRemap = loadRemap(path)
        print ("OLD:")
        print (oldRemap)
        print ("\nNEW:")
        print (newRemap)
        newRemap = _mergeFullRemap(oldRemap, newRemap)
        print ("\nMERGED:")
        print (newRemap)

    with open(path, 'w') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t')
        for stackID, stackRemap in enumerate(newRemap):
            for (fromID, toID) in stackRemap:
                writer.writerow([stackID, fromID, toID])

# Merge two full remaps, by merging each stack separately.
def _mergeFullRemap(oldRemap, newRemap):
    result = []

    # Merge the overlap...
    lastStack = min(len(oldRemap), len(newRemap))
    for stackID in range(lastStack):
        result.append(_mergeSingleRemap(oldRemap[stackID], newRemap[stackID]))

    # ... then copy any final stages from old and new remaps:
    result.extend([pair for pair in oldRemap[lastStack:]])
    result.extend([pair for pair in newRemap[lastStack:]])
    return result

def _mergeSingleRemap(oldRemap, newRemap):
    remap, inverseMap = [], {}
    for pair in oldRemap:
        remap.append(pair)

    for fromID, newID in newRemap:
        matchedOld = False
        for i, pair in enumerate(remap):
            if pair[1] == fromID:
                remap[i] = (pair[0], newID)
                matchedOld = True
                break
        if not matchedOld:
            remap.append((fromID, newID))
    return remap
