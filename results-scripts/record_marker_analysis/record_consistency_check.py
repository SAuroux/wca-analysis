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

import datetime
import numpy as np
import pandas as pd

# global variables

# Location of the database export used by the script
DB_EXPORT_DIR = "db_export"
if not DB_EXPORT_DIR[-1] == '/':
    DB_EXPORT_DIR += '/'
# Name of the output file
OUTPUT_FILE = "record_consistency_output_{}.tsv".format(datetime.datetime.now().strftime("%Y%m%d"))

# defining record markers
WR_MARKER = 'WR'
CR_MARKER = {'_Africa': 'AfR', '_Asia': 'AsR', '_Europe': 'ER', '_North America': 'NAR',
             '_Oceania': 'OcR', '_South America': 'SAR'}
NR_MARKER = 'NR'

# define round ranks to be able to compare different round types
ROUND_RANKS = {'0': 0, '1': 1, '2': 2, '3': 3, 'b': 3, 'c': 4, 'd': 1, 'e': 2, 'f': 4, 'g': 3, 'h': 0}


# helper functions

def get_marker(region):
    if region == 'World':
        return WR_MARKER
    elif region in CR_MARKER:
        return CR_MARKER[region]
    else:
        return NR_MARKER


def get_round_rank(round_type):
    return ROUND_RANKS[round_type]


def get_start_date(row):
    year, month, day = row['year'], row['month'], row['day']
    return datetime.date(year, month, day).strftime('%Y-%m-%d')


def get_end_date(row):
    year, month, day, end_month, end_day = (row['year'], row['month'], row['day'], row['endMonth'], row['endDay'])
    if int(end_month) < int(month):  # turn of the year
        return datetime.date(year + 1, end_month, end_day).strftime('%Y-%m-%d')
    else:
        return datetime.date(year, end_month, end_day).strftime('%Y-%m-%d')


def format_result(value, event_id):
    """ formats results for output """

    # do not format FMC and MultiBlind for simplicity
    if event_id in ['333fm', '333mbf']:
        return str(value)
    else:
        out = str(datetime.timedelta(milliseconds=10 * int(value)))
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


def check_record(min_per_round, old_records, region, value, competition, round_id):
    """ helper function to check whether or not a given result could potentially be a record """

    # min_per_round (best result per round) is already known at this point, so if there was already a
    # better results for this competition, round, region then return False
    if min_per_round[(competition, round_id, region)] < value:
        return False

    # also check preceding rounds for better results
    for round_type in ROUND_RANKS:
        if (competition, round_type, region) in min_per_round.keys() \
                and ROUND_RANKS[round_type] < ROUND_RANKS[round_id] \
                and min_per_round[(competition, round_type, region)] < value:
            return False

    # otherwise compare against old records
    return region not in old_records or value <= old_records[region]


def update_old_records(all_records, old_records, active_continents, active_countries, start_date):
    """ helper function to update dict of records happened strictly before the given start_date """

    past_records = pd.DataFrame(all_records)
    past_records = past_records[past_records['end_date'] < start_date]

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

    return old_records


def store_errors(records, event_id, kind):
    """ helper function to store clear errors and possible errors (conflicting records) """

    if len(records) == 1:
        r = records.iloc[0]
        if r['marker'] != r['computed']:
            err = output_tuple(r, event_id, kind)
            # avoid duplicates (could appear in multiple overlapping sets)
            if err not in clear_errors:
                clear_errors.append(err)
    elif len(records) > 1:
        err = []
        for i, r in records.iterrows():
            err.append(output_tuple(r, event_id, kind))
        # avoid duplicates (could appear in multiple overlapping sets)
        if err not in possible_errors:
            possible_errors.append(err)


def evaluate_record_output(records, comp, event_id, kind, record_df, overlapping_comps):
    """ helper function to further assess possible errors """

    if len(records) == 0:
        return None
    elif len(records) > 1 or comp == records['competitionId'].iloc[0]:
        # there are either multiple results or this is already the affected
        # competition's overlapping set (no double-check needed)
        store_errors(records, event_id, kind)
    else:
        # test if the current overlapping set equals the competition's
        # overlapping set. If not, do nothing: if it is a clear error, it
        # will reappear and handled within a different overlapping set.
        ts_date, te_date = records['start_date'].iloc[0], records['end_date'].iloc[0]
        test_set = list(
            record_df[
                (ts_date <= record_df['end_date']) & (record_df['start_date'] <= te_date)].competitionId.unique())
        if test_set == overlapping_comps:
            store_errors(records, event_id, kind)


