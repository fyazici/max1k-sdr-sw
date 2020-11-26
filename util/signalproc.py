#!/usr/bin/env python
# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
from scipy.io import wavfile

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("rawrecord")
parser.add_argument("tunefreq")
args = parser.parse_args()

#iq = np.load(args.rawrecord)["iq"]
raw = np.load(args.rawrecord)["raw"]

print("loaded")

#print(np.mean(raw[0]), np.mean(raw[1]))

#plt.figure(1), plt.plot(raw[0])

N = raw.shape[1]
Fs = 250000
T = float(N) / Fs
iq = (raw[1]-np.mean(raw[1])) + 1j * (raw[0]-np.mean(raw[0]))
#iq_f = np.fft.fft(iq)
#freqs = np.fft.fftfreq(N, 1.0/Fs)
fbase = 1406250
print("count: ", N)

def waterfall(iq, fs):
    plt.specgram(iq, NFFT=1024, Fs=fs, cmap="jet")
    plt.show()

#waterfall(iq, Fs)
#exit(1)

#plt.figure(2), plt.plot(freqs + fbase, 20*np.log10(np.abs(iq_f)/N)), plt.show()

if args.tunefreq[-1] == "k":
    ftune = int(args.tunefreq[:-1]) * 1000
elif args.tunefreq[-1] == "m":
    ftune = int(args.tunefreq[:-1]) * 1000000
else:
    ftune = int(args.tunefreq)
fcorr = -9
fdelta = ftune - fbase + fcorr


print("before mix")

#t = np.linspace(0, T, N)
#iqmix = np.exp(-2j*np.pi*fdelta*t) * iq

# mix_iq_signal(iq, N, Fs, fdelta)
mix_sig = np.exp(-2j * np.pi * fdelta * np.arange(0, N) / Fs)
iq *= mix_sig

print("after mix")

Qdecimate = 32
Fsdown = int(Fs/Qdecimate + 0.5)
Ndown = int(N/Qdecimate + 0.5)
iq = signal.decimate(iq, Qdecimate, ftype="fir")
iqdown = iq
#iqdown = iqdown - np.mean(iqdown)
#freqs_down = np.fft.fftfreq(Ndown, 1.0/Fsdown)
tdown = np.linspace(0, T, Ndown)


#iqdownmixed_f = np.fft.fft(iqdown)
#plt.figure(3), plt.plot(freqs_down, 20*np.log10(np.abs(iqdownmixed_f)/Ndown)), plt.show()


audio_data = np.abs(iqdown[100:])
#plt.figure(4), plt.plot(tdown[100:], audio_data), plt.show()

# stop low freq noise due to osc shifts
f_low = 50
w = signal.firwin(63, 2*f_low/Fsdown, pass_zero=False)
audio_data = signal.lfilter(w, 1.0, audio_data)

#plt.figure(5), plt.plot(tdown[100:], audio_data_h), plt.show()

ll, ul = np.min(audio_data), np.max(audio_data)


audio_data = audio_data * 2**15 / (ul-ll)
wavfile.write("audio{}.wav".format(ftune), int(Fsdown), audio_data.astype(np.int16))

