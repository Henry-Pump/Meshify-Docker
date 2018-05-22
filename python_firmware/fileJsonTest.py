import simplejson as json
import os
dict = {}
for dirname, dirnames, filenames in os.walk("/root"):
    # print path to all subdirectories first.


    print "##########################################"
    print "new directory: " + dirname
    print "##########################################"
    # print path to all filenames.
    tempDictParent = {}
    for filename in filenames:
        tempDict = {}
        filepath = os.path.join(dirname, filename)
        try:
            fileMem = os.stat(filepath).st_size
            fileDate = os.stat(filepath).st_mtime
        except:
            fileMem = ""
            fileDate = ""
        print filepath, fileMem, fileDate
        tempDict["mem"] = fileMem
        tempDict["date"] = fileDate
        tempDictParent[filename] = tempDict

    dict[dirname] = tempDictParent


    # Advanced usage:
    # editing the 'dirnames' list will stop os.walk() from recursing into there.
    if '.git' in dirnames:
        # don't go into any .git directories.
        dirnames.remove('.git')
    print dict
    value = json.dumps(dict)
    print value
