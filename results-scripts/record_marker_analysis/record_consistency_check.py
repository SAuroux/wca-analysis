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
import time

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
        for bad_padding in ['0:00:0', '0:00:', '0:0', '0:', '0']:
            rel_index = len(bad_padding)
            if out[:rel_index] == bad_padding:
                out = out[rel_index:]

        return out


def check_record(value, min_per_round, cummin_above, past_records, region):
    """ helper function to check whether or not a given result could potentially be a record """

    # min_per_round (best result per round) is already known at this point, so if there was already a
    # better results for this competition, round, region then return False
    if min_per_round < value:
        return False

    # further, the result needs to be at least as good as all preceding values
    if cummin_above < value:
        return False

    # otherwise compare against past records
    return region not in past_records or value <= past_records[region]


def get_past_records(df, value_col):
    """ helper function to construct a dict of standing records from the given DataFrame """

    if df.empty:
        return {}

    past_records = {'World': df[value_col].min()}
    past_records.update(df[['continentId', value_col]].groupby('continentId')[value_col].min().to_dict())
    past_records.update(df[['personCountryId', value_col]].groupby('personCountryId')[value_col].min().to_dict())

    return past_records


def evaluate_records(records, comp_year, event_id, kind, clear_errors, possible_errors, evaluated_hashes):
    """ helper function to further assess possible errors

    for all record types, a single record among overlapping competitions
    where the current marker does not equal the computed marker corresponds
    to a clear error. However, this requires double-checking for the affected
    competition's overlapping set.
    Meanwhile, multiple records with the same region are given out to
    check for possible errors.
    """

    if len(records) == 0:
        return None

    records_hash = pd.util.hash_pandas_object(records).sum()
    if records_hash in evaluated_hashes:
        # this set of records was already checked, don't check again!
        return None
    evaluated_hashes.append(records_hash)

    if len(records) == 1:
        if records.iloc[0]['marker'] != records.iloc[0]['computed']:
            # only one record without conflicts differing from computed, so this is a clear error
            store_errors(records, event_id, kind, clear_errors)
        return None

    if records['value'].nunique() == 1 and not (records['marker'] == records['computed']).all():
        # ties should always be marked as awarded records, otherwise this is a clear error
        store_errors(records, event_id, kind, clear_errors)
    elif comp_year >= 2013 and records['competitionId'].nunique() == 1 \
            and records.iloc[0]['num_days'] < records.loc[records['marker'] != '', 'value'].nunique():
        # since 2013, any competition with number of days < number of distinct records (without ties) is a clear error
        store_errors(records, event_id, kind, clear_errors)
    else:  # possible error
        store_errors(records, event_id, kind, possible_errors)


def store_errors(records, event_id, kind, errors):
    """ helper function to store record errors """

    err = [output_tuple(row, event_id, kind) for _, row in records.iterrows()]

    if err and err not in errors:
        errors.append(err)

    return errors


def output_tuple(row, event_id, kind):
    """ helper function to create output tuples """
    return (row['personId'], row['country'], row['continent'], event_id, kind, format_result(row['value'], event_id),
            row['competitionId'], row['start_date'].strftime('%Y-%m-%d'), row['end_date'].strftime('%Y-%m-%d'),
            row['round'], row['marker'], row['computed'])


def format_error_output(err):
    """ helper function to format output tuples """
    return '\n'.join(['\t'.join(map(str, t)) for t in err])


