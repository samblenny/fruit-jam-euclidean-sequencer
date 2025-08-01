# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2025 Sam Blenny
#
# Related Docs:
# - https://docs.circuitpython.org/projects/tlv320/en/latest/api.html
# - https://learn.adafruit.com/adafruit-tlv320dac3100-i2s-dac/overview
# - https://docs.circuitpython.org/en/latest/docs/environment.html
# - https://docs.circuitpython.org/en/latest/shared-bindings/audiobusio/
# - https://docs.circuitpython.org/en/latest/shared-bindings/audiomixer/
# - https://midi.org/specs
# - https://github.com/todbot/circuitpython-synthio-tricks
# - https://docs.circuitpython.org/en/latest/shared-bindings/bitmaptools/
# - https://docs.circuitpython.org/en/latest/shared-bindings/displayio/
#
from audiobusio import I2SOut
from board import (
    I2C, I2S_BCLK, I2S_DIN, I2S_MCLK, I2S_WS, PERIPH_RESET,
    CKP, CKN, D0P, D0N, D1P, D1N, D2P, D2N
)
import bitmaptools
import displayio
from digitalio import DigitalInOut, Direction, Pull
from displayio import Bitmap, Group, Palette, TileGrid
import framebufferio
import gc
import math
from micropython import const
import os
import picodvi
import supervisor
import synthio
import sys
from terminalio import FONT
import time
from usb.core import USBError, USBTimeoutError
import usb_host
import usb_midi

from adafruit_display_text import bitmap_label
import adafruit_imageload
from adafruit_tlv320 import TLV320DAC3100

from euclidean import gen_rhythm
from sb_usb_midi import find_usb_device, MIDIInputDevice


# DAC and Synthesis parameters
SAMPLE_RATE = const(22050)
CHAN_COUNT  = const(1)
BUFFER_SIZE = const(512)
#==============================================================
# CAUTION! When this is set to True, the headphone jack will
# send a line-level output suitable use with a mixer or powered
# speakers, but that will be _way_ too loud for earbuds. For
# finer control of volume, you can set dac.dac_volume below.
LINE_LEVEL  = const(True)
#==============================================================

# Change this to True if you want more MIDI output on the serial console
DEBUG = const(True)

# Color Theme (16-bit RGB565 colors for RP2350 which zero fills low bits)
CYANISH = const(0x00A8C0)
GREEN   = const(0x00FC00)
WHITE   = const(0xF8FCF8)
BLACK   = const(0x000000)


def init_display(width, height, color_depth):
    # Initialize the picodvi display
    # Video mode compatibility:
    # | Video Mode     | Fruit Jam | Metro RP2350 No PSRAM    |
    # | -------------- | --------- | ------------------------ |
    # | (320, 240,  8) | Yes!      | Yes!                     |
    # | (320, 240, 16) | Yes!      | Yes!                     |
    # | (320, 240, 32) | Yes!      | MemoryError exception :( |
    # | (640, 480,  8) | Yes!      | MemoryError exception :( |
    displayio.release_displays()
    gc.collect()
    fb = picodvi.Framebuffer(width, height, clk_dp=CKP, clk_dn=CKN,
        red_dp=D0P, red_dn=D0N, green_dp=D1P, green_dn=D1N,
        blue_dp=D2P, blue_dn=D2N, color_depth=color_depth)
    display = framebufferio.FramebufferDisplay(fb)
    supervisor.runtime.display = display
    return display

