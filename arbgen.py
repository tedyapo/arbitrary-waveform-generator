#!/usr/bin/env python3
""" generate samples for arbitrary waveforms """

import numpy as np
from scipy import special
from scipy import signal


class Arbgen:
    """ generate samples for arbitrary waveforms """
    class __Value:
        def __init__(self, value):
            self.value = value

        def digitize(self, t, offset):
            return self.value * (t >= offset), offset

    class __Delay:
        def __init__(self, length):
            self.length = length

        def digitize(self, t, offset):
            return 0 * t, offset + self.length

    class __Edge:
        def __init__(self, polarity, shape, rise_time, amplitude,
                     low_thresh, ctr_thresh, high_thresh):
            self.shape = shape
            self.rise_time = rise_time
            self.amplitude = amplitude * polarity
            self.low_thresh = low_thresh
            self.ctr_thresh = ctr_thresh
            self.high_thresh = high_thresh

        def __digitize_gaussian(self, t, offset):
            t_low = special.ndtri(self.low_thresh)
            t_ctr = special.ndtri(self.ctr_thresh)
            t_high = special.ndtri(self.high_thresh)
            k = (t_high - t_low)/self.rise_time
            f = self.amplitude*special.ndtr(k*(t-offset)+t_ctr)
            return f, offset

        def __digitize_exponential(self, t, offset):
            t_low = -np.log(1 - self.low_thresh)
            t_ctr = -np.log(1 - self.ctr_thresh)
            t_high = -np.log(1 - self.high_thresh)
            k = (t_high - t_low)/self.rise_time
            f = self.amplitude*np.maximum(0, (1-np.exp(-k*(t-offset)-t_ctr)))
            return f, offset

        def __digitize_ramp(self, t, offset):
            return (self.amplitude *
                    (np.clip((t - offset +
                              self.ctr_thresh*self.rise_time) /
                             self.rise_time,
                             0, 1))), offset

        def __digitize_square(self, t, offset):
            return self.amplitude*(t >= offset), offset

        def digitize(self, t, offset):
            if self.shape == 'Gaussian':
                return self.__digitize_gaussian(t, offset)
            elif self.shape == 'exponential':
                return self.__digitize_eponential(t, offset)
            elif self.shape == 'ramp':
                return self.__digitize_ramp(t, offset)
            elif self.shape == 'square':
                return self.__digitize_square(t, offset)

    class __Sine:
        def __init__(self, frequency, phase, amplitude, offset):
            self.frequency = frequency
            self.phase = phase
            self.amplitude = amplitude
            self.offset = offset

        def digitize(self, t, offset):
            return ((self.offset +
                     self.amplitude*np.sin(2 * np.pi *
                                           self.frequency*t + self.phase)),
                    offset)

    class __Cosine:
        def __init__(self, frequency, phase, amplitude, offset):
            self.frequency = frequency
            self.phase = phase
            self.amplitude = amplitude
            self.offset = offset

        def digitize(self, t, offset):
            return ((self.offset +
                     self.amplitude*np.cos(2 * np.pi *
                                           self.frequency*t + self.phase)),
                    offset)

    class __Function:
        def __init__(self, function):
            self.function = function

        def digitize(self, t, offset):
            return self.function(t, offset)

    def __init__(self, channels=1, initial_value=0, defined_period=0,
                 pre_equalize=False, equalization_taps=31):
        self.channels = [[] for x in range(channels)]
        self.current_channel = 0
        self.initial_value = initial_value
        self.defined_period = defined_period
        self.pre_equalize = pre_equalize
        self.equalization_taps = equalization_taps

    def channel(self, channel):
        self.current_channel = channel
        return self

    def __DAC_pre_eq_gen(self):
        bands = np.linspace(0, 1, self.equalization_taps)[1:-1]
        bands = np.repeat(bands, 2)
        bands = np.append(bands, 1)
        bands = np.insert(bands, 0, 0)
        desired = 1./np.sqrt(np.sinc(bands/2.))
        b = signal.firls(self.equalization_taps, bands, desired)
        return b

    def __append(self, primitive):
        self.channels[self.current_channel].append(primitive)

    def rc_to_rise_time(self, rc, low_thresh=0.1, high_thresh=0.9):
        return rc*(-np.log(1-high_thresh) + np.log(1-low_thresh))

    def setValue(self, value):
        self.__append(self.__Value(value))

    def delay(self, length):
        self.__append(self.__Delay(length))

    def function(self, function):
        self.__append(self.__Function(function))

    def sine(self, frequency, phase, amplitude, offset):
        self.__append(self.__Sine(frequency, phase, amplitude, offset))

    def cosine(self, frequency, phase, amplitude, offset):
        self.__append(self.__Cosine(frequency, phase, amplitude, offset))

    def posEdge(self, shape, rise_time, amplitude,
                low_thresh=0.1, ctr_thresh=0.5, high_thresh=0.9):
        self.__append(self.__Edge(+1, shape, rise_time,
                                  amplitude,
                                  low_thresh, ctr_thresh,
                                  high_thresh))

    def negEdge(self, shape, rise_time, amplitude,
                low_thresh=0.1, ctr_thresh=0.5, high_thresh=0.9):
        self.__append(self.__Edge(-1, shape, rise_time,
                                  amplitude,
                                  low_thresh, ctr_thresh,
                                  high_thresh))

    def posPulse(self, shape, rise_time, fall_time, width, amplitude,
                 low_thresh=0.1, ctr_thresh=0.5, high_thresh=0.9):
        self.__append(self.__Edge(+1, shape, rise_time, amplitude,
                                  low_thresh, ctr_thresh, high_thresh))
        self.__append(self.__Delay(width))
        self.__append(self.__Edge(-1, shape, fall_time, amplitude,
                                  low_thresh, ctr_thresh, high_thresh))

    def find_period(self):
        if self.defined_period:
            return self.defined_period
        period = 0
        for channel in self.channels:
            t = np.array([0])
            offset = 0
            for primitive in channel:
                f, offset = primitive.digitize(t, offset)
            period = max(period, offset)
        return period

    def digitize(self, sample_rate, channel=None, cycles=1):
        if channel is None:
            channel = self.current_channel
        period = self.find_period()
        n_samples = int(period*sample_rate)
        t = np.linspace(0, period, n_samples)
        f = np.zeros(t.size)
        offset = 0
        for p in self.channels[channel]:
            fp, offset = p.digitize(t, offset)
            f += fp
        tc = np.array([])
        offset = 0
        for i in range(0, cycles+2):
            tc = np.append(tc, t + offset)
            offset = tc[-1]
        f = np.tile(f, cycles+2)
        if self.pre_equalize:
            return (signal.filtfilt(self.__DAC_pre_eq_gen(), 1, f)
                    [n_samples:(1+cycles)*n_samples],
                    tc[n_samples:(1+cycles)*n_samples] -
                    period)
        else:
            return (f[n_samples:(1+cycles)*n_samples],
                    tc[n_samples:(1+cycles)*n_samples] -
                    period)

    def save(self, filename, sample_rate, channel=None, cycles=1,
             pre_equalize=False):
        f, t = self.digitize(sample_rate, channel, cycles)
        outfile = open(filename, 'wb')
        outfile.write(bytes(np.round(np.clip(f, 0, 1)*255)
                            .astype('uint8')+128))
        outfile.close()
