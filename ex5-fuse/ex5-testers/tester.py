import os
import sys
import subprocess
import shutil
import glob
import fcntl
from time import sleep,localtime
from ioctl import ioctl

TARGET_NAME = "res.x86"
EX_NAME = "ex3"
TEST_TAR = EX_NAME + "_files.tar"
TEST_FOLDER = ["tests"]
MAKE_BASE = "makefile" 
TMP_DIR = os.getcwd() + "/tmp"
TO_COPY = [MAKE_BASE]
RES_FOLDER = "res"
RES = "_res"
USERS_DIR = os.getcwd()
SHORT_RES_FOLDER = "short_res"

MOUNTDIR = "mymount"
ROOTDIR = "myroot"

BLOCKSIZE = 4096
BLOCKNUM = 40
UNFUSE = "fusermount -u " + MOUNTDIR 
EXEFILE = "MyCachingFileSystem"
RUNCMD = EXEFILE + " /tmp/"+str(ROOTDIR) +" /tmp/" + \
        str(MOUNTDIR) + " " + str(BLOCKNUM) + " " + str(BLOCKSIZE)
RUNCMDXY = EXEFILE + " /tmp/"+str(ROOTDIR) +" /tmp/" + str(MOUNTDIR) + " "

runFuse = lambda x,y: os.system(RUNCMDXY + str(x) +" " + str(y))

orgDir = os.getcwd()
summery = []
file_name = "NOT_INIT"

def transFile():
    # Creating the tmp folder
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
        
    # Extracting the files
    os.chdir(USERS_DIR)
    with open(os.devnull, "w") as f:
        subprocess.call(["tar", "-xvf", file_name, "-C",TMP_DIR], stdout = f)
    
    os.chdir(orgDir)

def makeFileTest():
    dirN = os.getcwd()
    os.chdir(TMP_DIR)
    try:
        subprocess.check_output("make", shell=True) # Runs "make" w/o printing to the std
        res = not os.path.exists(EXEFILE)
    except:
        return False 

    if res:
        raw_input("Name is not good, Rename it to '" + str(EXEFILE) + "' and press 'Enter'")
        return True
    else:
        print "MakeFile is Good"
        return True
    
    # Cleaning compilation files
    for oFile in glob.glob(TMP_DIR + "/*.o"):
        os.remove (oFile)

    os.chdir(dirN)
    
def clean():
    shutil.rmtree(TMP_DIR)

def run_command(command):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    
    return process

def textDiff(org, res):
    retVal = True
    
    f1 = open(org,"r")
    f2 = open(res,"r")

    line1 = f2.readlines()
    line2 = f1.readlines()

    if len(line1) != len(line2):
        retVal =  False

    index = 0;
    for i in line1:
        user = i.upper().strip()
        school = line2[index].upper().strip()
        if user != school:
            retVal =  False
            print "Correct:",school,"|Yours:",user
       
        index +=1
    return retVal

def x2yDiff(org, res,start,end):
    f1 = open(org,"r")
    f2 = open(res,"r")

    SS = f1.readlines()
    stud = f2.readlines()

    if end > (len(stud)-1):
        return 1
        
    index = start;
    for i in SS[start:end]:
        if i != stud[index]:
            return 0
        index +=1
    return 1

def compileFile(fileN):
    fileName = fileN[fileN.rindex('/')+1:-4]
    compLine = "g++ -std=c++11 -Wall " + str(fileName) +".cpp -o " + fileName
    os.system(compLine)
    
    return fileName


def environmentSetup():
    orgDir = os.getcwd()
    os.chdir("/tmp/")
    
    if os.path.exists(MOUNTDIR) or os.path.exists(ROOTDIR):
        environmentTearDown()
    
    os.mkdir(MOUNTDIR)
    os.mkdir(ROOTDIR)
    
    os.chdir(ROOTDIR)
    
    # Creating files
    fileLst = ["basic","small","large","med"]
    lineNum = [4,1,600,30]
    for eachFile,fileLen in zip(fileLst,lineNum):
        fd = open(eachFile,'w')
        for i in xrange(fileLen):
            fd.write(str(i)+": The Due is back!\n")
        fd.close()
    
    # Creating folder
    os.mkdir("dir")
    fd = open("dir/dirFile",'w')
    fd.write("boo\n")
    fd.close()
    
    os.chdir(orgDir)
    