def output_tuple(row, event_id, kind):
    """ helper function to create output tuples """
    return (row['personId'], row['country'], row['continent'], event_id, kind, format_result(row['value'], event_id),
            row['competitionId'], row['start_date'], row['end_date'], row['round'], row['marker'], row['computed'])


def format_output_tuple(t):
    """ helper function to format output tuples """
    return (11 * '{}\t' + '{}\n').format(*t)


def record_consistency_check(df, competition_dates, event_id, kind):
    """ checks for consistency of all records of a certain event and a
    certainly kind(single or average) and stores all clear/possible errors.
    The function loops through all competitions ordered by start_date,
    compared result to all records that happened strictly before a given
    competition and eventually stores clear errors and possible errors. """

    print("Calculating records for " + event_id + " " + kind + " records...")

    if kind == 'single':
        df = df[(df['eventId'] == event_id) & (df['best'] > 0)]
        df = df.sort_values(by=['start_date', 'competitionId', 'round_rank', 'best'])
    elif kind == 'average':
        df = df[(df['eventId'] == event_id) & (df['average'] > 0)]
        df = df.sort_values(by=['start_date', 'competitionId', 'round_rank', 'average'])
    else:
        print("Error: Invalid record kind for consistency check: " + str(kind))
        exit(1)

    all_records, old_records, min_per_round = [], {}, {}
    active_countries, active_continents = [], []
    old_start_date = np.min(df['start_date'])

    # first compute all possible records
    for index, row in df.iterrows():
        person = row['personId']
        competition = row['competitionId']
        round_id = row['roundTypeId']
        country = row['personCountryId']
        continent = row['continentId']
        if kind == 'single':
            value = int(row['best'])
            marker = row['regionalSingleRecord']
        else:
            value = int(row['average'])
            marker = row['regionalAverageRecord']
        s_date = row['start_date']
        e_date = row['end_date']

        if s_date != old_start_date:
            old_records = update_old_records(all_records, old_records, active_continents, active_countries, s_date)

        # for each competition, round and country, it is only needed to checks
        # the best result. Remember that results are ordered in ascending order.
        # Also set values for continent and world when not yet present
        if not (competition, round_id, country) in min_per_round:
            min_per_round[(competition, round_id, country)] = value
            if not (competition, round_id, continent) in min_per_round:
                min_per_round[(competition, round_id, continent)] = value
                if not (competition, round_id, 'World') in min_per_round:
                    min_per_round[(competition, round_id, 'World')] = value

        # store active countries and continents for more efficient execution
        if country not in active_countries:
            active_countries.append(country)
            if continent not in active_continents:
                active_continents.append(continent)

        record_data = {'personId': person, 'competitionId': competition, 'round': round_id, 'value': value,
                       'country': country, 'continent': continent, 'start_date': s_date, 'end_date': e_date,
                       'marker': marker, 'computed': ''}

        # check for record potential in order: national, continental, global
        if check_record(min_per_round, old_records, country, value, competition, round_id):
            record_data['computed'] = NR_MARKER
            record_data['region'] = country
            if check_record(min_per_round, old_records, continent, value, competition, round_id):
                record_data['computed'] = CR_MARKER[continent]
                record_data['region'] = continent
                if check_record(min_per_round, old_records, 'World', value, competition, round_id):
                    record_data['computed'] = WR_MARKER
                    record_data['region'] = 'World'
            all_records.append(record_data)

        # if no record was computed but a record is currently stored, this is a
        # clear error. Adding these here to clear_errors is convenient.
        if record_data['computed'] == '' and marker != '':
            err = output_tuple(record_data, event_id, kind)
            clear_errors.append(err)

        old_start_date = s_date

    # then analyze records for (possible) errors, looking at each distinct set
    # of overlapping competitions

    print("Analyzing records for " + event_id + " " + kind + " records...")

    record_df = pd.DataFrame(all_records)
    overlapping_comp_sets = []
    record_competitions = list(record_df['competitionId'].unique())

    for comp in record_competitions:
        s_date, e_date = competition_dates.loc[comp]['start_date'], competition_dates.loc[comp]['end_date']
        overlapping_comps = list(
            record_df[(s_date <= record_df['end_date']) & (record_df['start_date'] <= e_date)].competitionId.unique())
        if overlapping_comps in overlapping_comp_sets:
            continue
        else:
            overlapping_comp_sets.append(overlapping_comps)

        # now check for world, continental and national records
        # for all record types, a single record among overlapping competitions
        # where the current marker does not equal the computed marker corresponds
        # to a clear error. However, this requires double-checking for the affected
        # competition's overlapping set.
        # Meanwhile, multiple records with the same region are given out to
        # check for possible errors.

        # world records
        curr_records = record_df[record_df['competitionId'].isin(overlapping_comps)]
        curr_records = curr_records[curr_records['computed'] == WR_MARKER]
        evaluate_record_output(curr_records, comp, event_id, kind, record_df, overlapping_comps)

        # continental records
        ov_con_records = record_df[record_df['competitionId'].isin(overlapping_comps)]
        ov_con_records = ov_con_records[ov_con_records['computed'] != NR_MARKER]
        curr_continents = list(ov_con_records['continent'].unique())
        for con in curr_continents:
            curr_records = ov_con_records[ov_con_records['continent'] == con]
            if (curr_records['computed'].isin(list(CR_MARKER.values()))).sum() > 0:
                # (otherwise this would have been caught above, prevent repetition)
                evaluate_record_output(curr_records, comp, event_id, kind, record_df, overlapping_comps)

        # national records
        ov_nat_records = record_df[record_df['competitionId'].isin(overlapping_comps)]
        curr_countries = list(ov_nat_records['country'].unique())
        for nat in curr_countries:
            curr_records = ov_nat_records[ov_nat_records['country'] == nat]
            if (curr_records['computed'] == NR_MARKER).sum() > 0:
                # (otherwise this would have been caught above, prevent repetition)
                evaluate_record_output(curr_records, comp, event_id, kind, record_df, overlapping_comps)


