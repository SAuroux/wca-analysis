#!/usr/bin/env python
# coding: utf-8

""" WCA record consistency check.

This script analyses the WCA database for record consistency. This includes:

1) clear record errors: records that are certainly either wrongly assigned or
missing. (Note: Due to a rule change in 2013 (regulation 9i2), some pre-2013
results classified as clear error might indeed not be errors.)
2) conflicting records: records whose state is questionable because of
other results happening on overlapping calendar dates. Such results need to
be assessed individually to determine the correct outcome.

The script requires a WCA database export to be unpacked in <db_export_dir>.
For more information check:
https://www.worldcubeassociation.org/results/misc/export.html

Developer's note: Since this script is not meant for regular public use, I have
mostly omitted exception handling.

"""

__author__ = "Sébastien Auroux"
__contact__ = "sebastien@auroux.de"

import pandas as pd
import numpy as np
import sys
import datetime
import pdb
#pdb.set_trace()

# Location of the database export used by the script
db_export_dir = "db_export"
# Name of the output file
output_file = "record_consistency_output.tsv"

# read in all required data from WCA database export
try:
    if not db_export_dir[-1] == '/':
        db_export_dir += '/'
    # using separate dataframes for single and average results for more individual data wrangling
    results = pd.read_csv(db_export_dir + 'WCA_export_Results.tsv', \
        delimiter='\t', usecols=['competitionId','eventId','roundTypeId', \
        'personId','personCountryId','best','average', \
        'regionalSingleRecord','regionalAverageRecord']).fillna('')
    competition_data = pd.read_csv(db_export_dir + \
        'WCA_export_Competitions.tsv', delimiter='\t', \
        usecols=['id','year','month','day','endMonth','endDay'])
    countries = pd.read_csv(db_export_dir + \
        'WCA_export_Countries.tsv', delimiter='\t', \
        usecols=['id','continentId'])
except:
    print("Error: could not load export data from folder " + db_export_dir)

### data preparation

# defining record markers
WR_marker = 'WR'
CR_marker = {'_Africa': 'AfR', '_Asia': 'AsR', '_Europe': 'ER', \
    '_North America': 'NAR', '_Oceania': 'OcR', '_South America': 'SAR'}
NR_marker = 'NR'

def get_marker(region):
    if region == 'World':
        return WR_marker
    elif region in CR_marker:
        return CR_marker[region]
    else:
        return NR_marker

# define round ranks to be able to compare different round types
round_rank = {'0': 0, '1': 1, '2': 2, '3': 3, 'b': 3, 'c': 4, 'd': 1, 'e': 2, 'f': 4, 'g': 3, 'h': 0}

def get_round_rank(roundtype):
    return round_rank[roundtype]

results['roundrank'] = results['roundTypeId'].apply(get_round_rank)

def get_start_date(row):
    year, month, day = row['year'], row['month'], row['day']
    return datetime.date(year,month,day).strftime('%Y-%m-%d')

def get_end_date(row):
    year,month,day,endmonth,endday = (row['year'],row['month'],row['day'],row['endMonth'],row['endDay'])
    if int(endmonth) < int(month): # turn of the year
        return datetime.date(year+1,endmonth,endday).strftime('%Y-%m-%d')
    else:
        return datetime.date(year,endmonth,endday).strftime('%Y-%m-%d')

# excluse 333mbo since these records can not be properly analyzed (many better results were changed to 333mbf)
results = results[results['eventId'] != '333mbo']

competition_data['startdate'] = competition_data.apply(get_start_date,axis=1)
competition_data['enddate'] = competition_data.apply(get_end_date,axis=1)
competition_dates = competition_data[['id','startdate','enddate']].rename(columns={'id': 'competitionId'})

results = results.merge(competition_dates,how='inner',on='competitionId')

countries.rename(columns={'id': 'personCountryId'}, inplace=True)
results = results.merge(countries,how='inner',on='personCountryId')
competition_dates.set_index(keys='competitionId', inplace=True)

### record consistency check
# this is done one event at a time, first for single, then for average

def format_result(value,event):
    """ formats results for output """

    # do not format FMC and MultiBlind for simplicity
    if event in ['333fm','333mbf']:
        return str(value)
    else:
        out = str(datetime.timedelta(milliseconds=10*int(value)))
        # str(timedelta) produces either 6 (microseconds > 0) or no digits
        # (microseconds = 0). Make it uniformly two.
        if out[-7] == '.':
            out = out[:-4]
        else:
            out += '.00'
        # remove leading zeros
        for bad_padding in ['0:00:0', '0:00:', '0:0', '0']:
            rel_index = len(bad_padding)
            if out[:rel_index] == bad_padding:
                out = out[rel_index:]

        return out

