# coding: utf-8
from PyQt4.QtCore import QByteArray, QIODevice, QDataStream

def packIntToByteArray(num):
    ba = QByteArray()
    stream = QDataStream(ba, QIODevice.WriteOnly)
    stream.writeInt32(num)
    return ba
    
def unpackIntFromByteArray(ba):
    stream = QDataStream(ba, QIODevice.ReadOnly)
    return stream.readInt32()
    