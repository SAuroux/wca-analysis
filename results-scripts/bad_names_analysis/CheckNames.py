#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Alexandre Campos (Idea & First version), Sébastien Auroux (Modifications)
# acampos@worldcubeassociation.org
# sauroux@worldcubeassociation.org

# Instructions:
# 1. place and extract the export from https://www.worldcubeassociation.org/results/misc/WCA_export.tsv.zip
# in a folder and set global variable DB_EXPORT_DIR to the corresponding path
# 2. Run CheckNames.py

# Change log:
# 2019-02-10: conversion to Python 3, ignoring local names in proper ()-brackets.
# 2019-02-12: add characters code to the output, update instructions
# 2019-09-20: minor modifications for upload
# 2021-12-22: code cleanup & global variable for WCA export location

import csv
import datetime
import pathlib
import string

# global variables

# Location and filenames of the database export used by the script
DB_EXPORT_DIR = pathlib.Path("../_wca_db_export")
DB_PERSONS_TSV = "WCA_export_Persons.tsv"

# allowed non-alphanumeric characters
ALLOWED_NON_ALPHANUM_CHARS = " .-()'"


def validate(str_to_check):
    return [x for x in str_to_check if not (x.isalpha()) and not (x in ALLOWED_NON_ALPHANUM_CHARS)]


def suggestion(invalid):
    # 1 warning by type
    parenthesis = True
    apostrophe = True
    dot = True
    printable = True

    output = []
    char_codes = []
    for x in invalid:

        if x in "（）" and parenthesis:
            parenthesis = False
            output.append("Use regular parenthesis")

        if x in "’`" and apostrophe:
            apostrophe = False
            output.append("Use regular apostrophe")

        if x == "·" and dot:
            dot = False
            output.append("Replace by regular dot")

        if x not in string.printable and printable:
            printable = False
            output.append("Not printable character detected")

        char_codes.append(str(ord(x)))

    return " - ".join(output) + "\tChar codes: " + ", ".join(char_codes)


if __name__ == "__main__":
    out = ''
    with open(DB_EXPORT_DIR / DB_PERSONS_TSV, encoding="utf8") as tsv_file:

        tsv_reader = csv.reader(tsv_file, delimiter="\t")
        for line in tsv_reader:

            name = line[2]
            if '(' in name and name[-1] == ')':
                name = name[:name.find('(')]
            invalid_chars = validate(name)

            if invalid_chars:
                person_id = line[0]
                out += person_id + "\t" + name + "\t" + "".join(invalid_chars) + "\t" + suggestion(invalid_chars) + "\n"

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    with open("output_{}.txt".format(timestamp), "w", encoding="utf8") as f_out:
        f_out.write(out)
