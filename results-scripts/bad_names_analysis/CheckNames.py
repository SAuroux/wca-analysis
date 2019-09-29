#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Alexandre Campos (Idea & First version), Sébastien Auroux (Modifications)
# acampos@worldcubeassociation.org
# sauroux@worldcubeassociation.org
# 2019

# place this CheckNames.py in a folder
# place the export from
# https://www.worldcubeassociation.org/results/misc/WCA_export.tsv.zip
# in a folder called db_export

# your main folder would contain

# | ChackNames.py
# | db_export/

# db_export/ would contain the extracted version of the .zips

# 2019-02-10: conversion to Python 3, ignoring local names in proper ()-brackets.
# 2019-02-12: add characters code to the output, update instructions
# 2019-09-20: minor modifications for upload

import csv, string, sys, datetime

allowed = " .-()'"

def validate(s):

	out = ""
	invalid = []
	for x in s:
		if not (x.isalpha()) and not (x in allowed): # not a letter
			invalid.append(x)
	flag = len(invalid) == 0
	return flag, invalid

def suggestion(invalid):

	# 1 warning by type
	parenthesis = True
	apostophre = True
	dot = True
	printable = True
	
	out = []
	char_codes = []
	for x in invalid:
	
		if x in "（）" and parenthesis:
			parenthesis = False
			out.append("Use regular parenthesis")

		if x in "’`" and apostophre:
			apostophre = False
			out.append("Use regular apostrophe")

		if x == "·" and dot:
			dot = False
			out.append("Replace by regular dot")

		if not x in string.printable and printable:
			printable = False
			out.append("Not printable character detected")
		
		char_codes.append(str(ord(x)))
			
	return " - ".join(out) +"\tChar codes: "+ ", ".join(char_codes)

if __name__ == "__main__":
	out = ''
	with open("db_export/WCA_export_Persons.tsv", encoding="utf8") as tsvfile:

		tsvreader = csv.reader(tsvfile, delimiter="\t")
		for line in tsvreader:
		
			name = line[2]
			if '(' in name and name[-1] == ')':
				name = name[:name.find('(')]
			flag, invalid = validate(name)
			
			if not flag:
				person_id = line[0]
				out += person_id + "\t" + name + "\t" + "".join(invalid) + "\t" + suggestion(invalid) + "\n"

	timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")			
	with open("output_{}.txt".format(timestamp), "w", encoding="utf8") as fout:
		fout.write(out)
