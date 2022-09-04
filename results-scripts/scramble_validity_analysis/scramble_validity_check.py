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

import datetime
import pathlib
import re

from collections import defaultdict

# Location and filenames of the database export used by the script
DB_EXPORT_DIR = pathlib.Path("../_wca_db_export")
DB_COMPETITIONS_TSV = "WCA_export_Competitions.tsv"
DB_EVENTS_TSV = "WCA_export_Events.tsv"
DB_ROUNDS_TSV = "WCA_export_RoundTypes.tsv"
DB_SCRAMBLES_TSV = "WCA_export_Scrambles.tsv"

# Name of the output file
OUTPUT_TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
OUTPUT_FILE = "irregular_scrambles_{}.txt".format(OUTPUT_TIMESTAMP)

# global parameter to limit what years are being checked by the script (allow to only check for new violations)
MIN_COMPETITION_YEAR = 2020

# defining regular expressions patterns matching the scramble structure for each WCA event.
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
    # 333mbf is a difficult case, since every 'scramble' field contains multiple scrambles separated by '\n'.
    # In the database export, '\n' is replaced by '|'. Unfortunately, '\r\n' (the Windows line break) is replaced
    # by ' |', which would cause every scramble ever edited from a Windows-PC to be shown as error when requiring '|'.
    # Therefore, the regular expression below allows for both '|' and ' |' as separators between scrambles.
    '333mbf': "^(([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?( [RUF]w['2]?){0,2} ?($|\|)){2,}$",
    '333oh': "^([RUFLDB]['2]? ){12,24}[RUFLDB]['2]?$",
    # requiring 38-50 moves for 4x4x4 serves as a heuristic to identify unusual scrambles.
    '444': "^([RUFLDB]w?['2]? ){37,49}[RUFLDB]w?['2]?$",
    '444bf': "^([RUFLDB]w?['2]? ){37,49}[RUFLDB]w?['2]?( [xyz]['2]?){0,2}$",
    # 5x5x5 scrambles consist of  exactly 60 random moves.
    '555': "^([RUFLDB]w?['2]? ){59}[RUFLDB]w?['2]?$",
    # 5x5x5 BLD scrambles consist of 60 random moves + three layer moves to change orientation.
    # These three layer moves might cancel with the last 'normal' move, making it 59 'normal' moves.
    '555bf': "^([RUFLDB]w?['2]? ){58,59}[RUFLDB]w?['2]?( 3[RUF]w['2]?){0,2}$",
    # 6x6x6 scrambles consist of exactly 80 random moves.
    '666': "^(3?[RUFLDB]w?['2]? ){79}3?[RUFLDB]w?['2]?$",
    # 7x7x7 scrambles consist of exactly 100 random moves.
    '777': "^(3?[RUFLDB]w?['2]? ){99}3?[RUFLDB]w?['2]?$",
    # Clock and Megaminx both have very exact scramble patterns
    'clock': ("^UR[0-6][\+-] DR[0-6][\+-] DL[0-6][\+-] UL[0-6][\+-] "
              "U[0-6][\+-] R[0-6][\+-] D[0-6][\+-] L[0-6][\+-] ALL[0-6][\+-] y2 "
              "U[0-6][\+-] R[0-6][\+-] D[0-6][\+-] L[0-6][\+-] ALL[0-6][\+-]( UR)?( DR)?( DL)?( UL)?$"),
    'minx': "^((R(\+\+|--) D(\+\+|--) ){5}U'?($|\s)){7}$",
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
    # (Note: this expression will also catch the weird, yet valid case of excessively many (>5) extra scrambles.)
    'scrambleNum': "^[1-5]$"
}
    
patterns = {event: re.compile(pattern_dict[event]) for event in pattern_dict}

with open(DB_EXPORT_DIR / DB_COMPETITIONS_TSV, 'r', encoding="utf8") as f:
    competitions = [line.strip().split('\t')[0] for line in f.readlines()[1:]]
with open(DB_EXPORT_DIR / DB_EVENTS_TSV, 'r') as f:
    events = [line.strip().split('\t')[0] for line in f.readlines()[1:]]
with open(DB_EXPORT_DIR / DB_ROUNDS_TSV, 'r') as f:
    round_types = [line.strip().split('\t')[0] for line in f.readlines()[1:]]

checklists = {'competitionId': competitions, 'eventId': events, 'roundTypeId': round_types}

f_in = open(DB_EXPORT_DIR / DB_SCRAMBLES_TSV, 'r')
scramble_columns = f_in.readline().strip().split('\t')
f_out = open(OUTPUT_FILE, 'w')
checked_scrambles = 0
errors_found = defaultdict(int)

while True:
    try:
        current_line = f_in.readline().strip().split('\t')
        d = {c: current_line[i] for i, c in enumerate(scramble_columns)}
        competition_year = int(d['competitionId'][-4:])

        if competition_year < MIN_COMPETITION_YEAR:
            continue

        invalid = False
        for c in d: 
            # go through all columns of the current Scrambles table row
            if c in patterns: 
                # covers scrambleId, groupId, isExtra, scrambleNum
                invalid = (patterns[c].match(d[c]) is None)
            elif c in checklists: 
                # covers competitionId, eventId, roundTypeId
                invalid = (d[c] not in checklists[c])
            else:  # only c = 'scramble' remains
                if d['eventId'] == '333fm' and competition_year >= 2017:
                    # catch the special case of 333fm scrambles >= 2017 (see '333fm_new' in pattern_dict)
                    invalid = (patterns['333fm_new'].match(d[c]) is None)
                else:
                    invalid = (patterns[d['eventId']].match(d[c]) is None)

            if invalid:
                output = 'Error for ' + c + ': ' + str(d)
                f_out.write(output + '\n')
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
