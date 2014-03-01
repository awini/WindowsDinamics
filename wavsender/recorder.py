"""PyAudio example: Record a few seconds of audio and save to a WAVE file.
Used code from ogg-theora-vorbis version 0.0.1 package (https://pypi.python.org/pypi/ogg-theora-vorbis)"""

import pyaudio
import wave
import random

from PyQt4.QtNetwork import QTcpSocket

from CuOgg import *
from CuVorbis import *

CHUNK = 1024

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
QUALITY = -0.1 # values between -0.1 (bad) to 1.0 (good)

class WaveRecorder(object):
    def __init__(self, sock):
        self.sock = QTcpSocket()
        self.sock.setSocketDescriptor(sock)
        self.data = []
        self.device = None
        self.head = False
        self.p = False
        self.stream = False
        self.i = 0
        self.stopping = False
        self.pp = False
        self.pstream = False

        self.vi = make_vorbis_info()            # struct that stores all the static vorbis bitstream
        self.vc = make_vorbis_comment()         # struct that stores all the user comments
        self.vd = make_vorbis_dsp_state()       # central working state for the packet->PCM decoder
        self.vb = make_vorbis_block()           # local working space for packet->PCM decode

        self.header      = make_ogg_packet()
        self.header_comm = make_ogg_packet()
        self.header_code = make_ogg_packet()
        self.audio_pkt   = make_ogg_packet()

        self.to   = make_ogg_stream_state()
        self.page = make_ogg_page()
        self.terminationFlag = True # this flag is used to signal recorder that it is no longer needed (when the connection is lost)

    def __del__(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pstream:
            # stop stream (4)
            self.pstream.stop_stream()
            self.pstream.close()

        # close PyAudio (5)
        if self.p:
            self.p.terminate()
        if self.pp:
            self.pp.terminate()

    # make the last page in Ogg stream, purging buffer
    def flushFrames(self):
        vorbis_analysis_wrote(self.vd,0)
        while (vorbis_analysis_blockout(self.vd, self.vb) == 1):
            vorbis_analysis(self.vb,self.audio_pkt)
            ogg_stream_packetin(self.to,self.audio_pkt)
        self.savePage()

    def addWaveFrames(self, frames):
        vorbis_encode_wave_frames(self.vd, self.vb, frames, frames.__len__() / (CHANNELS * 2), CHANNELS)
        while (vorbis_analysis_blockout(self.vd, self.vb) == 1):
            vorbis_analysis(self.vb,self.audio_pkt)
            ogg_stream_packetin(self.to,self.audio_pkt)
        self.savePage()
        return 1

    # make initial page of Ogg stream
    def oggStart(self):
        r1 = vorbis_info_init(self.vi)
        r2 = vorbis_encode_init_vbr(self.vi, CHANNELS, RATE, QUALITY)
        r3 = vorbis_encode_setup_init(self.vi)

        r4 = vorbis_comment_init(self.vc)
        r5 = vorbis_analysis_init(self.vd,self.vi)
        r6 = vorbis_block_init(self.vd,self.vb)

        r7 = vorbis_analysis_headerout(self.vd, self.vc, self.header, self.header_comm, self.header_code)

        rnd = int(random.random()*10000)
        ogg_stream_init(self.to,rnd)

        r1 = ogg_stream_packetin(self.to, self.header)
        r2 = ogg_stream_packetin(self.to, self.header_comm)
        r3 = ogg_stream_packetin(self.to, self.header_code)

        self.savePage()

    # purge Vorbis structures (not used yet)
    def clear(self):
        vorbis_analysis_wrote(self.vd,0)
        while (vorbis_analysis_blockout(self.vd, self.vb) == 1):
            vorbis_analysis(self.vb,self.audio_pkt)
            ogg_stream_packetin(self.to,self.audio_pkt)
        ogg_stream_pageout(self.to, self.page)

    # make a (middle) page of Ogg stream - this one contains multimedia data
    def savePage(self):
        n = ogg_stream_pageout(self.to, self.page)
        if n:
            header = page_header(self.page)
            body = page_body(self.page)
            self.sock.write(header) #write Ogg page header to TCP socket
            self.sock.write(body) #write Ogg page body to TCP socket
            self.sock.flush() # stop waiting for data - immediately send TCP packet with everything, that was put into buffer with "write" method
            self.sock.waitForBytesWritten()

    def open(self, dev):
        if not self.p:
            self.p = pyaudio.PyAudio()
        if self.stream:
            return self.stream
        if not self.findDevice(dev):
            return False
        self.stream = self.p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=self.device)
        return self.stream

    def record(self, dev=0):
        stream = self.open(dev)
        if stream:
            self.oggStart() # initialize Ogg stream by writing the first page
            self.readStreamToData(stream)
            return True
        return False

    def findDevice(self, dev):
        count = self.p.get_device_count()
        devices = [None,] + range(count)

        if dev<0 or dev>=len(devices):
            return False

        self.device = devices[dev]
        return True

    def readStreamToData(self, stream):
        while self.terminationFlag == False:
            self.data = stream.read(CHUNK)
            self.addWaveFrames(self.data) # recorded audio frames are passed to Vorbis encoder
        self.clear()
