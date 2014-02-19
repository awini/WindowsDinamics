# coding: utf8
#!/usr/bin/env python
import sys, optparse
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, QThread, pyqtSignal, QTimer, QObject, QDataStream, QByteArray, QIODevice, QCoreApplication
from PyQt4.QtNetwork import QTcpServer, QTcpSocket, QHostAddress, QAbstractSocket
from PyQt4 import uic, QtCore
from PyQt4.QtTest import QTest
from datetime import datetime, timedelta

import codecs

from multiprocessing import Process, Queue
from recorder import WaveRecorder, SEND_BYTES_SIZE
import time
from timewatch import TW
from sendprocesswatch import SendProcessWatch
from datachange import *

SEND_PART_SIZE = 414
    
def toStrList(args):
    for a in args:
        yield str(a)
    
def debug(*args):
    print ' '.join(list(toStrList(args)))

class SocketCycler(object):
    def start(self, count=0):
        debug("start cycles:", count)
        self.lastNum = 0
        self.time = datetime.now()
        if self.sock and self.sock.state()==QAbstractSocket.ConnectedState:
            self.doOnStart()
        self.cycle(count)
        self.doOnStop()
        
    def cycle(self, count):
        i = 0
        while self.sock and self.sock.state()==QAbstractSocket.ConnectedState \
                and (i<count or count==0):
            self.doTime(i)
            self.run()
            print "fin cycle", i
            i+=1
        
    def doTime(self, i):
        tm = datetime.now()
        if tm - self.time >= timedelta(0, 1):
            d = i - self.lastNum
            self.lastNum = i
            self.time = tm
            print "d =", d
            
class MultiProcessSender(object):
    def __init__(self, parent):
        self.parent = parent
        parent.getData = self.getData
        parent.sendLength = self.sendLength
        parent.sendData = self.sendData
        self.parentPrepareRecorder = parent.prepareRecorder
        parent.prepareRecorder = self.prepareRecorder
        self.parentDoOnStop = parent.doOnStop
        parent.doOnStop = self.doOnStop
        
    def getData(self):
        self.parent.data = self.parent.q.get()
        
    def sendLength(self):
        self.parent.write(
            packIntToByteArray(
                len(self.parent.data)
            )
        )
        
    def sendData(self):
        self.write(self.parent.data, True)
        
    def prepareRecorder(self):
        self.parentPrepareRecorder()        
        self.parent.q = Queue()
        self.parent.recorderProcess = Process(target=self.recorder.cycle, args=(self.q,))
        self.parent.recorderProcess.start()
        #print q.get()    # prints "[42, None, 'hello']"
        #self.recorderProcess.join()
        
    def doOnStop(self):
        self.parentDoOnStop()
        if self.parent.recorder:
            self.parent.recorder.stopping = True
            

class WaveSender(SocketCycler):
    def __init__(self, multiprocess=False):
        self.recorder = False
        if multiprocess:
            self.multiProcessSender = MultiProcessSender(self)
        
    def doOnStart(self):
        self.prepareRecorder()
        TW.time_watch(self.read)
        
    def doOnStop(self):
        self.sendFin()
        
    def run(self):
        self.getData()
        TW.time_watch(self.sendLength)
        TW.time_watch(self.sendData)
        
    def prepareRecorder(self):
        if not self.recorder:
            self.recorder = self.recorderInit()
        
    def getData(self):
        TW.time_watch(self.recorder.record)

    def sendLength(self):
        self.write(
            packIntToByteArray(
                len(self.recorder.data)
            )
        )

    def sendData(self):
        self.write(self.recorder.data, True)
            
    def sendFin(self):
        self.write(
            packIntToByteArray(0)
        )
        
    def read(self):
        return self.sock.readAll()
        
    def write(self, val, withOkAnswer=False):
        ln = self.sock.write(val)
        while self.sock.bytesToWrite() > 0:
            print "\twaiting..."
            self.sock.waitForBytesWritten()
        if withOkAnswer:
            self.getOkAnswer()
        return ln
        
    def getOkAnswer(self):
        self.sock.waitForReadyRead()
        d = self.sock.readAll()
        if d=="/d":
            print "send ok!"
            return True
        print "send result:", d
        return False