def record_consistency_check(event,kind):
    """ checks for consistency of all records of a certain event and a
    certainly kind(single or average) and stores all clear/possible errors.
    The function loops through all competitions ordered by startdate,
    compared result to all records that happened strictly before a given
    competition and eventually stores clear errors and possible errors. """

    print("Calculating records for " + event + " " + kind + " records...")

    if kind == 'single':
        df = results[(results['eventId'] == event) & (results['best'] > 0)]
        df = df.sort_values(by=['startdate','competitionId','roundrank','best'])
    elif kind == 'average':
        df = results[(results['eventId'] == event) & (results['average'] > 0)]
        df = df.sort_values(by=['startdate','competitionId','roundrank','average'])
    else:
        print("Error: Invalid record kind for consistency check: " + str(kind))
        exit(1)

    all_records, old_records, min_per_round = [], {}, {}
    active_countries, active_continents = [], []
    old_startdate = np.min(df['startdate'])
    competitions = list(df['competitionId'].unique())

    def check_record(region,value,competition,round):
        """ helper function to check whether or not a given result could
        potentially be a record """

        # min_per_round is already set at this point, so if there was already a
        # better results for this competition,round,region then return False
        if min_per_round[(competition,round,region)] < value:
            return False

        # also check preceeding rounds for better results
        for roundtype in round_rank:
            if (competition,roundtype,region) in min_per_round.keys() \
            and round_rank[roundtype] < round_rank[round] \
            and min_per_round[(competition,roundtype,region)] < value:
                return False

        # otherwise compare against old records
        if not region in old_records:
            return True
        elif value <= old_records[region]:
            return True
        else:
            return False

    def update_old_records(sdate):
        """ helper function to update dict of records happened strictly
        before the given startdate """

        past_records = pd.DataFrame(all_records)
        past_records = past_records[past_records['enddate'] < sdate]

        tmp = past_records['value']
        if len(tmp) > 0:
            old_records['World'] = tmp.min()
        for con in active_continents:
            tmp = past_records[past_records['continent'] == con]['value']
            if len(tmp) > 0:
                old_records[con] = tmp.min()
        for nat in active_countries:
            tmp = past_records[past_records['country'] == nat]['value']
            if len(tmp) > 0:
                old_records[nat] = tmp.min()

    def output_tuple(r):
        """ helper function to create output tuples """

        err = (r['personId'], r['country'], r['continent'], event, kind, \
            format_result(r['value'],event), r['competitionId'], r['startdate'], \
            r['enddate'], r['round'], r['marker'], r['computed'])

        return err

    # first compute all possible records
    for index, row in df.iterrows():
        person = row['personId']
        competition = row['competitionId']
        round = row['roundTypeId']
        country = row['personCountryId']
        continent = row['continentId']
        if kind == 'single':
            value = int(row['best'])
            marker = row['regionalSingleRecord']
        else:
            value = int(row['average'])
            marker = row['regionalAverageRecord']
        sdate = row['startdate']
        edate = row['enddate']

        if sdate != old_startdate:
            update_old_records(sdate)

        # for each competition, round and country, it is only needed to checks
        # the best result. Remember that results are ordered ascendingly.
        # Also set values for continent and world when not yet present
        if not (competition,round,country) in min_per_round:
            min_per_round[(competition,round,country)] = value
            if not (competition,round,continent) in min_per_round:
                min_per_round[(competition,round,continent)] = value
                if not (competition,round,'World') in min_per_round:
                    min_per_round[(competition,round,'World')] = value

        # store active countries and continents for more efficient execution
        if not country in active_countries:
            active_countries.append(country)
            if not continent in active_continents:
                active_continents.append(continent)

        record_data = {'personId': person, 'competitionId': competition, 'round': round, \
            'value': value, 'country': country, 'continent': continent, 'startdate': sdate, \
            'enddate': edate, 'value': value, 'marker': marker, 'computed': ''}

        # check for record potential in order: national, continental, global
        if check_record(country,value,competition,round):
            record_data['computed'] = NR_marker
            record_data['region'] = country
            if check_record(continent,value,competition,round):
                record_data['computed'] = CR_marker[continent]
                record_data['region'] = continent
                if check_record('World',value,competition,round):
                    record_data['computed'] = WR_marker
                    record_data['region'] = 'World'
            all_records.append(record_data)

        # if no record was computed but a record is currently stored, this is a
        # clear error. Adding these here to clear_errors is convenient.
        if record_data['computed'] == '' and marker != '':
            err = output_tuple(record_data)
            clear_errors.append(err)

        old_startdate = sdate

    # then analyze records for (possible) errors, looking at each distinct set
    # of overlapping competitions

    print("Analyzing records for " + event + " " + kind + " records...")

    record_df = pd.DataFrame(all_records)
    overlapping_comp_sets = []
    record_competitions = list(record_df['competitionId'].unique())

    def store_errors(records):
        """ helper function to store clear errors and possible errors
        (conflicting records) """

        if len(records) == 1:
            r = records.iloc[0]
            if r['marker'] != r['computed']:
                err = output_tuple(r)
                # avoid duplicates (could appear in multiple overlapping sets)
                if not err in clear_errors:
                    clear_errors.append(err)
        elif len(records) > 1:
            err = []
            for i, r in records.iterrows():
                err.append(output_tuple(r))
            # avoid duplicates (could appear in multiple overlapping sets)
            if not err in possible_errors:
                possible_errors.append(err)

    def evaluate_record_output(records,comp):
        """ helper function to further assess possible errors """

        if len(records) == 0:
            return None
        elif len(records) > 1 or comp == records['competitionId'].iloc[0]:
            # there are either multiple results or this is already the affected
            # competition's overlapping set (no doublecheck needed)
            store_errors(records)
        else:
            # test if the current overlapping set equals the competition's
            # overlapping set. If not, do nothing: if it is a clear error, it
            # will reappear and handled within a different overlapping set.
            tsdate, tedate = records['startdate'].iloc[0], records['enddate'].iloc[0]
            test_set = list(record_df[(tsdate <= record_df['enddate']) & (record_df['startdate'] <= tedate)].competitionId.unique())
            if test_set == overlapping_comps:
                store_errors(records)

    for comp in record_competitions:
        sdate, edate = competition_dates.loc[comp]['startdate'], competition_dates.loc[comp]['enddate']
        overlapping_comps = list(record_df[(sdate <= record_df['enddate']) & (record_df['startdate'] <= edate)].competitionId.unique())
        if overlapping_comps in overlapping_comp_sets:
            continue
        else:
            overlapping_comp_sets.append(overlapping_comps)

        # now check for world, continental and national records
        # for all record types, a single record among overlapping competitions
        # where the current marker does not equal the computed marker corresponds
        # to a clear error. However, this requires doublechecking for the affected
        # competition's overlapping set.
        # Meanwhile, multiple records with the same region are given out to
        # check for possible errors.

        # world records
        curr_records = record_df[record_df['competitionId'].isin(overlapping_comps)]
        curr_records = curr_records[curr_records['computed'] == WR_marker]
        evaluate_record_output(curr_records,comp)

        # continental records
        ov_con_records = record_df[record_df['competitionId'].isin(overlapping_comps)]
        ov_con_records = ov_con_records[ov_con_records['computed'] != NR_marker]
        curr_continents = list(ov_con_records['continent'].unique())
        for con in curr_continents:
            curr_records = ov_con_records[ov_con_records['continent'] == con]
            if (curr_records['computed'].isin(list(CR_marker.values()))).sum() > 0:
                # (otherwise this would have been caught above, prevent repetition)
                evaluate_record_output(curr_records,comp)

        # national records
        ov_nat_records = record_df[record_df['competitionId'].isin(overlapping_comps)]
        curr_countries = list(ov_nat_records['country'].unique())
        for nat in curr_countries:
            curr_records = ov_nat_records[ov_nat_records['country'] == nat]
            if (curr_records['computed'] == NR_marker).sum() > 0:
                # (otherwise this would have been caught above, prevent repetition)
                evaluate_record_output(curr_records,comp)


# create lists of events, initialize error lists to store results
single_events = results[results['best'] > 0].eventId.unique()
average_events = results[results['average'] > 0].eventId.unique()
clear_errors, possible_errors = [], []


# main loop for checking all records
# first check single_events for single records
for event in single_events:
    record_consistency_check(event,'single')
# then check average_events for average records
for event in average_events:
    record_consistency_check(event,'average')


# result output

def format_output_tuple(t):
    """ helper function to format output tuples """

    return '{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}\t{9}\t{10}\t{11}\n'.format(*t)

with open(output_file,"w") as fout:
    # column headers
    fout.write('WCAID\tCountry\tContinent\tevent\tS/A\tResults\tCompetition\tStart Date\tEnd Date\tRound\tStored\tComputed\n\n')
    fout.write('Clear errors: {}\n\n'.format(len(clear_errors)))
    for err in clear_errors:
        out = format_output_tuple(err)
        fout.write(str(out)+'\n')
    fout.write('\nPossible errors: {}\n\n'.format(len(possible_errors)))
    for err in possible_errors:
        out = ''
        for r in err:
            out += format_output_tuple(r)
        fout.write(str(out)+'\n')
