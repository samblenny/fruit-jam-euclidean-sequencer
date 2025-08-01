<!-- SPDX-License-Identifier: MIT -->
<!-- SPDX-FileCopyrightText: Copyright 2025 Sam Blenny -->
# Fruit Jam Euclidean Sequencer

**DRAFT: WORK IN PROGRESS**

![screenshot of rhythm visualizer](wip-screenshot.png)
(*screenshot of work in progress on rhythm visualizer*)

This is a Euclidean rhythm sequencer for CircuitPython with graphical display
and control input from a USB MIDI keyboard controller. Rather than using the
keyboard keys to play notes in the usual way, this code uses the keys as
buttons to control sequencer settings.

This code was developed and tested on CircuitPython 10.0.0-beta.0 with a
pre-release rev B Fruit Jam prototype which uses a different I2S pinout from
the current rev D boards. Keep in mind that what's written here may be out of
date by the time CircuitPython 10.0.0 is released and the production revision
of the Fruit Jam board becomes available in the shop.


## Suitable MIDI Controllers

This code is meant to work with one of the commonly available compact two
octave (25-key) USB MIDI keyboard controllers. Larger keyboard controllers
should also work fine. For discussion of the pros and cons of various
controllers, you can check forums like reddit or modwiggler.

Based on my reading of forums, reviews, and manufacturer websites, I made the
list below with some controllers that might be suitable. I've only tried a
couple of these, but I've seen people online say that they like them (others
disagree). Keep in mind that 25 key keyboards have some inherent limitations,
caveat emptor, etc. Anyhow, in alphabetical order...

- Arturia MicroLab mk3
- Korg MicroKEY-25
- Korg NanoKEY2
- Korg NanoKEY Fold
- Korg NanoPAD2
- Muse Kinetics (Keith McMillen) K-Board C


## Board Revision Note

The I2S pinout changed between Fruit Jam board revision B and revision D. The
change got committed to CircuitPython between the 10.0.0-alpha.6 and
10.0.0-alpha.7 releases (see circuitpython
[commit 9dd53eb](https://github.com/adafruit/circuitpython/commit/9dd53eb6c34994dc7ef7e2a4f21dfd7c7d8dbbd9)).

Table of old and new I2S pins definitions:

| I2S Signal | Rev B Pin           | Rev D Pin |
| ---------- | ------------------- | --------- |
| I2S_MCLK   | GPIO27 (rev D WS)   | GPIO25    |
| I2S_BCLK   | GPIO26 (same)       | GPIO26    |
| I2S_WS     | GPIO25 (rev D MCLK) | GPIO27    |
| I2S_DIN    | GPIO24 (same)       | GPIO24    |

Since I'm developing this on a rev B board, the code checks an environment
variable to allow for swapping the pins.  If you have a rev D or later board,
you can ignore the I2S pinout change. **But, if you have a rev B board
(pre-production prototype), you need to add** `FRUIT_JAM_BOARD_REV = "B"` **in
your CIRCUITPY/settings.toml file**. Otherwise, the code won't have any way to
detect that it needs to swap the I2S pins.