if __name__ == '__main__':
    # read in and prepare all required data from WCA database export
    # results data
    results = pd.read_csv(DB_EXPORT_DIR + 'WCA_export_Results.tsv', delimiter='\t',
                          usecols=['competitionId', 'eventId', 'roundTypeId', 'personId', 'personCountryId', 'best',
                                   'average', 'regionalSingleRecord', 'regionalAverageRecord']).fillna('')
    results['round_rank'] = results['roundTypeId'].apply(get_round_rank)
    # exclude 333mbo since these records cannot be properly analyzed (many better results were changed to 333mbf)
    results = results[results['eventId'] != '333mbo']

    # competition data
    competition_data = pd.read_csv(DB_EXPORT_DIR + 'WCA_export_Competitions.tsv', delimiter='\t',
                                   usecols=['id', 'year', 'month', 'day', 'endMonth', 'endDay'])
    competition_data['start_date'] = competition_data.apply(get_start_date, axis=1)
    competition_data['end_date'] = competition_data.apply(get_end_date, axis=1)
    comp_dates = competition_data[['id', 'start_date', 'end_date']].rename(columns={'id': 'competitionId'})
    results = results.merge(comp_dates, how='inner', on='competitionId')
    comp_dates.set_index(keys='competitionId', inplace=True)

    # country data
    countries = pd.read_csv(DB_EXPORT_DIR + 'WCA_export_Countries.tsv', delimiter='\t', usecols=['id', 'continentId'])
    countries.rename(columns={'id': 'personCountryId'}, inplace=True)
    results = results.merge(countries, how='inner', on='personCountryId')

    # create lists of events, initialize error lists to store results
    single_events = results[results['best'] > 0].eventId.unique()
    average_events = results[results['average'] > 0].eventId.unique()
    clear_errors, possible_errors = [], []

    # record consistency check
    # this is done one event at a time, first for single, then for average
    for event in single_events:
        record_consistency_check(results, comp_dates, event, 'single')
    for event in average_events:
        record_consistency_check(results, comp_dates, event, 'average')

    # output consistency check results
    with open(OUTPUT_FILE, "w") as output_stream:
        column_headers = ['WCA-ID', 'country', 'continent', 'event', 'record type', 'result', 'competition',
                          'start date', 'end date', 'round', 'stored', 'computed']

        # Output clear errors
        output_stream.write('Clear errors: {}\n\n'.format(len(clear_errors)))
        output_stream.write('\t'.join(column_headers) + '\n\n' if clear_errors else '')
        for detected_error in clear_errors:
            output_row = format_output_tuple(detected_error)
            output_stream.write(str(output_row) + '\n')

        # Output possible errors
        output_stream.write('\nPossible errors: {}\n\n'.format(len(possible_errors)))
        output_stream.write('\t'.join(column_headers) + '\n\n' if possible_errors else '')
        for detected_error in possible_errors:
            output_row = ''
            for output_record in detected_error:
                output_row += format_output_tuple(output_record)
            output_stream.write(str(output_row) + '\n')