def init_dac_audio_synth(i2c):
    # Configure TLV320 I2S DAC for audio output and make a Synthesizer.
    # - i2c: a reference to board.I2C()
    # - returns tuple: (dac: TLV320DAC3100, audio: I2SOut, synth: Synthesizer)
    #
    # The I2S pinout changed between Fruit Jam board revision B and revision D.
    # The change got committed to CircuitPython between the 10.0.0-alpha.6 and
    # 10.0.0-alpha.7 releases (see commit 9dd53eb). Since I'm developing this
    # on a rev B board, the code checks an environment variable to allow for
    # swapping the pins. If you have a rev B board, you need to add
    # `FRUIT_JAM_BOARD_REV = "B"` in your CIRCUITPY/settings.toml file.
    #
    # You could easily modify this for a Metro RP2350 with a TLV320 DAC
    # breakout board. To do that, first change the `from board import ...` line
    # up top to match the pins you want to use. Then change this function to
    # have an `audio = I2SOut(bit_clock=...)` line for your pinout.
    #
    # 1. Reset DAC (reset is active low)
    rst = DigitalInOut(PERIPH_RESET)
    rst.direction = Direction.OUTPUT
    rst.value = False
    time.sleep(0.1)
    rst.value = True
    time.sleep(0.05)
    # 2. Configure sample rate, bit depth, and output port
    dac = TLV320DAC3100(i2c)
    dac.configure_clocks(sample_rate=SAMPLE_RATE, bit_depth=16)
    dac.speaker_mute = True
    dac.headphone_output = True
    # 3. Set volume for for line-level or headphone level
    print("Initial dac_volume", dac.dac_volume)
    print("Initial headphone_volume", dac.headphone_volume)
    if LINE_LEVEL:
        # This gives a line output level suitable for plugging into a mixer or
        # the AUX input of a powered speaker (THIS IS TOO LOUD FOR HEADPHONES!)
        dac.dac_volume = -30
        dac.headphone_volume = -64
    else:
        # This is a reasonable volume for my cheap JVC Gumy earbuds. They tend
        # to be louder than other headphones, so probably this ought to be a
        # generally safe volume level. For headphones that need a stronger
        # signal, carefully increase dac_volume (closer to 0 is louder).
        dac.dac_volume = -58
        dac.headphone_volume = -64
    print("Current dac_volume", dac.dac_volume)
    print("Current headphone_volume", dac.headphone_volume)
    # 4. Initialize I2S, checking environment variable to control swapping of
    #    the MCLK and WS from their default values (for rev B prototype boards)
    # =====
    # To adapt this for Metro RP2350, this is where you would modify the code
    # with an `audio = I2SOut(...)` line to match the pinout for your DAC. You
    # would also need to change the `from board import ...` line up top.
    # =====
    if os.getenv("FRUIT_JAM_BOARD_REV") == "B":
        print("USING FRUIT JAM REV B BOARD: SWAPPING I2S PINS!")
        audio = I2SOut(bit_clock=I2S_BCLK, word_select=I2S_MCLK, data=I2S_DIN)
    else:
        print("Using default I2S pin definitions (board rev D or newer)")
        audio = I2SOut(bit_clock=I2S_BCLK, word_select=I2S_WS, data=I2S_DIN)
    # 5. Configure synthio patch to generate audio
    vca = synthio.Envelope(
        attack_time=0.005, decay_time=0.005, sustain_level=0.3,
        release_time=0.001, attack_level=0.4
    )
    synth = synthio.Synthesizer(
        sample_rate=SAMPLE_RATE, channel_count=CHAN_COUNT, envelope=vca
    )
    audio.play(synth)
    return (dac, audio, synth)

def elapsed_ms(t1, t2):
    # Calculate elapsed ms between two supervisor.ticks_ms() timestamps.
    #
    # The CircuitPython ticks counter rolls over at 2**29, so this uses a bit
    # mask of (2**29)-1 = 0x3fffffff for the subtraction. If you want to learn
    # more about why doing it this way gives the correct result even when the
    # interval spans a rollover, try reading about "modular arithmetic",
    # "integer overflow", and "two's complement" arithmetic.
    return (t2 - t1) & 0x3fffffff

def key_change(num, up):
    # Handle note on event (up==True) or note off event (up==False)
    pass

