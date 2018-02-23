#!/usr/bin/env python
# coding: utf-8

""" Top 100 WCA podium trios.

Originally written: June 2015

This script analyses the WCA database for podium trios, i.e. three people
sharing a podium at a WCA competition, and generates the Top 100 podium trios
with most shared podiums (outut in BB table code).

The script requires a WCA database export to be assigned to <source>.
For more information check:
https://www.worldcubeassociation.org/results/misc/export.html

"""

__author__ = "Sébastien Auroux"
__contact__ = "sebastien@auroux.de"

import zipfile, csv
import itertools

source = 'WCA_export007_20180223.tsv.zip'
output_file = 'podium_trios_20180223.txt'

people = []
podiums = {}
names = {}
podiums_person = {}

with zipfile.ZipFile(source) as zf:
	with zf.open('WCA_export_Results.tsv') as pf:
		for row in csv.DictReader(pf, delimiter='\t'):
			if not row['competitionId'] in podiums:
				podiums[row['competitionId']] = {}
			if not row['eventId'] in podiums[row['competitionId']]:
				podiums[row['competitionId']][row['eventId']] = []
			if row['pos'] in ['1','2','3'] and row['roundTypeId'] in ['c','f'] and row['best'] not in ['-2','-1','0']:
				podiums[row['competitionId']][row['eventId']].append(row['personId'])
				if not row['personId'] in people:
					people.append(row['personId'])
					podiums_person[row['personId']] = []
				podiums_person[row['personId']].append([row['competitionId'],row['eventId']])
	with zf.open('WCA_export_Persons.tsv') as pf:
		for row in csv.DictReader(pf, delimiter='\t'):
			if row['subid'] == '1':
				names[row['id']] = row['name']

sdict = {}

for i in range(0,len(people)):
	print("Searching for podium person " + str(i+1) + " out of " + str(len(people)) + ": " + people[i])
	for p in podiums_person[people[i]]:
		for j in podiums[p[0]][p[1]]:
			for k in podiums[p[0]][p[1]]:
				if (people[i],k,j) not in sdict and (j,people[i],k) not in sdict and (j,k,people[i]) not in sdict and (k,people[i],j) not in sdict and (k,j,people[i]) not in sdict:
					if not (people[i],j,k) in sdict:
						sdict[(people[i],j,k)] = 0
					if people[i]<>j and people[i]<>k and j<>k:
						sdict[(people[i],j,k)] += 1

scores = [[s[0],s[1],s[2],sdict[s]] for s in sdict]
scores.sort(key=lambda s: s[3], reverse=True)

out = ''
out += '[spoiler="Top 100 of most common podium trios"][table="width: 1000, class: grid, align: left"]\n'
out += '[tr][td][b]#[/b][/td][td][b]Person 1[/b][/td][td][b]Person 2[/b][/td][td][b]Person 3[/b][/td][td][b]Amount of shared Podiums[/b][/td][/tr]\n'
pos = "1."
for i in range(0,100):
	if i > 0 and scores[i][3] < scores[i-1][3]:
		pos = str(i+1) + "."
	cells = (pos, names[scores[i][0]], names[scores[i][1]], names[scores[i][2]], scores[i][3])
	out += '[tr]' + ''.join('[td]{}[/td]'.format(x) for x in cells) + '[/tr]\n'
out += '[/table][/spoiler]'

fout = open(output_file, "w")
fout.write(out)
