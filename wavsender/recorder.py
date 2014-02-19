"""PyAudio example: Record a few seconds of audio and save to a WAVE file."""

import pyaudio
import wave

#SEND_BYTES_SIZE = 172L
#CHUNK = 32 
SEND_BYTES_SIZE = 4140L
CHUNK = 1024

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 0
WAVE_OUTPUT_FILENAME = "output.wav"

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
            self.readStreamToData(stream)
            self.appendHeadToData()
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
        else:
            frames = []
            for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                self.data = stream.read(CHUNK)
                frames.append(self.data)
            self.data = b''.join(frames)
        #print("* done recording")
        
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
        
    #=========================================================

    def play(self):
        """PyAudio Example: Play a wave file."""

        #wf = wave.open(WAVE_OUTPUT_FILENAME, 'rb')

        if not self.pp:
            # instantiate PyAudio (1)
            self.pp = pyaudio.PyAudio()

            # open stream (2)
            self.pstream = self.pp.open(format=self.pp.get_format_from_width(self.sample_width), #p.get_format_from_width(wf.getsampwidth()),
                            channels=CHANNELS, #wf.getnchannels(),
                            rate=RATE, #wf.getframerate(),
                            output=True)

        # read data
        '''
        data = wf.readframes(CHUNK)

        # play stream (3)
        while data != '':
            stream.write(data)
            data = wf.readframes(CHUNK)
        '''
        pre_data = self.data
        data = pre_data[:CHUNK]
        pre_data = pre_data[CHUNK:]
        while len(data)>0:
            data = pre_data[:CHUNK]
            pre_data = pre_data[CHUNK:]
            self.pstream.write(data)

        