def environmentTearDown():
    cleaned = False
    while(not cleaned):
        try:
            if os.path.exists("ioctloutput.log"):
                os.remove("ioctloutput.log")
            orgDir = os.getcwd()
            os.chdir("/tmp/")
            os.system(UNFUSE)
            
            if os.path.exists(MOUNTDIR):
                shutil.rmtree(MOUNTDIR)
            if os.path.exists(ROOTDIR):
                shutil.rmtree(ROOTDIR)
            
            os.chdir(orgDir)
            cleaned = True
        except:
            print "BAD"
    


def Test1():
    print "Test 1"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    retVal = True
    
    
    fInF = os.listdir(os.getcwd())
    for eachFile in ["basic","small","large","med"]:
        if eachFile not in fInF:
            print eachFile,"is not in the mount folder."
            retVal = "fail"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test2():
    print "Test 2"
    try:
        # Start
        environmentSetup()
        os.system(RUNCMD)
        orgDir = os.getcwd()
        os.chdir("/tmp/"+MOUNTDIR)
        
        retVal  = True
        if not os.path.isdir("dir"):
            print "The folder 'dir' is not in the mount folder."
            retVal = "fail"
        
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "2:\tThe directory is not in the mountdir!"
        
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test3():
    print "Test 3"
    try:
        # Start
        environmentSetup()
        os.system(RUNCMD)
        orgDir = os.getcwd()
        os.chdir("/tmp/"+MOUNTDIR)
        
        retVal  = True
        os.chdir("dir")
        
        if not os.path.exists("dirFile"):
            print "The file in the directory is missing."
            retVal = "fail"
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "3:\tThe file is not in the mountdir/dir!"
        
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test4():
    print "Test 4"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    
    os.system("mv basic newbasic")
    
    if not os.path.exists("newbasic") or os.path.exists("basic"):
        print "The rename command on a file did not work"
        retVal = "4:\tThe rename function dose not work!"
    
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test5():
    print "Test 5"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    
    os.system("mv dir newdir")
    
    if not os.path.exists("newdir") or os.path.exists("dir"):
        print "The rename command on a directory did not work"
        retVal = "5:\tThe rename dir function dose not work!"
    
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test6():
    print "Test 6"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    try:
        result = subprocess.check_output("cat basic", shell=True)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "6:\tThe Cat function does not work!"
    
        
    fd = open(orgDir+"/out",'w')
    fd.write(result)
    fd.close()
    if not textDiff("/tmp/" + ROOTDIR + "/basic", orgDir+"/out"):
        retVal = "6:\tThe Cat function does not work!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test7():
    print "Test 7"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    try:
        subprocess.check_output("cat basic", shell=True)
        runIoctl("basic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "7:\tThe Basic Ioctl does not work(time or file)!"
    
    
    timeS = localtime()
    names = ["basic"]
    numbers = [1]
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    
    fd.close()
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "7:\tThe Basic Ioctl does not work(time or file)!"

    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,timeS,True):
            retVal = "7:\tThe Basic Ioctl does not work(time or file)!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test8():
    print "Test 8"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    try:
        result = subprocess.check_output("cat large", shell=True)
        runIoctl("basic")
        timeS = localtime()
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "8:\tThe Large Ioctl does not work!"
    
    names = ["large","large",
             "large","large"]
    numbers = [4,3,2,1]
    rnumbers = list(numbers)
    rnumbers.reverse()
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "8:\tThe Large Ioctl does not work!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if (not eachOctl.equals(names,numbers,timeS,False))\
        and (not eachOctl.equals(names,rnumbers,timeS,False)):
            retVal = "8:\tThe Large Ioctl does not work!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test9():
    print "Test 9"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    try:
        result = subprocess.check_output("cat large", shell=True)
        result = subprocess.check_output("cat basic", shell=True)
        sleep(1)
        result = subprocess.check_output("tail -c 3 large", shell=True)
        timeS = localtime()
        runIoctl("basic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "9:\tThe Tail does not work!"
    
    names = ["large","large",
             "large","basic",
             "large"]
    rnames = list(names)
    rnames.reverse()
    numbers = [1,2,3,1,4]
    rnumbers = list(numbers)
    rnumbers.reverse()
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "9:\tThe Tail does not work!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,timeS,False):
            retVal = "9:\tThe Tail does not work!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test10():
    print "Test 10"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    retVal  = True
    
    try:
        result = subprocess.check_output("cat basic", shell=True)
        os.chdir("/tmp/"+MOUNTDIR)
        os.system("mv basic newbasic")
    
        timeS = localtime()
        runIoctl("newbasic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "10:\tThe File name-Cache change does not work!"
    
       
    names = ["newbasic"]
    numbers = [1]
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()

    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "10:\tThe File name-Cache change does not work!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,timeS,False):
            retVal = "10:\tThe File name-Cache change does not work!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test11():
    print "Test 11"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    retVal  = True
    
    try:
        os.chdir("/tmp/"+MOUNTDIR + "/dir/")
        result = subprocess.check_output("cat dirFile", shell=True)
        os.chdir("/tmp/"+MOUNTDIR)
        os.system("mv dir newdir")
    
        timeS = localtime()
        runIoctl("newdir/dirFile")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "11:\tThe Folder name-Cache change does not work!"
      
    names = ["newdir/dirFile"]
    numbers = [1]
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "11:\tThe Folder name-Cache change does not work!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,timeS,False):
            retVal = "11:\tThe Folder name-Cache change does not work!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test12():
    print "Test 12"
    # Start
    environmentSetup()
    os.system(RUNCMD)
    orgDir = os.getcwd()
    os.chdir("/tmp/"+MOUNTDIR)
    
    retVal  = True
    try:
        result = subprocess.check_output("cat basic", shell=True)
        sleep(1)
        result = subprocess.check_output("cat basic", shell=True)
        timeS = localtime()
        runIoctl("basic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "12:\tThe time in the cache dose not update!"
    
    names = ["basic"]
    numbers = [1]
    times = [timeS]
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "12:\tThe time in the cache dose not update!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.timeEquals(names,numbers,times,timeS,False):
            retVal = "12:\tThe time in the cache dose not update!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test13():
    print "Test 13"
    # Start
    environmentSetup()
    runFuse(10,4096)
    orgDir = os.getcwd()
    
    # Creating a LOT of small files
    os.chdir("/tmp/" + ROOTDIR)
    for i in range(100):
        tmpfd = open("file"+str(i),'w')
        tmpfd.write("the dude is the dude")
        tmpfd.close()
    
    os.chdir("/tmp/"+MOUNTDIR)
    retVal  = True
    try:
        for i in range(100):
            subprocess.check_output("cat file"+str(i), shell=True)
        timeS = localtime()
        runIoctl("basic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "13:\tThe Cache small over-flow failed!"
    
    names = ["file99","file98","file97",
             "file96","file95","file94",
             "file93","file92","file91",
             "file90"]
    numbers = [1]*10
    times = [timeS]
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "13:\tThe Cache small over-flow failed!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,times,False):
            retVal = "13:\tThe Cache small over-flow failed!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test14():
    print "Test 14"
    # Start
    environmentSetup()
    runFuse(10,4096)
    orgDir = os.getcwd()
    
    # Creating big files
    os.chdir("/tmp/" + ROOTDIR)
    for i in range(10):
        tmpfd = open("file"+str(i),'w')
        for i in range(250*10):
            tmpfd.write("the dude is big!")
        tmpfd.close()
    
    os.chdir("/tmp/"+MOUNTDIR)
    retVal  = True
    try:
        for i in range(10):
            subprocess.check_output("cat file"+str(i), shell=True)
        timeS = localtime()
        runIoctl("basic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "14:\tThe Cache large over-flow failed!"
    
    
    names = ["file9"]*10
    numbers = [1,2,3,4,5,6,7,8,9,10]
    rnumbers = numbers
    rnumbers.reverse()
    times = [timeS]
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "14:\tThe Cache large over-flow failed!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,times,False):
            retVal = "14:\tThe Cache large over-flow failed!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test15():
    print "Test 15"
    # Start
    environmentSetup()
    runFuse(11,4096)
    orgDir = os.getcwd()
    
    # Creating big files
    os.chdir("/tmp/" + ROOTDIR)
    for i in range(10):
        tmpfd = open("BigFile"+str(i),'w')
        for i in range(250*10):
            tmpfd.write("the dude is big!")
        tmpfd.close()
        
    # Creating small files
    for i in range(100):
        tmpfd = open("SmallFile"+str(i),'w')
        tmpfd.write("the dude is the dude")
        tmpfd.close()
        
        
    os.chdir("/tmp/"+MOUNTDIR)
    retVal  = True
    try:
        for i in range(10):
            for j in range(100):
                subprocess.check_output("cat SmallFile"+str(j), shell=True)
                
            subprocess.check_output("cat BigFile"+str(i), shell=True)
        timeS = localtime()
        runIoctl("basic")
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "15:\tThe Cache large over-flow failed!"
    
    
    names = ["BigFile9"]*10
    names.append("SmallFile99")
    numbers = [1,1,2,3,4,5,6,7,8,9,10]
    rnumbers = numbers
    rnumbers.reverse()
    times = [timeS]
    
    fd = open(orgDir+"/ioctloutput.log",'r')
    ioctlLines = [x for x in fd.readlines() if (not x == '\n') 
                  and (not x.startswith("error"))]
    fd.close()
    
    try:
        ioctlOut = ioctlGenarator(ioctlLines)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "15:\tThe Cache large over-flow failed!"
    
    # Cheking the ioctls
    for eachOctl in ioctlOut:
        if not eachOctl.equals(names,numbers,times,False):
            retVal = "15:\tThe Cache large over-flow failed!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test16():
    print "Test 16"
    # Start
    environmentSetup()
    runFuse(10,4096)
    orgDir = os.getcwd()
    
    # Creating big files
    os.chdir("/tmp/" + ROOTDIR)
    for i in range(10):
        tmpfd = open("file"+str(i),'w')
        for i in range(250*10):
            tmpfd.write("the dude is big!")
        tmpfd.close()
    
    os.chdir("/tmp/"+MOUNTDIR)
    retVal  = True
    try:
        for i in range(10):
            result = subprocess.check_output("cat file"+str(i), shell=True)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "16:\tThe cat over large over-flow failed!"
    
    
    fd = open(orgDir+"/out",'w')
    fd.write(result)
    fd.close()
    if not textDiff("/tmp/" + ROOTDIR + "/file9", orgDir+"/out"):
        retVal = "16:\tThe cat over large over-flow failed!"
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    
    return retVal

def Test17():
    print "Test 17"
    # Start
    environmentSetup()
    orgDir = os.getcwd()
    try:
        valgrindSet(RUNCMD,orgDir)
        
        # Creating a LOT of small files
        os.chdir("/tmp/" + ROOTDIR)
        for i in range(10):
            tmpfd = open("file"+str(i),'w')
            tmpfd.write("the dude is the dude")
            tmpfd.close()
        
        os.chdir("/tmp/"+MOUNTDIR)
        for i in range(10):
            subprocess.check_output("cat file"+str(i), shell=True)
    except:
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return "17:\tThe memory is leaking!"
    
    if valgrindCheck(orgDir):
        # End
        os.chdir(orgDir)
        environmentTearDown()
        return True
    
    # End
    os.chdir(orgDir)
    environmentTearDown()
    # Memory is Leaking
    return "17:\tThe memory is leaking!"

def valgrindSet(cmdLine,orgDir):
    os.chdir(orgDir)
    valLine = "valgrind -q --log-file=valRes --leak-check=full "\
            +"--show-possibly-lost=yes --show-reachable=yes --undef-value-errors=no "
    execCmd = valLine + cmdLine
    
    os.system(execCmd)

def valgrindCheck(orgDir):
    os.chdir(orgDir)
    if not os.path.exists(os.getcwd() + "valRes"):
        return True
    
    ins = open( "valRes", "r" )
    line = ins.readline()
    if line:
        return False
    return True

def runIoctl(fileName):
    fd = os.open("/tmp/" + MOUNTDIR +"/" + str(fileName), os.O_RDONLY)
    fcntl.ioctl(fd, 0)
    os.close(fd)

def ioctlGenarator(ioctlLines):
    # Add iOctls
    allIoctls = []
    buff = []
    for line in ioctlLines:
        if len(buff) == 0:
            buff.append(line) 
            continue
        if len(line.split('\t'))<2:
            allIoctls.append(ioctl(buff))
            buff = [line]
        else:
            buff.append(line)
    allIoctls.append(ioctl(buff))
    
    outTxt = []
    for i in allIoctls:
        outTxt.append(str(i))
        
    return allIoctls
    
def exeTest(msg,testNum):
    global outFile
    global failedTest
    
    if not msg == True:
        print "Error:"
        testNum = msg.split(':')[0]
        logMsg = "\tERROR_" + str(testNum) + "\n"
        failedTest.append(int(testNum))
        
        outFile.write(logMsg)
    else:
        print str(testNum) + ": Passed! :-)"

def printNames():
    global outFile
    readmeFile = open("README","r")
    outFile.write(readmeFile.readline().strip()+":\n")
    readmeFile.close()

def main(givenName):
    global baseDir
    baseDir = os.getcwd()
    
    global file_name
    file_name = givenName
    global outFile
    outFile = open("results",'w');

    # Creating the tmp folder and moving all the files there
    transFile()
    
    # Making the files
    if makeFileTest() == False:
        # Erasing the tmpfile
        os.chdir (orgDir)
        clean()
        
        outFile.write('\tBAD_MAKEFILE\n')
        outFile.close()
        return
    
    global failedTest
    failedTest = []
    
    printNames()
    
    try:
        # Runing the files and saving the input
        ## Basic Tests
        exeTest(Test1(),1) # Checking the files are there
        exeTest(Test2(),2) # Checking the directories are there
        exeTest(Test3(),3) # Checking the files in the directories are there
        exeTest(Test4(),4) # Checking the rename function works
        exeTest(Test5(),5) # Checking the rename dir function works
        exeTest(Test6(),6) # Checking the cat function works
              
        ## Advanced Tests
        exeTest(Test7(),7) # Checking the ioctal with the basic file
        exeTest(Test8(),8) # Checking the ioctal with the large file
        exeTest(Test9(),9) # Checking that it reads only the last cluster with 'tail' command
        exeTest(Test10(),10) # Checking that if the file name is changed the name in the cash changes as well
        exeTest(Test11(),11) # Checking that if the dir name is changed the name in the cash changes as well
        exeTest(Test12(),12) # Checking that if the timestamp in the cache is updated
        exeTest(Test13(),13) # Checking that the cache handels a lot of small files
        exeTest(Test14(),14) # Checking that the cache handels a lot of large files
        exeTest(Test15(),15) # Checking that the cache handels a lot of large and small files
        exeTest(Test16(),16) # Checking that the cat handels a lot of large files
        exeTest(Test17(),17) # Checking Memory leaks
        
    except Exception as e:
        sys.stderr.write(str(e))
        print "\nexeption!"
        # End
        os.chdir(orgDir)
        isClean = False
        while(not isClean):
            try:
                environmentTearDown()
                isClean = True
            except:
                sleep(1)
        
        outFile.write('\tEXEPTION\n')
        outFile.close()
    

    # Erasing the tmpfile
    os.chdir(orgDir)
    isClean = False
    while(not isClean):
        try:
            clean()
            isClean = True
        except:
            sleep(1)

    return failedTest

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print "Usage: tester <fileName>"
        print "Your input:"
        print "tester",
        for arg in sys.argv:
            print arg,
        print ""
    
    else: 
        main(sys.argv[1])
