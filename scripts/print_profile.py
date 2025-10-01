#!/usr/bin/env python3

import pstats
import sys


def main():
    profile_path = sys.argv[1]
    if len(sys.argv) > 2:
        order = sys.argv[2]
    else:
        order = 'cumulative'  # or 'time'

    stats = pstats.Stats(profile_path)
    stats.sort_stats(order)
    stats.print_stats()


main()