def thick_circle(bitmap, x, y, radius, value, stroke_px, fill=None):
    # Draw circle with a thick stroke line by filling the space between two
    # 1px stroke bitmaptools.draw_circle() circles.
    # - bitmap: destination displayio.Bitmap object
    # - x, y, radius, value: same meaning as for bitmaptools.draw_circle()
    # - stroke_px: thickness of stroke in pixels (should be 3 or more)
    # - fill: optional palette index for interior fill color
    #
    radius = max(5, radius)
    stroke_px = max(3, stroke_px)
    inner_radius = radius - (stroke_px // 2)
    outer_radius = inner_radius + stroke_px
    fill_x = x + radius
    bitmaptools.draw_circle(bitmap, x, y, inner_radius, value)
    bitmaptools.draw_circle(bitmap, x, y, outer_radius, value)
    bitmaptools.boundary_fill(bitmap, fill_x, y, value)
    if fill is not None:
        # Optionally fill interior of circle
        bitmaptools.boundary_fill(bitmap, x, y, fill)

class RhythmRing:
    # RythmRing maintains a set of Euclidean rhythm parameters, generates a
    # rhythm pattern when the parameters change, and helps with drawing the
    # rhythm ring visualizer.
    def __init__(
        self, bg, fg, cx, cy, radius,
        beats=8, hits=5, shift=0, bpm=80
    ):
        self.bg = bg          # background bitmap
        self.fg = fg          # foreground bitmap
        self.cx = cx          # ring center coordinate X value
        self.cy = cy          # ring center coordinate Y value
        self.radius = radius  # ring radius
        self.beats = 8
        self.hits = 5
        self.shift = 0
        self.bpm = 80
        self.rhythm = gen_rhythm(beats, hits, shift)

    def adjust(self, beats=0, hits=0, shift=0):
        # Adjust current Euclidean rhythm parameters and regenerate rhythm.
        # Beats value gets clipped to minimum of 1, maximum of 16.
        # Hits  value gets clipped to minimum of 1, maximum of self.beats.
        # Shift value gets clipped to minimum of 1, maximum of self.beats.
        self.beats  = max(1, min(16, self.beats + dbeats))
        self.hits   = max(1, min(self.beats, self.hits + dhits))
        self.shift  = max(0, min(self.beats, self.shift + dshift))
        self.rhythm = gen_rhythm(self.beats, self.hits, self.shift)

    def draw_ring(self, bg_color=0, stroke_color=1):
        # Draw the background ring as a thick-stroked circle
        self.bg.fill(bg_color)
        thick_circle(self.bg, self.cx, self.cy, self.radius,
            value=stroke_color, stroke_px=3)

    def draw_dots(self, stroke_color, hit_fill, rest_fill, transparent):
        # Draw dots on top of the background ring to mark the rhythm.
        # This uses alpha blending and stroke/fill colors to separate the dots
        # from the background ring.
        # - stroke_color: palette index of stroke color
        # - hit_fill: palette index for hit dot fill color
        # - hit_fill: palette index for rest dot fill color
        # - transparent: palette index for transparent areas
        self.fg.fill(transparent)
        rhythm = self.rhythm
        for i in range(len(rhythm)):
            angle = math.radians(360 * i / len(rhythm))
            x = round(self.cx + ((self.radius + 0.5) * math.cos(angle)))
            y = round(self.cy + ((self.radius + 0.5) * math.sin(angle)))
            if rhythm[i] == 'x':
                thick_circle(self.fg, x, y, radius=10,
                    value=stroke_color, stroke_px=3, fill=hit_fill)
            else:
                thick_circle(self.fg, x, y, radius=8,
                    value=stroke_color, stroke_px=4, fill=rest_fill)


def main():

    # Configure display with requested picodvi video mode
    display = init_display(320, 240, 16)
    grp = Group(scale=1)
    display.root_group = grp

    # Make background bitmap and palette (solid color and concentric rings)
    bg_pal = Palette(2)
    bg_pal[0] = CYANISH
    bg_pal[1] = WHITE
    bg = Bitmap(display.width, display.height, len(bg_pal))
    bg_tg = TileGrid(bg, pixel_shader=bg_pal)
    grp.append(bg_tg)

    # Make foreground bitmap and palette (dots for beats)
    fg_pal = Palette(4)
    fg_pal[0] = BLACK   # this gets set to transparent below
    fg_pal[1] = WHITE
    fg_pal[2] = CYANISH
    fg_pal[3] = GREEN
    fg_pal.make_transparent(0)
    fg = Bitmap(display.width, display.height, len(fg_pal))
    fg_tg = TileGrid(fg, pixel_shader=fg_pal)
    grp.append(fg_tg)

    ring = RhythmRing(bg, fg, cx=110, cy=display.height//2, radius=65,
        beats=8, hits=5, shift=0, bpm=80
    )
    ring.draw_ring(bg_color=0, stroke_color=1)
    ring.draw_dots(stroke_color=2, hit_fill=3, rest_fill=1, transparent=0)

    # Set up the audio stuff for a basic synthesizer
    i2c = I2C()
    (dac, audio, synth) = init_dac_audio_synth(i2c)

    # Cache function and object references (MicroPython performance trick)
    fast_wr = sys.stdout.write
    panic = synth.release_all
    press = synth.press
    release = synth.release
    sleep = time.sleep
    ticks_ms = supervisor.ticks_ms
    diff_ms = elapsed_ms
    key = key_change

    # Main loop: scan USB host bus for MIDI device, connect, start event loop.
    # This grabs the first MIDI device it finds. Reset board to re-scan bus.
    while True:
        fast_wr("USB Host: scanning bus...\n")
        gc.collect()
        device_cache = {}
        try:
            # This loop will end as soon as it finds a ScanResult object (r)
            r = None
            while r is None:
                sleep(0.4)
                r = find_usb_device(device_cache)
            # Use ScanResult object (r) to check if USB device descriptor info
            # matches the class/subclass/protocol pattern for a MIDI device. If
            # the device doesn't match, MIDIInputDevice will raise an exception
            # and trigger another iteration through the outer while True loop.
            dev = MIDIInputDevice(r)
            fast_wr(" found MIDI device vid:pid %04X:%04X\n" % (r.vid, r.pid))
            # Collect garbage to hopefully limit heap fragmentation.
            r = None
            device_cache = {}
            gc.collect()
            # MIDI Event Input Loop: Poll for input until USB error.
            #
            # CAUTION: This loop needs to be as efficient as possible. Any
            # extra work here directly adds time to USB latency.
            #
            # This uses the input event generator to prepare an iterator object
            # that we can poll inside the while loop. There's an easier syntax
            # to use this with a for loop, but here we need to de-prioritize
            # USB IO a little in order to share resources with synthio,
            # picodvi, and the sequencer timing loop.
            #
            event_it = dev.input_event_generator()
            if event_it is None:
                continue
            cin = chan = num = val = 0x00
            t1 = t2 = ticks_ms()
            while True:
                # Use elapsed time interval to regulate sequencer timing
                t2 = ticks_ms()
                if diff_ms(t1, t2) > 30:
                    # TODO: implement this
                    pass

                # Poll for a USB MIDI event and begin handling midi packet. The
                # packet (data) should be None or a 4-byte memoryview. The :=
                # syntax is Python's "Walrus operator".
                if (data := next(event_it)) is None:
                    continue

                # data[0] has CN (Cable Number) and CIN (Code Index Number). By
                # discarding CN with `& 0x0f`, we ignore the virtual MIDI port
                # that the messages arrive from. Ignoring CN would be bad for a
                # fancy DAW or synth setup where you needed to route MIDI
                # among multiple devices. But, that doesn't matter here. We do
                # need CIN to distinguish between note on, note off, Control
                # Change (CC), and so on. For the channel, adding 1 gives us
                # human-friendly channel numbers in the range of 1 to 16.
                #
                cin = data[0] & 0x0f
                chan = (data[1] & 0xf) + 1
                num = data[2]
                val = data[3]

                # This decodes MIDI events by comparing constants against bytes
                # from a memoryview. Using a class to do this parsing would add
                # many extra heap allocations and dictionary lookups. That
                # stuff is slow, and we want to go _fast_. For details about
                # the MIDI 1.0 standard, see https://midi.org/specs
                #
                if cin == 0x08 and (21 <= num <= 108):
                    # Note off
                    release(num)
                    key(num, False)
                elif cin == 0x09 and (21 <= num <= 108):
                    # Note on
                    press(num)
                    key(num, True)
                elif cin == 0x0b and num == 123 and val == 0:
                    # CC 123 means stop all notes ("panic")
                    panic()
                    fast_wr('PANIC %d %d %d\n' % (chan, num, val))
                if DEBUG:
                    if cin == 0x08:
                        # Note On
                        fast_wr('Off %d %d %d\n' % (chan, num, val))
                    elif cin == 0x09:
                        # Note Off
                        fast_wr('On  %d %d %d\n' % (chan, num, val))
                    elif cin == 0x0b:
                        # CC control change
                        fast_wr('CC  %d %d %d\n' % (chan, num, val))
                    elif cin == 0x0a:
                        # MPE polyphonic key pressure (aftertouch)
                        fast_wr('MPE %d %d %d\n' % (chan, num, val))
                    elif cin == 0x0d:
                        # CP channel key pressure (aftertouch)
                        fast_wr('CP  %d %d %d\n' % (chan, num, val))
                    elif cin == 0x0e:
                        # PB pitch bend (this can be noisy with a K-Board C)
                        pass
                        #fast_wr('PB  %d %d %d\n' % (chan, num, val))
                    else:
                        # Ignore the rest: SysEx, System Realtime, or whatever
                        pass
        except USBError as e:
            # This sometimes happens when devices are unplugged. Not always.
            print("USBError: '%s' (device unplugged?)" % e)
        except ValueError as e:
            # This can happen if an initialization handshake glitches
            print(e)


main()
