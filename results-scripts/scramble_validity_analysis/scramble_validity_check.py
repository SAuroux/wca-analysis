#!/usr/bin/env python
# coding: utf-8

""" WCA scramble validity check.

This script analyses the Scrambles table of th WCA database for validity and consistency. This currently includes:

1. scrambleId, groupId, isExtra and scrambleNum are within their expected ranges
2. competitionId, eventId and roundTypeId are valid, i.e. within the respective existing sets
3. making sure that scramble is correctly formatted and all moves are valid moves

1. and 3. are done using regular expressions, see: https://docs.python.org/2/library/re.html

The script requires an unpacked WCA database export.
For more information check:
https://www.worldcubeassociation.org/results/misc/export.html

"""

__author__ = "Sébastien Auroux"
__contact__ = "sebastien@auroux.de"

import numpy as np
import re
from collections import defaultdict

# Location of the database export used by the script
scramble_export_file = "db_export/WCA_export_Scrambles.tsv"
# Name of the output file
output_file = "irregular_scrambles.txt"

# defining regular expressions patterns matching the scramble strucutre for each WCA event
# in addition, I am defining simple patterns for the non-scramble columns in the WCA Scrambles table
pattern_dict = {
    '222': '^([RUF][\'2]? ){10}[RUF][\'2]?$',               # 2x2x2 scrambles only have [RUF] moves and are standardized to 11 moves.
    '333': '^([RUFLDB][\'2]? ){12,24}[RUFLDB][\'2]?$',        # requiring 13 or more moves for 3x3x3 does not match the regulations, 
                                                            # but serves as a heuristic here to identify unusually short scrambles.
    '333bf': '^([RUFLDB][\'2]? ){12,24}[RUFLDB][\'2]?( [RUF]w[\'2]?){0,2}$',
    '333fm': '^([RUFLDB][\'2]? ){12,27}[RUFLDB][\'2]?$',
    '333ft': '^([RUFLDB][\'2]? ){12,24}[RUFLDB][\'2]?$',
    '333mbf': '^(([RUFLDB][\'2]? ){12,24}[RUFLDB][\'2]?( [RUF]w[\'2]?){0,2}($|\|))+$',
    '333oh': '^([RUFLDB][\'2]? ){12,24}[RUFLDB][\'2]?$',
    '444': '^([RUFLDB]w?[\'2]? ){37,49}[RUFLDB]w?[\'2]?$',    # requiring 38 or more moves for 4x4x4 does not match the regulations, 
                                                            # but serves as a heuristic here to identify unusually short scrambles.
    '444bf': '^([RUFLDB]w?[\'2]? ){37,49}[RUFLDB]w?[\'2]?( [xyz][\'2]?){0,2}$',
    '555': '^([RUFLDB]w?[\'2]? ){59}[RUFLDB]w?[\'2]?$',     # 5x5x5 scambles consist of 60 random moves.
    '555bf': '^([RUFLDB]w?[\'2]? ){58,59}[RUFLDB]w?[\'2]?( 3[RUF]w[\'2]?){0,2}$',   # 5x5x5 BLD scambles consist of 60 random moves + three layer moves to change orientation.
                                                                                    # These three layer moves might cancel with the last 'normal' move, making it 59 'normal' moves.
    '666': '^(3?[RUFLDB]w?[\'2]? ){79}3?[RUFLDB]w?[\'2]?$', # 6x6x6 scambles consist of 80 random moves.
    '777': '^(3?[RUFLDB]w?[\'2]? ){99}3?[RUFLDB]w?[\'2]?$', # 7x7x7 scambles consist of 100 random moves.
    'clock': '^UR[0-6][+-] DR[0-6][+-] DL[0-6][+-] UL[0-6][+-] U[0-6][+-] R[0-6][+-] D[0-6][+-] L[0-6][+-] ALL[0-6][+-] y2 ' + \
                'U[0-6][+-] R[0-6][+-] D[0-6][+-] L[0-6][+-] ALL[0-6][+-]( UR)?( DR)?( DL)?( UL)?$',
    'minx': '^((R(\+\+|--) D(\+\+|--) ){5}U\'?($|\s)){7}$',                                         # Clock and Megaminx both have a very exact scramble pattern
    'pyram': '^([RULB]\'? ){10}[RULB]\'?( u\'?)?( l\'?)?( r\'?)?( b\'?)?$',                         # Pyraminx scrambles are standardized to 11 moves (+tips).
    'skewb': '^([RULB]\'? ){10}[RULB]\'?$',
    'sq1': '^(\((-[1-5]|[0-6]),(-[1-5]|[0-6])\) \/ ){7,}\((-[1-5]|[0-6]),(-[1-5]|[0-6])\)( \/)?$',  # requiring 8 or more (a,b) moves for SQ1 does not match the regulations, 
                                                                                                    # but serves as a heuristic here to identify unusually short scrambles.
    'scrambleId': '^[0-9]+$',   # Only check if scrambleIds are numeric
    'groupId': '^[AB]?[A-Z]$',  # this regular expression covers up to 78 groups (A - BZ)
    'isExtra': '^[01]$',        # isExtra always has to be either 0 or 1
    'scrambleNum': '^[1-5]$'    # scrambleNum should generally be between 1 and 5 
                                # (Note: this expression will also catch the weird, yet valid case of excessivly many (>5) extra scrambles.)
}
    
patterns = {event: re.compile(pattern_dict[event]) for event in pattern_dict}

with open("db_export/WCA_export_Competitions.tsv", 'r', encoding="utf8") as f:
    competitions = [line.strip().split('\t')[0] for line in f.readlines()[1:]]
with open("db_export/WCA_export_Events.tsv", 'r') as f:
    events = [line.strip().split('\t')[0] for line in f.readlines()[1:]]
with open("db_export/WCA_export_RoundTypes.tsv", 'r') as f:
    roundtypes = [line.strip().split('\t')[0] for line in f.readlines()[1:]]

checklists = {'competitionId': competitions, 'eventId': events, 'roundTypeId': roundtypes}

fin = open(scramble_export_file, 'r')
scramble_columns = fin.readline().strip().split('\t')
fout = open(output_file, 'w')
checked_scrambles = 0
errors_found = defaultdict(int)

while True:
    try:
        tmp = fin.readline().strip().split('\t')
        d = {c: tmp[i] for i, c in enumerate(scramble_columns)}

        invalid = False
        for c in d: # columns in Scramble table
            if c in patterns: # covers scrambleId, groupId, isExtra, scrambleNum
                invalid = (patterns[c].match(d[c]) is None)
            elif c in checklists: # covers competitionId, eventId, roundTypeId
                invalid = (d[c] not in checklists[c])
            else: # only c = 'scramble' remains
                invalid = (patterns[d['eventId']].match(d[c]) is None)
            if invalid:
                output = 'Error for ' + c + ': ' + str(d)
                fout.write(output + '\n')
                print(output)
                errors_found[c] += 1
                break
        checked_scrambles += 1
    except:
        print('Total number of scrambles checked:', checked_scrambles)
        print('Total number of errors found:', sum(errors_found.values()) if len(errors_found) else 0)
        for c in errors_found:
            print(c, 'errors:', errors_found[c])
        break