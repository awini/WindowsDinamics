"""PyAudio example: Record a few seconds of audio and save to a WAVE file.
Used code from ogg-theora-vorbis version 0.0.1 package (https://pypi.python.org/pypi/ogg-theora-vorbis)"""

import pyaudio
import wave
import random

from CuOgg import *
from CuVorbis import *

#SEND_BYTES_SIZE = 172L
#CHUNK = 32
SEND_BYTES_SIZE = 4140L
CHUNK = 1024

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 2 # 2 seconds for debug purposes. Originally: 0
WAVE_OUTPUT_FILENAME = "output.ogg"

class WaveRecorder(object):
    def __init__(self):
        self.data = []
        self.device = None
        self.head = False
        self.p = False
        self.stream = False
        self.i = 0
        self.q = False
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
        self.fout = open(WAVE_OUTPUT_FILENAME, "wb")

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
        quality = -0.1 # values between -0.1 (bad) to 1.0 (good)
        r1 = vorbis_info_init(self.vi)
        r2 = vorbis_encode_init_vbr(self.vi, CHANNELS, RATE, quality)
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
        vorbis_block_clear(self.vb)
        vorbis_dsp_clear(self.vd)
        vorbis_comment_clear(self.vc)
        vorbis_info_clear(self.vi)

    # make a (middle) page of Ogg stream - this one contains multimedia data
    def savePage(self):
        n = ogg_stream_pageout(self.to, self.page)
        if n:
            header = page_header(self.page)
            body = page_body(self.page)
            self.fout.write(header)
            self.fout.write(body)

    def cycle(self, q=False):
        self.q = q
        while not self.stopping:
            self.record()

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
        #print("* recording")
        return self.stream

    def record(self, dev=0):
        stream = self.open(dev)
        if stream:
            self.oggStart() # initialize Ogg stream by writing the first page
            self.readStreamToData(stream)
            self.fout.close()
            #self.appendHeadToData() # -- we don't use wave files and don't need this anymore
            if self.q:
                self.q.put(self.data)
            #self.play()
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
        if RECORD_SECONDS <= 0:
            self.data = stream.read(CHUNK)
            self.addWaveFrames(self.data) # not sure if it works, because the whole program does not work for me with RECORD_SECONDS = 0 # recorded audio frames are passed to Vorbis encoder
        else:
            frames = []
            for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                self.data = stream.read(CHUNK)
                #frames.append(self.data) # -- we don't use wave files and don't need this anymore
                self.addWaveFrames(self.data) # recorded audio frames are passed to Vorbis encoder
            #self.data = b''.join(frames) # -- we don't use wave files and don't need this anymore
        #print("* done recording")

# -- we don't use wave files and don't need this anymore (and also "self.play" procedure)
"""
    def appendHeadToData(self):
        if self.head:
            self.data = self.head + self.data
        else:
            ln1 = len(self.data)
            self.saveStreamDataToWaveFile()
            self.loadFullDataFromFile()
            ln2 = len(self.data)
            head_len = ln2-ln1
            self.head = self.data[:head_len]
            #print "head len:", head_len, len(self.head)

    def saveStreamDataToWaveFile(self):
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        self.sample_width = self.p.get_sample_size(FORMAT)
        wf.setsampwidth(self.sample_width)
        wf.setframerate(RATE)
        wf.writeframes(self.data)
        wf.close()

    def loadFullDataFromFile(self):
        f = open(WAVE_OUTPUT_FILENAME, 'rb')
        self.data = f.read()
        f.close()
        #print "start_file:", fdata
"""