def record_consistency_check(df, competition_dates, event_id, kind):
    """ checks for consistency of all records of a certain event and a
    certainly kind(single or average) and stores all clear/possible errors.
    The function loops through all competitions ordered by start_date,
    compared result to all records that happened strictly before a given
    competition and eventually stores clear errors and possible errors. """

    if kind not in ['single', 'average']:
        print("Warning: Invalid record kind for consistency check: " + str(kind))
        return [], []

    print("Calculating all potential records for {} {} records...".format(event_id, kind))

    value_col = 'best' if kind == 'single' else 'average'
    marker_col = 'regionalSingleRecord' if kind == 'single' else 'regionalAverageRecord'

    # reduce provided data to relevant rows and columns to improve execution time
    df = df[(df['eventId'] == event_id) & (df[value_col] > 0)]
    df = df.drop(columns=['eventId', 'average' if kind == 'single' else 'best'])
    df = df.sort_values(by=['start_date', 'end_date', 'competitionId', 'round_rank', value_col])

    # from the remaining rows, only those with a marker or with the best value per round and country are relevant
    df['min_round_nat'] = df.groupby(['competitionId', 'roundTypeId', 'personCountryId'])[value_col].transform('min')
    df = df[(df[value_col] == df['min_round_nat']) | (df[marker_col] != '')]

    # generate more helpful columns for the upcoming consistency check
    df['min_round_con'] = df.groupby(['competitionId', 'roundTypeId', 'continentId'])[value_col].transform('min')
    df['min_round_world'] = df.groupby(['competitionId', 'roundTypeId'])[value_col].transform('min')
    df['cummin_comp_nat'] = df.groupby(['competitionId', 'personCountryId'])[value_col].agg('cummin')
    df['cummin_comp_con'] = df.groupby(['competitionId', 'continentId'])[value_col].agg('cummin')
    df['cummin_comp_world'] = df.groupby(['competitionId'])[value_col].agg('cummin')

    # create needed lists and dictionaries to store the consistency check results
    all_records, past_records = [], {}
    clear_errors, possible_errors = [], []
    old_start_date = np.min(df['start_date'])

    # first compute all potential records
    for index, row in df.iterrows():
        competition = row['competitionId']
        round_id = row['roundTypeId']
        country = row['personCountryId']
        continent = row['continentId']
        value = int(row[value_col])
        marker = row[marker_col]
        s_date = row['start_date']

        if s_date != old_start_date:
            past_records = get_past_records(df[df['end_date'] < s_date], value_col)

        record_data = {'personId': row['personId'], 'competitionId': competition, 'round': round_id, 'value': value,
                       'country': country, 'continent': continent, 'start_date': s_date, 'end_date': row['end_date'],
                       'marker': marker, 'computed': ''}

        # check for record potential in order: national, continental, global
        if check_record(value, row['min_round_nat'], row['cummin_comp_nat'], past_records, country):
            record_data['computed'] = NR_MARKER
            record_data['region'] = country
            if check_record(value, row['min_round_con'], row['cummin_comp_con'], past_records, continent):
                record_data['computed'] = CR_MARKER[continent]
                record_data['region'] = continent
                if check_record(value, row['min_round_world'], row['cummin_comp_world'], past_records, 'World'):
                    record_data['computed'] = WR_MARKER
                    record_data['region'] = 'World'
            all_records.append(record_data)

        # if no record was computed but a record is currently stored, this is a clear error.
        # Adding these here to clear_errors right away is most convenient.
        if record_data['computed'] == '' and marker != '':
            err = output_tuple(record_data, event_id, kind)
            clear_errors.append(err)

        old_start_date = s_date

    # then analyze records for (possible) errors
    print("Analyzing potential records for {} {} records...".format(event_id, kind))

    record_df = pd.DataFrame(all_records)
    record_df['num_days'] = (record_df['end_date'] - record_df['start_date']).dt.days + 1
    record_competitions = record_df['competitionId'].unique()
    evaluated_hashes = []  # list for storing hashes of evaluated DataFrames with records to prevent duplicate checks

    for comp in record_competitions:
        s_date, e_date = competition_dates.loc[comp]['start_date'], competition_dates.loc[comp]['end_date']
        overlapping_comps = record_df[(s_date <= record_df['end_date'])
                                      & (record_df['start_date'] <= e_date)].competitionId.unique()

        # now check for world, continental and national records
        comp_set_records = record_df[record_df['competitionId'].isin(overlapping_comps)]

        # before 2013, records were awarded at the end of each round.
        # Therefore we can continue here if and year < 2013, if there is just one competition
        # and if all existing markers match the computed ones.
        if s_date.year < 2013 and comp_set_records['competitionId'].nunique() == 1 \
                and (comp_set_records['marker'] == comp_set_records['computed']).all():
            continue

        # world records
        curr_records = comp_set_records[comp_set_records['computed'] == WR_MARKER]
        if comp in curr_records['competitionId'].values:
            evaluate_records(curr_records, s_date.year, event_id, kind,
                             clear_errors, possible_errors, evaluated_hashes)

        # continental records
        ov_con_records = comp_set_records[comp_set_records['computed'] != NR_MARKER]
        curr_continents = list(ov_con_records['continent'].unique())
        for con in curr_continents:
            curr_records = ov_con_records[ov_con_records['continent'] == con]
            if comp in curr_records['competitionId'].values \
                    and (curr_records['computed'].isin(list(CR_MARKER.values()))).sum() > 0:
                evaluate_records(curr_records, s_date.year, event_id, kind,
                                 clear_errors, possible_errors, evaluated_hashes)

        # national records
        curr_countries = list(comp_set_records['country'].unique())
        for nat in curr_countries:
            curr_records = comp_set_records[comp_set_records['country'] == nat]
            if comp in curr_records['competitionId'].values and (curr_records['computed'] == NR_MARKER).sum() > 0:
                evaluate_records(curr_records, s_date.year, event_id, kind,
                                 clear_errors, possible_errors, evaluated_hashes)

    return clear_errors, possible_errors


