# coding: utf-8
from PyQt4 import QtCore
from PyQt4.QtNetwork import QTcpServer, QTcpSocket, QHostAddress, QAbstractSocket
from PyQt4.QtCore import pyqtSignal

class SocketServer(QTcpServer):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(SocketServer, self).__init__(parent)
        self.sock = False
        self.listening = False
        self.isWorking = False # this flag is set when there is a connection already to prevent >1 connections

    def __del__(self):
        self.stopListen()

    def startListen(self):
        self.disconnect(self, QtCore.SIGNAL("newConnection()"), self.doConnection)
        self.connect(self, QtCore.SIGNAL("newConnection()"), self.doConnection)
        ret = self.listen(QHostAddress(self.ip), int(self.port))
        self.listening = ret
        return ret

    def stopListen(self):
        if self.sock:
            self.sock.close()
        self.close()
        self.finished.emit()

    def doConnection(self):
        sock = self.nextPendingConnection()
        if self.isWorking == False:
            self.sock = sock
            self.isWorking = True
            self.connect(self.sock, QtCore.SIGNAL("disconnected()"), self.clientWentOffline) # signal that fires, when the socket is disconnected
            self.connect(self.sock, QtCore.SIGNAL("readyRead()"), self.parseRequest) # signal that fires, when some data (request) from client is pending on the socket
        else:
            sock.close() # decline any new connection if there is an already existing one

    def clientWentOffline(self):
        self.isWorking = False
