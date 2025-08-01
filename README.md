<!-- SPDX-License-Identifier: MIT -->
<!-- SPDX-FileCopyrightText: Copyright 2025 Sam Blenny -->
# Fruit Jam Euclidean Sequencer

**DRAFT: WORK IN PROGRESS**

![screenshot of rhythm visualizer](wip-screenshot.png)
(*screenshot of work in progress on rhythm visualizer*)

This is a Euclidean rhythm sequencer for CircuitPython with graphical display
and control input from a USB MIDI controller. The code listens for MIDI CC
(Control Change) messages on the USB host port to control the beats, hits,
shift, and bpm for the rhythm generator.

This code was developed and tested on CircuitPython 10.0.0-beta.0 with a
pre-release rev B Fruit Jam prototype which uses a different I2S pinout from
the current rev D boards. Keep in mind that what's written here may be out of
date by the time CircuitPython 10.0.0 is released and the production revision
of the Fruit Jam board becomes available in the shop.


## Suitable MIDI Controllers

You need a USB MIDI controller that can send four different MIDI CC values from
knobs, sliders, or whatever. I wrote and tested this with an Arturia BeatStep
Pro, but many other commercial or DIY controllers would work. The configuration
section at the top of code.py has four constants (CC_...) that you can set to
adjust the MIDI control number assignments.


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
