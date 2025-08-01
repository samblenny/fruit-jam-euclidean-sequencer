# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2025 Sam Blenny
#
# This generates Euclidean rhythm patterns using Bjorklund's algorithm as
# described in [1].
#
# References:
# [1] Godfried T. Toussaint. The Euclidean algorithm generates traditional
# musical rhythms. In Proceedings of BRIDGES: Mathematical Connections in Art,
# Music and Science, Banff, Canada, July 31 - August 3 2005.
# http://archive.bridgesmathart.org/2005/bridges2005-47.html


def gen_rhythm(beats, hits, shift=0, debug=False):
    # Wrapper function for recursive algorithm to generate Euclidean rhythm

    # 1. Initialize lists: group1 starts with hits, group2 starts with rests
    rests = beats - hits
    group1 = ["x"] * hits
    group2 = ["."] * rests

    # 2. Define a recursive inner function for evenly distributing items from
    #    group2 into group1. Initially, group1 has hits (pulses) and group2 has
    #    rests (gap intervals between pulses). But, it gets more complicated
    #    than that. In general, group2 holds some kind of remainder that needs
    #    to get put into group1 on the next pass of the algorithm.
    def recurse(group1, group2):
        len1 = len(group1)
        len2 = len(group2)
        if debug:
            print(' %s  %s' % (group1, group2))
        if len1 == 0:
            # Base Case: group1 was initially empty (no hits)
            return ''.join(group2)
        elif len2 == 0:
            # Base Case: group2 was initially empty (no rests)
            return ''.join(group1)
        elif len2 == len1:
            # Base Case: group lengths match, so each group2 item can be moved
            # to the end of a group1 item in one pass with no leftovers
            for i in range(len2):
                group1[i] = group1[i] + group2[i]
            if debug:
                print(' %s' % group1)
            return ''.join(group1)
        elif len2 <= len1:
            # Recursive Case: group2 is shorter, so moving each group2 item to
            # the end of a group1 item leaves a remainder of short items at
            # the end of group1. So, after the first pass, we need to split
            # group1 and make another recursive call to distribute the short
            # items evenly.
            for i in range(len2):
                group1[i] = group1[i] + group2[i]
            # Suppose group1 has ['x..', 'x..', 'x.'] at this point. The slices
            # below would set group1 to ['x..', 'x..'] and group2 to ['x.'].
            group2 = group1[len2:]
            group1 = group1[:len2]
            return recurse(group1, group2)
        else:
            # Recursive Case: group2 is longer, so there will be a remainder
            # after we move one group2 item to the end of each group1 item. To
            # handle leftover group2 items, we call this function again.
            for i in range(len1):
                group1[i] = group1[i] + group2[i]
            group2 = group2[len1:]
            return recurse(group1, group2)

    # 3. Now we're back in the wrapper function. This is where the recursive
    #    chain of function calls begins. We make the first call to recurse()
    #    using the initial list values defined above.
    if shift > 0:
        # Shift was requested, so rotate the rhythm to start on different beat
        r = recurse(group1, group2)
        shift = shift % beats
        return r[shift:] + r[:shift]
    else:
        # No shift
        return recurse(group1, group2)


# This stuff at the end is so you can use regular Python on a full size
# computer to trace through each step of the the recursive algorithm and see
# how it works. You can run this in a terminal with `python3 euclidean.py`.
if __name__ == "__main__":
    # Trace each step of recursion for a range of beats/hits combinations
    for beats in range(3, 16 + 1):
        for hits in range(1, beats + 1):
            print(f"=== {beats}/{hits} ===")
            r = gen_rhythm(beats, hits, debug=True)
    print()
    # Do it again, but this time only show the final result
    for beats in range(3, 16 + 1):
        for hits in range(1, beats + 1):
            tag = f"{beats}/{hits}"
            print(f"{tag:5s} ", gen_rhythm(beats, hits, shift=5))