if __name__=="__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test', dest='test', action='store_true')
    parser.add_argument('-i', '--ip', dest='ip', action='store', default='127.0.0.1')
    parser.add_argument('-p', '--port', dest='port', action='store', default=9999, type=int)
    parser.add_argument('-c', '--cycles', dest='cycles', action='store', default=0, type=int)
    parser.add_argument('-m', '--mulriprocess', dest='mulriprocess', action='store_true', default=False)
    parser.add_argument('-r', '--real_recorder', dest='real_recorder', action='store_true')
    parser.add_argument('-w', '--watch', dest='watch', action='store', default=True, type=int)
    args = parser.parse_args()
    sys.argv = sys.argv[:1]

    if args.test:
        import unittest
        from socketserver import SocketServer

        class SocketWorker(object):
            def __init__(self, parent):
                super(SocketWorker,self).__init__()
                self.parent = parent
                
            def execute(self, sock):
                sock.write("/d")
                while True:
                    ln = self.getLength(sock)
                    if ln == 0:
                        print "fin recieved"
                        break
                    self.readData(sock, ln)
                    self.answerOk(sock)
                    
            def getLength(self, sock):
                sock.waitForReadyRead()
                ln = unpackIntFromByteArray(sock.readAll())
                return ln
                
            def readData(self, sock, ln):
                print "reading", ln
                data = QByteArray()
                while data.length() < ln:
                    sock.waitForReadyRead()
                    bytes = sock.readAll()
                    data += bytes
                    print "recieved", bytes.length(), "sum:", data.length()
                self.parent.data += data
                
            def answerOk(self, sock):
                sock.write("/d")

        class TestServer(SocketServer):
            def __init__(self, parent=None):
                super(TestServer,self).__init__(parent)
                print "TestServer.start"
                self.data = QByteArray()
                self.ip = QHostAddress(args.ip)
                self.port = args.port
                self.socketWorker = SocketWorker(self)

            def __del__(self):
                print "TestServer.finish"
                
        class TestRecorder(object):
            def record(self):
                data = ""
                for a in xrange(0,4140):
                    data += "a"
                self.data = data
                
        class Test1(unittest.TestCase):
            def setUp(self):
                self.workWhileExists = QObject()
                self.ts = TestServer()
                self.ts.ip = args.ip
                self.ts.port = args.port
                self.thread = QThread()
                self.ts.moveToThread(self.thread);
                self.ts.connect(self.thread,QtCore.SIGNAL("started()"),self.ts.startListen)
                self.ts.connect(self.ts,QtCore.SIGNAL("finished()"),self.thread.quit)
                self.ts.connect(self.workWhileExists,QtCore.SIGNAL("destroyed()"),self.ts.stopListen)
                self.thread.start()
                
                QTest.qWait(250)
                
                self.assertEquals(self.ts.listening, True)
                
            def tearDown(self):
                self.sock.close()
                del self.workWhileExists
                self.workWhileExists = False

                QTest.qWait(250)

                self.thread.quit()
                self.assertEquals(self.thread.wait(), True)

            def test_execution(self):
                ws = WaveSender(args.mulriprocess)
                if args.watch == True:
                    ws.sendProcessWatch = SendProcessWatch(ws)
                else:
                    def twm(func):
                        return func()
                    def ptw():
                        pass
                    TW.time_watch = twm
                    TW.print_time_watch = ptw
                if args.real_recorder:
                    ws.recorderInit = WaveRecorder
                else:
                    ws.recorderInit = TestRecorder
                ws.sock = QTcpSocket()
                self.sock = ws.sock
                print "connect to:", args.ip +":"+ str(args.port)
                ws.sock.connectToHost(QHostAddress(args.ip), args.port)
                self.assertEquals(ws.sock.waitForConnected(), True)

                QTest.qWait(250)
                cycles = args.cycles
                if cycles == 0:
                    cycles = 1
                ws.start(cycles)
                
                if args.watch:
                    self.assertEquals(ws.sendProcessWatch.recieved, "/d")
                    self.assertEquals(ws.sendProcessWatch.sendedLens, [4L, SEND_BYTES_SIZE, 4L])
                else:
                    print "-- NO WATCH! --"
                
                TW.print_time_watch()

        app = QCoreApplication(sys.argv)
        unittest.main()
        app.exec_()
    else:
        #app = QCoreApplication(sys.argv)
        ws = WaveSender(args.mulriprocess)
        ws.recorderInit = WaveRecorder
        ws.sock = QTcpSocket()
        while True:
            ws.sock.connectToHost(QHostAddress(args.ip), args.port)
            if ws.sock.waitForConnected():
                print "connected"
                break
        ws.start(args.cycles)
        #app.exec_()
