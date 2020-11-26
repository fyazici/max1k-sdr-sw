import threading
import time
import numpy as np
import queue
from PacketDecoder import PacketDecoder
import sys
import scipy.signal
import sounddevice
import matplotlib.pyplot as plt
import itertools
import subprocess

class RadioSink:
    def __init__(self, in_stream):
        self.in_stream = in_stream
        self.packet_q = queue.Queue()
        self.sink_thread = threading.Thread(target=self.sink_worker)
        self.stop_flag = threading.Event()
    
    def start(self):
        self.sink_thread.start()
    
    def join(self):
        self.sink_thread.join()
    
    def stop(self):
        self.stop_flag.set()

    def iterator(self):
        while True:
            packet = self.packet_q.get()
            if packet is None:
                return None
            yield packet

    def sink_worker(self):
        synced = False
        while not self.stop_flag.is_set():
            if not synced:
                while not self.stop_flag.is_set():
                    b = self.in_stream.read(1)
                    if b == b"\x00":
                        break
                synced = True
            else:
                buf = bytearray(self.in_stream.read(256))
                ubuf = PacketDecoder.byte_unstuff(buf)
                if ubuf:
                    packet = PacketDecoder.decode_samples(ubuf)
                    self.packet_q.put(packet)
                else:
                    synced = False
        self.packet_q.put(None)


def packet_merger(packet_seq, packet_count):
    buffer = np.zeros((2, packet_count * 84), dtype=np.uint16)
    packet_index = 0
    for packet in packet_seq:
        if packet is None:
            return None
        buffer[:, (84 * packet_index):(84 * (packet_index + 1))] = packet
        packet_index += 1
        if packet_index == packet_count:
            yield buffer.astype(np.float32)
            packet_index = 0
            buffer = np.zeros((2, packet_count * 84), dtype=np.uint16)


def sample_type_converter(sample_iq_seq):
    z = np.zeros(84000)
    prev_q = 0
    for iq in sample_iq_seq:
        if iq is None:
            return None
        print(np.mean(iq[0]), np.std(iq[0]), np.mean(iq[1]), np.std(iq[1]))
        i, q = iq[0] - np.mean(iq[0]), iq[1] - np.mean(iq[1])
        z[1:] = i[:-1] / 2 + i[1:] / 2
        z[0] = prev_q / 2 + i[0] / 2
        prev_q = i[-1]
        yield z + 1j * q

def sample_spectrum_plotter(sample_seq, fs):
    fig = plt.figure()
    plt.show(block=False)
    for samples in sample_seq:
        plt.clf()
        #plt.specgram(samples, NFFT=len(samples)//32, Fs=fs, cmap="jet")
        #plt.xlim([-10000, 10000])
        #plt.ylim([-40, 30])
        f = np.fft.fft(samples, n=2**12)
        ff = np.fft.fftfreq(2**12, 1.0/fs)
        plt.plot(ff + actual_freq, 20*np.log10(np.abs(f)/(2**12)))
        #plt.plot(np.real(samples[0:50]))
        #plt.plot(np.imag(samples[0:50]))
        fig.canvas.draw_idle()
        fig.canvas.start_event_loop(0.001)
        yield samples

actual_freq = 1406250
fdelta = 1413000 - 1406250

def sample_mixer(sample_seq, fs):
    global fdelta
    phase = 1+0j
    for samples in sample_seq:
        qp = np.exp(-2j * np.pi * fdelta / fs)
        q = phase * np.exp(-2j * np.pi * fdelta * np.arange(0, 84 * 1000) / fs)
        if samples is None:
            return None
        samples *= q
        phase = q[-1] * qp
        yield samples
        

def sample_real_valued(sample_seq):
    for samples in sample_seq:
        if samples is None:
            return None
        yield np.abs(samples)

def sample_decimator(sample_seq, q):
    for samples in sample_seq:
        if samples is None:
            return None
        yield scipy.signal.decimate(samples, q, ftype="fir")

def am_audio_filter(sample_seq, f_low, f_high, fs):
    sos = scipy.signal.butter(13, [f_low, f_high], btype="bandpass", output="sos", fs=fs)
    zstate = scipy.signal.sosfilt_zi(sos)
    for samples in sample_seq:
        if samples is None:
            return None
        output, zstate = scipy.signal.sosfilt(sos, samples, zi=zstate)
        yield output

def audio_sink(sample_seq, fs):
    q = queue.Queue()

    def audio_callback(outdata, frames, time, status):
        if not q.empty():
            outdata[:] = q.get_nowait()
    
    stream = sounddevice.OutputStream(samplerate=10000, blocksize=3360, dtype="float32", callback=audio_callback, channels=2)

    # prefill buffer
    for samples in itertools.islice(sample_seq, 4):
        ll, ul = np.min(samples), np.max(samples)
        s = samples * 0.5 / (ul - ll + 1)
        q.put(s.reshape(-1, 1))

    with stream:
        for samples in sample_seq:
            if samples is None:
                break
            ll, ul = np.min(samples), np.max(samples)
            s = samples * 0.5 / (ul - ll + 1)
            q.put(s.reshape(-1, 1))

if __name__ == "__main__":
    serial_pipe = subprocess.Popen(
        ["python3", "SerialPipe.py", "/dev/ttyUSB0", "12000000"], 
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    sink = RadioSink(serial_pipe.stdout)
    packet_source = sink.iterator()
    merged_packets = packet_merger(packet_source, 1000)
    complex_samples_ = sample_type_converter(merged_packets)
    complex_samples = sample_spectrum_plotter(complex_samples_, 250000)
    complex_mixed_samples = sample_mixer(complex_samples, 250000)
    #complex_mixed_samples = sample_spectrum_plotter(complex_mixed_samples_, 250000)
    real_mixed_samples = sample_real_valued(complex_mixed_samples)
    #real_mixed_samples = sample_spectrum_plotter(real_mixed_samples_, 250000)
    baseband_samples = sample_decimator(real_mixed_samples, 25)
    #baseband_samples = sample_spectrum_plotter(baseband_samples_, 10000)
    audio_band_samples = am_audio_filter(baseband_samples, 60, 4500, 10000)

    sink.start()

    t = threading.Thread(target=audio_sink, args=(audio_band_samples, 10000))
    t.start()

    counter_freq = 180000000
    counter_width = 32

    try:
        while True:
            target_freq = int(input("New Frequency: "))
            counter_reload = int(counter_freq / (target_freq) / 4) + 1
            #actual_freq_1 = counter_freq / counter_reload / 4
            #actual_freq_2 = counter_freq / (counter_reload + 1) / 4
            #if abs(target_freq - actual_freq_2) < abs(target_freq - actual_freq_1):
            #    counter_reload += 1
            actual_freq = counter_freq / counter_reload / 4
            fdelta = target_freq - actual_freq
            print("actual lo freq:", actual_freq, "delta:", fdelta)
            serial_pipe.stdin.write(b"\xFE")
            serial_pipe.stdin.write((counter_reload - 1).to_bytes((counter_width // 8), byteorder="big"))
            serial_pipe.stdin.flush()
    except EOFError as ex:
        sink.stop()

    sink.join()
    t.join()
    
    serial_pipe.stdin.write(b"\xFF")
    serial_pipe.stdin.flush()
    serial_pipe.stdout.read()
    serial_pipe.wait()