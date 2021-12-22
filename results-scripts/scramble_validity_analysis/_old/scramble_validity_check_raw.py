#!/usr/bin/env python
# coding: utf-8

""" WCA scramble validity check (raw version).

This script analyses the Scrambles table of th WCA database for validity and consistency. This currently includes:

1. scrambleId, groupId, isExtra and scrambleNum are within their expected ranges
2. competitionId, eventId and roundTypeId are valid, i.e. within the respective existing sets
3. making sure that scramble is correctly formatted and all moves are valid moves

1. and 3. are done using regular expressions, see: https://docs.python.org/2/library/re.html

RAW version: While the 'normal' version of the script is designed for the scramble format of the database export, 
this version is modified to deal with the exact format expected to be present in the database.

The script requires a '\t'-separated custom export of "SELECT * FROM Scrambles" without column enclosures/escapes.

"""

__author__ = "Sébastien Auroux"
__contact__ = "sebastien@auroux.de"

import numpy as np
import re
from collections import defaultdict

# Location of the database export used by the script
scramble_export_file = "Scrambles_raw.tsv"
# Name of the output file
output_file = "irregular_scrambles_raw.txt"

# defining regular expressions patterns matching the scramble strucutre for each WCA event.
# In addition, I am defining simple patterns for the non-scramble columns in the WCA Scrambles table.
pattern_dict = {
    # 2x2x2 scrambles only have [RUF]['2]? moves and are standardized to 11 moves.
    '222': "^([RUF]['2]? ){10}[RUF]['2]?$",
    # requiring 13-25 moves for 3x3x3 serves as a heuristic to identify unusual scrambles.
    '333': "^([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?$",
    '333bf': "^([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?( [RUF]w['2]?){0,2}$",
    '333fm': "^([RUFLDB]['2]? ){12,27}[RUFLDB]['2]?$",
    # '333fm_new': since late 2016, all 333fm scrambles have R' U' F as static pre- and suffix.
    '333fm_new': "^R' U' F ([RUFLDB]['2]? ){12,24}R' U' F$",
    '333ft': "^([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?$",
    # For 333mbf, every 'scramble' field contains multiple scrambles separated by '\n'.
    '333mbf': "^(([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?( [RUF]w['2]?){0,2}\n)+([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?( [RUF]w['2]?){0,2}$",
    '333oh': "^([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?$",
    # requiring 38-50 moves for 4x4x4 serves as a heuristic to identify unusual scrambles.
    '444': "^([RUFLDB]w?['2]? ){37,49}[RUFLDB]w?['2]?$",
    '444bf': "^([RUFLDB]w?['2]? ){37,49}[RUFLDB]w?['2]?( [xyz]['2]?){0,2}$",
    # 5x5x5 scambles consist of  exactly 60 random moves.
    '555': "^([RUFLDB]w?['2]? ){59}[RUFLDB]w?['2]?$",
    # 5x5x5 BLD scambles consist of 60 random moves + three layer moves to change orientation.
    # These three layer moves might cancel with the last 'normal' move, making it 59 'normal' moves.
    '555bf': "^([RUFLDB]w?['2]? ){58,59}[RUFLDB]w?['2]?( 3[RUF]w['2]?){0,2}$",
    # 6x6x6 scambles consist of exactly 80 random moves.
    '666': "^(3?[RUFLDB]w?['2]? ){79}3?[RUFLDB]w?['2]?$",
    # 7x7x7 scambles consist of exactly 100 random moves.
    '777': "^(3?[RUFLDB]w?['2]? ){99}3?[RUFLDB]w?['2]?$",
    # Clock and Megaminx both have very exact scramble patterns
    'clock': "^UR[0-6][\+-] DR[0-6][\+-] DL[0-6][\+-] UL[0-6][\+-] U[0-6][\+-] R[0-6][\+-] D[0-6][\+-] L[0-6][\+-] ALL[0-6][\+-] y2 " + \
                "U[0-6][\+-] R[0-6][\+-] D[0-6][\+-] L[0-6][\+-] ALL[0-6][\+-]( UR)?( DR)?( DL)?( UL)?$",
    'minx': "^((R(\+\+|--) D(\+\+|--) ){5}U'?\n){6}(R(\+\+|--) D(\+\+|--) ){5}U'?$",
    # Pyraminx scrambles are standardized to 11 moves, followed by possible tip rotations in fixed order.
    'pyram': "^([RULB]'? ){10}[RULB]'?( u'?)?( l'?)?( r'?)?( b'?)?$",
    'skewb': "^([RULB]'? ){10}[RULB]'?$",
    # requiring 8-15 (a,b) moves for SQ1 serves as a heuristic to identify unusual scrambles.
    'sq1': "^(\((-[1-5]|[0-6]),(-[1-5]|[0-6])\) \/ ){7,14}\((-[1-5]|[0-6]),(-[1-5]|[0-6])\)( \/)?$",
    # Only check if scrambleIds are numeric
    'scrambleId': "^[0-9]+$",
    # this regular expression for groupId covers up to 78 groups (A - BZ)
    'groupId': "^[AB]?[A-Z]$",
    # isExtra always has to be either 0 or 1
    'isExtra': "^[01]$",
    # scrambleNum should generally be between 1 and 5 
    # (Note: this expression will also catch the weird, yet valid case of excessivly many (>5) extra scrambles.)
    'scrambleNum': "^[1-5]$"
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

# Due to the raw data input, a new line does no longer equal a new table row.
# Therefore, I always look one line ahead until I find the beginning of the next table row.
new_table_row = re.compile("^[1-9][0-9]*\t")
current_line = fin.readline().split('\t')

while True:
    try:   
        d = {c: current_line[i] for i, c in enumerate(scramble_columns)}
        
        while True:
            next_line = fin.readline()
            if next_line.strip() == '':
                # end of file
                break
            if new_table_row.match(next_line) is None:
                # no new table row, append it to the current scramble
                d['scramble'] += next_line
            else: 
                # otherwise, prepare & keep the next line as current_line for the next iteration.
                current_line = next_line.split('\t')
                break

        invalid = False
        for c in d: 
            # go through all columns of the current Scrambles table row
            if c in patterns: 
                # covers scrambleId, groupId, isExtra, scrambleNum
                invalid = (patterns[c].match(d[c]) is None)
            elif c in checklists: 
                # covers competitionId, eventId, roundTypeId
                invalid = (d[c] not in checklists[c])
            else: # only c = 'scramble' remains
                competition_year = int(d['competitionId'][-4:])
                if d['eventId'] == '333fm' and competition_year >= 2017:
                    # catch the special case of 333fm scrambles >= 2017 (see '333fm_new' in pattern_dict)
                    invalid = (patterns['333fm_new'].match(d[c]) is None)
                else:
                    invalid = (patterns[d['eventId']].match(d[c]) is None)

            if invalid:
                output = 'Error for ' + c + ': ' + str(d)
                fout.write(output + '\n')
                print(output)
                errors_found[c] += 1
                break

        checked_scrambles += 1

        if next_line.strip() == '':
            # end of file
            break

    except:
        break

print('Total number of scrambles checked:', checked_scrambles)
print('Total number of errors found:', sum(errors_found.values()) if len(errors_found) else 0)
for c in errors_found:
    print(c, 'errors:', errors_found[c])