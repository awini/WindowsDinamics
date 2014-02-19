# coding: utf-8
from PyQt4.QtNetwork import QTcpServer, QTcpSocket, QHostAddress, QAbstractSocket
from PyQt4.QtCore import QObject, QThread, pyqtSignal
from PyQt4 import QtCore

class SocketServer(QTcpServer):
    finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super(SocketServer,self).__init__(parent)
        self.sock = False
        self.listening = False

    def startListen(self):
        self.disconnect(self,QtCore.SIGNAL("newConnection()"),self.doConnection)
        self.connect(self,QtCore.SIGNAL("newConnection()"),self.doConnection)
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
        self.sock = sock
        if sock:
            self.socketWorker.execute(sock)
