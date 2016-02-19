'''
Created on Jun 9, 2014

@author: ifryed
'''

MOUNT_PATH = "/tmp/mymount/"

class iFile:
    
    def getOnlyFileName(self,orgPath):
        if MOUNT_PATH in orgPath:
            return orgPath[len(MOUNT_PATH):]
        
        return orgPath
    
    def __init__(self,fileLine):
        fileLine = fileLine.split('\t')
        self.name = self.getOnlyFileName(fileLine[0])
        self.num = fileLine[1]
        
        tt = fileLine[2].split(":")
        #month:day:hour:minutes:seconds:miliseconds
        self.month = tt[0]
        self.day = tt[1]
        self.hour = tt[2]
        self.min = tt[3]
        self.sec = tt[4]
        self.msec = tt[5]
    
    def __str__(self):
        return str(self.name) + "-" + str(self.num) + "<>" + str(self.min) + ":" + str(self.sec)

class ioctl:
    
    def __init__(self,lines):
        tt = lines[0].split(":")
        #month:day:hour:minutes:seconds:miliseconds
        self.month = tt[0]
        self.day = int(tt[1])
        self.hour = int(tt[2])
        self.min = int(tt[3])
        self.sec = int(tt[4])
        self.msec = int(tt[5])
        
        self.fileList = []
        for i in xrange(1,len(lines)):
            self.fileList.append(iFile(lines[i]))
    
    
    def getTime(self,line):
        return
    
    def equals(self,names,numbers,timeStruct,checkTime):
        
        if not len(names) == len(self.fileList):
#             print "Number of files do not match!"
            return False
        if checkTime:
            # Checking time
            if not (int(timeStruct.tm_mon) == int(self.month) 
                and int(timeStruct.tm_mday) == int(self.day)
                and int(timeStruct.tm_hour) == int(self.hour) 
                and int(timeStruct.tm_min) == int(self.min)
                and int(timeStruct.tm_sec) == int(self.sec)):
                
                print "Month:\t",self.month,"|",timeStruct.tm_mon,":User"
                print "Day:\t",self.day,"|",timeStruct.tm_mday,":User"
                print "Hour:\t",self.hour,"|",timeStruct.tm_hour,":User"
                print "Minute:\t",self.min,"|",timeStruct.tm_min,":User"
                print "Second:\t",self.sec,"|",timeStruct.tm_sec,":User"
                
                return False
        
        # Checking file names and numbers
        retval = True;
        for nam,num,lst in zip(names,numbers,self.fileList):
            if not (nam == lst.name 
                    and int(num) == int(lst.num)):
                print "Forward Check:"
                print "Correct:",nam,num,"|Yours:",lst.name,lst.num
                return self.backCheck(names,numbers)
                

        return retval
    
    def backCheck(self,names,numbers):
        retval = True
        
        names.reverse()
        numbers.reverse()
        
        for nam,num,lst in zip(names,numbers,self.fileList):
            if not (nam == lst.name 
                    and int(num) == int(lst.num)):
                if (retval):
                    print "Backward Check:"
                print "Correct:",nam,num,"|Yours:",lst.name,lst.num
                retval = False
        
        if retval:
            print "Backward Check is OK!"
        return retval
        
        
    def timeEquals(self,names,numbers,times,timeStruct,checkTime):
        
        if not len(names) == len(self.fileList):
            print "Number of files do not match!"
            return False
        
        
        retVal = True
        
        # Checking file names and numbers
        for nam,num,tim,lst in zip(names,numbers,times,self.fileList):
            if not (nam == lst.name 
                    and int(num) == int(lst.num)):
                
                print "Correct:",nam,num,"|Yours:",lst.name,lst.num
                retVal = False
                
            # Checking time
            if not (int(tim.tm_hour) == int(lst.hour) 
                and int(tim.tm_min) == int(lst.min)
                and int(tim.tm_sec) == int(lst.sec)):
                
                print "File Name:",nam,num
                print "Hour:\t",self.hour,"|",timeStruct.tm_hour,":User"
                print "Minute:\t",self.min,"|",timeStruct.tm_min,":User"
                print "Second:\t",self.sec,"|",timeStruct.tm_sec,":User"
                retVal = False

        return retVal
    
    def __str__(self):
        retVal = ""
        for i in self.fileList:
            retVal += str(i) +"\n"
        return str(retVal)