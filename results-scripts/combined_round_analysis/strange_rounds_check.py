#!/usr/bin/env python
# coding: utf-8

""" WCA strange round check.

This script analyses the WCA database for strange round, which are here defined
as rounds where at least one competitor has fewer results than a strictly worse
placed competitor.

The script requires a WCA database export to be unpacked in <db_export_dir>.
For more information check:
https://www.worldcubeassociation.org/results/misc/export.html

"""

__author__ = "Sébastien Auroux"
__contact__ = "sebastien@auroux.de"

import pandas as pd
import numpy as np

# Location of the database export used by the script
db_export_dir = "db_export"
# Name of the output file
output_file = "strange_rounds.txt"


## data preparation
try:
    if not db_export_dir[-1] == '/':
        db_export_dir += '/'
    results = pd.read_csv(db_export_dir + 'WCA_export_Results.tsv',sep='\t',)
except:
    print("Error: could not load export data from folder " + db_export_dir)

results['zeros'] = sum((results['value'+str(i)]==0) for i in [1,2,3,4,5])
results = results.sort_values(by=['competitionId','eventId','roundTypeId','pos'])
results = results[['competitionId','eventId','roundTypeId','pos','zeros']]
combined_round_types = ["c","d","e","g","h"]
combined_results = results[results.roundTypeId.isin(combined_round_types)]


## analyze for strange rounds

# determine min and max positions for each number of zeros per rounds
min_pos_per_zero = combined_results.groupby(by=['competitionId','eventId','roundTypeId','zeros']).min()
max_pos_per_zero = combined_results.groupby(by=['competitionId','eventId','roundTypeId','zeros']).max()

# merge them!
min_pos_per_zero = min_pos_per_zero.rename(columns={'pos': 'min_pos'})
max_pos_per_zero = max_pos_per_zero.rename(columns={'pos': 'max_pos'})
df = min_pos_per_zero.merge(max_pos_per_zero, left_index=True, right_index=True)
df = df.reset_index()

# merge dataframe on itself to get all possible combinations of zeros and
# min/max positions. Then strange rounds can be identified very easily!

df = df.merge(df, how='inner', on=['competitionId','eventId','roundTypeId'])
strange_index = (df['min_pos_x'] <= df['max_pos_y']) & (df['zeros_x'] > df['zeros_y'])
strange_df = df[strange_index]
strange_df = strange_df[['competitionId','eventId','roundTypeId']].drop_duplicates()
strange_df['year'] = strange_df.apply(lambda x: int(x['competitionId'][-4:]),axis=1)
strange_df = strange_df.sort_values(by=['year','competitionId','eventId','roundTypeId'])

# result output
fout = open(output_file,"w")
fout.write("competitionId,eventId,roundTypeId\n")
for index, row in strange_df.iterrows():
    out = '{0},{1},{2}\n'.format(row['competitionId'],row['eventId'],row['roundTypeId'])
    fout.write(out)
fout.close()
