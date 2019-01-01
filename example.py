#!/usr/bin/env python3

import matplotlib.pyplot as plt
import arbgen


def main():
    # create 3 waveform channels
    arb = arbgen.Arbgen(channels=3, pre_equalize=False, equalization_taps=7)

    # define output sample rate (Samples/second)
    sample_rate = 100e6
    # number of cycles of waveforms to output
    cycles = 1

    # define a 400 ns Gaussian-edged pulse wih 100 ns transitions
    arb.channel(0)
    arb.setValue(0)
    arb.delay(200e-9)
    arb.posPulse(shape='Gaussian', rise_time=100e-9, fall_time=100e-9,
                 width=400e-9, amplitude=1)
    arb.delay(200e-9)

    # define a square 20 ns pulse
    arb.channel(1)
    arb.setValue(0.1)
    arb.delay(300e-9)
    arb.posPulse(shape='square', rise_time=100e-9, fall_time=100e-9,
                 width=20e-9, amplitude=1)
    arb.delay(200e-9)

    # define a sine wave of 2x the period defined by chanels 0 and 1
    arb.channel(2)
    arb.sine(frequency=2*(sample_rate*arb.find_period()-1) /
             (sample_rate*arb.find_period())/arb.find_period(),
             phase=0, amplitude=0.5, offset=0.5)

    # save sample
    arb.save(filename='chan0.dat',
             channel=0, sample_rate=sample_rate, cycles=cycles)
    arb.save(filename='chan1.dat',
             channel=1, sample_rate=sample_rate, cycles=cycles)
    arb.save(filename='chan2.dat',
             channel=2, sample_rate=sample_rate, cycles=cycles)

    # plot waveforms
    f, t = arb.digitize(channel=0, sample_rate=sample_rate)
    plt.subplot(311)
    plt.step(1e9*t, f)
    plt.ylabel('Chan 0')
    f, t = arb.digitize(channel=1, sample_rate=sample_rate)
    plt.subplot(312)
    plt.step(1e9*t, f)
    plt.ylabel('Chan 1')
    f, t = arb.digitize(channel=2, sample_rate=sample_rate)
    plt.subplot(313)
    plt.step(1e9*t, f)
    plt.ylabel('Chan 2')
    plt.xlabel('Time (ns)')
    plt.show()


if __name__ == '__main__':
    main()
