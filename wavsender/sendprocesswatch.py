
class SendProcessWatch(object):
    def __init__(self, parent):
        print "SendProcessWatch"
        self.parentRead = parent.read
        self.parentWrite = parent.write
        self.parentDoOnStart = parent.doOnStart
        self.parentRun = parent.run
        parent.read = self.read
        parent.write = self.write
        parent.doOnStart = self.doOnStart
        parent.run = self.run
        self.parent = parent
        self.clear()
        
    def read(self):
        self.setRecieved(
            self.parentRead()
        )
        
    def write(self, val, withOkAnswer=False):
        self.appendSendedLens(
            self.parentWrite(val, withOkAnswer)
        )
        
    def clear(self):
        self.sendedLens = []
        self.recieved = ""
        
    def setRecieved(self, val):
        self.recieved = val
        
    def appendSendedLens(self, val):
        self.sendedLens.append(val)
        
    def doOnStart(self):
        self.clear()
        self.parentDoOnStart()
        
    def run(self):
        recieved = self.recieved
        self.clear()
        self.recieved = recieved
        self.parentRun()