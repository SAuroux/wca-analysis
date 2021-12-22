#!/usr/bin/env python
# coding: utf-8

""" 
Just a small script analyzing the distribution of Skewb scramble lengths in the WCA database 
(as part of the scramble validity investigation).

"""

__author__ = "Sébastien Auroux"
__contact__ = "sebastien@auroux.de"

import numpy as np
import re
from collections import defaultdict

# Location of the database export used by the script
scramble_export_file = "db_export/WCA_export_Scrambles.tsv"

prog = re.compile('[RULB]\'?')

fin = open(scramble_export_file, 'r')
scramble_columns = fin.readline().strip().split('\t')
skewb_moves = defaultdict(int)
fout = open('skewb_outliers.txt', 'w')

while True:
    try:
        tmp = fin.readline().strip().split('\t')
        d = {c: tmp[i] for i, c in enumerate(scramble_columns)}
        if d['eventId'] != 'skewb': # or d['competitionId'] != 'CubingUSANationals2018':
            continue
        scramble_length = len(prog.findall(d['scramble']))
        skewb_moves[scramble_length] += 1
        if scramble_length != 11:
            fout.write(str(d) + '\n')
    except:
        for m in sorted(list(skewb_moves.keys())):
            print('Number of Skewb scrambles with {} moves: {}'.format(m, skewb_moves[m]))
        break