if __name__ == '__main__':
    # Asking for a start date for outputting possible errors:
    input_date = input("Date to begin output for possible errors (YYYY-MM-DD) (leave blank for all possible errors): ")
    start_time = time.time()

    possible_errors_start_date = pd.to_datetime(input_date, errors='coerce')
    if pd.isnull(possible_errors_start_date):
        possible_errors_start_date = datetime.datetime(1982, 1, 1, 0, 0, 0)
        if input_date:  # warn only if input provided was not blank
            print("Warning: Could not parse input '%s', will output all possible errors." % input_date)

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
    competition_data['start_date'] = pd.to_datetime(competition_data.apply(get_start_date, axis=1))
    competition_data['end_date'] = pd.to_datetime(competition_data.apply(get_end_date, axis=1))
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
    events_to_check = [(event, 'single') for event in single_events] + [(event, 'average') for event in average_events]
    all_clear_errors, all_possible_errors = [], []

    # record consistency check
    # this is done one event at a time, first for single, then for average
    for i, (curr_event_id, curr_kind) in enumerate(events_to_check):
        runtime = time.time() - start_time
        print("[{}/{} {:02d}:{:02d}] Checking consistency for {} {} records:".format(
            i + 1, len(events_to_check), int(runtime / 60), int(runtime) % 60, curr_event_id, curr_kind))
        ce, pe = record_consistency_check(results, comp_dates, curr_event_id, curr_kind)
        all_clear_errors.extend(ce)
        all_possible_errors.extend(pe)

    # output consistency check results
    with open(OUTPUT_FILE, "w") as output_stream:
        column_headers = ['WCA-ID', 'country', 'continent', 'event', 'record type', 'result', 'competition',
                          'start date', 'end date', 'round', 'stored', 'computed']

        # Output clear errors
        output_stream.write('Clear errors: {}\n\n'.format(len(all_clear_errors)))
        output_stream.write('\t'.join(column_headers) + '\n\n' if all_clear_errors else '')
        for detected_error in all_clear_errors:
            output_stream.write(format_error_output(detected_error) + '\n\n')

        # Filter possible errors for end_date >= possible_errors_start_date for at least one of the included results
        all_possible_errors = [pe for pe in all_possible_errors
                               if len([err for err in pe if pd.to_datetime(err[8]) >= possible_errors_start_date]) > 0]

        # Output possible errors
        output_stream.write('\nPossible errors: {}\n\n'.format(len(all_possible_errors)))
        output_stream.write('\t'.join(column_headers) + '\n\n' if all_possible_errors else '')
        for detected_error in all_possible_errors:
            output_stream.write(format_error_output(detected_error) + '\n\n')
