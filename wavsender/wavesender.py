# coding: utf8
#!/usr/bin/env python
import sys, argparse
from threading import Thread
from PyQt4.QtCore import QObject, QThread, pyqtSignal, QTextStream
from PyQt4.QtGui import QApplication, QDialog, QLineEdit, QLabel
from PyQt4.QtNetwork import QTcpServer, QTcpSocket, QHostAddress, QAbstractSocket

from recorder import WaveRecorder
from socketserver import SocketServer


class SomeServer(SocketServer):
    def __init__(self):
        super(SomeServer, self).__init__()
        self.recorder_thread = False

    # Parse the request in order to find, what the client wants to do
    def parseRequest(self):
        d = self.sock.readAll() # read client's request from socket

        # The procedure between dashes describes what command server expects,
        # how is it parsed and what kind of response is given to client.
        # Now for the debug purposes the server behaves as the simplest HTTP server
        # (it can be changed later when the client part is ready)
        # - begin -------------------------------------------------------
        d.truncate(d.indexOf("\r\n"))                            # leave only the first line of request
        d = d.toUpper()                                          # bring request to upper case
        command = d.split(" ")                                   # split the first line of request into list of strings (supposed value in case of proper request: #0="GET", #1="/", #2="HTTP/1.0" (or other versions))
        if command[0] == "GET" and command[1] == "/":            # condition for a proper request ("GET" must be the first word, "/" - the second, or all together: "GET /")
            self.sock.write(command[2])                          # send HTTP version into socket (HTTP/1.0, HTTP/1.1, or whatever)
            self.sock.write(" OK\r\n")                           # complete the first line of response
            self.sock.write("Content-Type: application/ogg\r\n") # another line of response
            self.sock.write("Cache-Control: no-cache\r\n\r\n")   # another line of response
        # - end ---------------------------------------------------------

            self.sock.flush() # stop waiting for data - immediately send the packet with everything, that was put into buffer with "write" method
            window.label_status.setText("Client connected")
            self.recorder_thread = Thread(target=self.doRecord)
            self.recorder_thread.start()
            return 1
        else:
            return -1

    def doRecord(self):
        self.recorder = WaveRecorder(self.sock.socketDescriptor())
        self.recorder.terminationFlag = False
        self.recorder.record()

    # overrides parent class' clientWentOffline method
    def clientWentOffline(self):
        self.recorder.terminationFlag = True
        self.recorder_thread.join()
        self.sock.close()
        window.label_status.setText("Client disconnected")
        self.isWorking = False

class WaveSenderWindow(QDialog):
    def __init__(self, parent=None):
        super(WaveSenderWindow, self).__init__(parent)
        self.setupServer()
        self.setupGui()

    def setupServer(self):
        self.server = SomeServer()
        self.server.ip = args.ip
        self.server.port = args.port
        self.server.startListen()

    def setupGui(self):
        width = 185  # window width
        height = 100 # window height
        title = "Wave Sender" # window title
        self.resize(width, height)
        self.move(app.desktop().availableGeometry().width() / 2 - 250 / 2, app.desktop().availableGeometry().height() / 2 - 150 / 2) # move window to visible desktop center
        self.setWindowTitle(title)

        # input for assigning an IP-address which server listens
        input_ip = QLineEdit(str(self.server.ip), self)
        input_ip.resize(120, input_ip.height())
        input_ip.move(5, 25)

        # input for assigning a port which server listens
        input_port = QLineEdit(str(self.server.port), self)
        input_port.resize(50, input_port.height())
        input_port.move(130, 25)

        # input for assigning a port which server listens
        label_ip = QLabel("IP-address:", self)
        label_ip.move(10, 5)

        # input for assigning a port which server listens
        label_port = QLabel("Port:", self)
        label_port.move(135, 5)

        self.label_status = QLabel("No connection to client", self)
        self.label_status.move(10, 80)

    # perform a proper exit procedure
    def closeEvent(self, evnt):
        super(WaveSenderWindow, self).closeEvent(evnt)
        if self.server.recorder_thread:
            if self.server.recorder_thread.isAlive() == True: # check if recorder thread is running
                self.server.recorder.terminationFlag = True # tell the recorder to stop
                self.server.recorder_thread.join() # wait for recorder to stop

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', dest='ip', action='store', default='0.0.0.0')
    parser.add_argument('-p', '--port', dest='port', action='store', default=999, type=int)
    args = parser.parse_args()
    sys.argv = sys.argv[:1]

    app = QApplication(sys.argv)

    window = WaveSenderWindow()
    window.show()

    app.exec_()
