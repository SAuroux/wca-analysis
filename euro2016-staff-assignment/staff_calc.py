# -*- coding: utf-8 -*-
from __future__ import division
import sys, copy, random, time, datetime, codecs
from math import *

class Event:
	def __init__(self,index,day,start,end,event,round,groups,areas):
		self.index = index
		self.day = str(day)
		if self.day == "Friday":
			self.start = datetime.datetime(2016,7,15,int(start[:2]),int(start[2:]))
			self.end = datetime.datetime(2016,7,15,int(end[:2]),int(end[2:]))
		if self.day == "Saturday":
			self.start = datetime.datetime(2016,7,16,int(start[:2]),int(start[2:]))
			self.end = datetime.datetime(2016,7,16,int(end[:2]),int(end[2:]))
		if self.day == "Sunday":
			self.start = datetime.datetime(2016,7,17,int(start[:2]),int(start[2:]))
			self.end = datetime.datetime(2016,7,17,int(end[:2]),int(end[2:]))
		self.event = str(event)
		self.round = int(round)
		self.groups = int(groups)
		self.areas = int(areas)
	def __repr__(self):
		return str(self.event) + ", Round " + str(self.round) + ", " + str(self.day) + ", " + self.start.strftime("%H:%M") + " - " + self.end.strftime("%H:%M")
	def __str__(self):
		return str(self.event) + ", Round " + str(self.round) + ", " + str(self.day) + ", " + self.start.strftime("%H:%M") + " - " + self.end.strftime("%H:%M")
		
class Staff:
	def __init__(self,name,fri,sat,sun,run,scr1,scr2,prac,proc):
		self.name = str(name)
		self.fri = int(fri)
		self.sat = int(sat)
		self.sun = int(sun)
		self.run = int(run)
		if len(scr1) > 2:
			self.scr1 = [str(n) for n in scr1.split(",")]
		else:
			self.scr1 = []
		if len(scr2) > 2:
			self.scr2 = [str(n) for n in scr2.split(",")]
		else:
			self.scr2 = []
		if len(prac) > 2:
			self.prac = [str(n) for n in prac.split(",")]
		else:
			self.prac = []
		if len(proc) > 2:
			self.proc = [str(n) for n in proc.split(",")]
		else:
			self.proc = []
	def __repr__(self):
		return str(self.name)
	def __str__(self):
		return str(self.name)
		
main_events = ["333","444","555","222","333bf","333oh","333ft","minx","pyram","sq1","clock","skewb","666","777"]
side_events = ["333fm","444bf","555bf","333mbf"]
scramblers_main = 3
runners_main = 3
judges_main = {1: 10, 2: 20, 3: 28}
Events = []
Groups = []
Staffs = []
Grouping = {}
Heats = {}
Scramblers = {}
Runners = {}
Judges = {}
Labels = {"c": "Competitor", "p": "Possibly proceeded competitor", "s": "Scrambler", "r": "Runner", "j": "Judge"}
avail = {}
Schedules = {}
Avail_side = {}

fin = open("schedule.dat", "r")
num_events = 0
tmp = fin.readline()
while True:
	tmp = fin.readline().split(",")
	if len(tmp) > 1:
		num_events += 1
		Events.append(Event(num_events,tmp[0],tmp[1],tmp[2],tmp[3],tmp[4],tmp[5],tmp[6].replace("\n","")))
	else:
		break
		
for e in Events:
	for i in range(0,e.groups):
		start = e.start + i*(datetime.timedelta(hours=e.end.hour, minutes=e.end.minute) - datetime.timedelta(hours=e.start.hour, minutes=e.start.minute)) // e.groups
		end = e.start + (i+1)*(datetime.timedelta(hours=e.end.hour, minutes=e.end.minute) - datetime.timedelta(hours=e.start.hour, minutes=e.start.minute)) // e.groups
		heats = [i*e.areas+j+1 for j in range(0,e.areas)]
		g = (e.event,e.round,i+1,e.day,start,end)
		Groups.append(g)
		Heats[g] = heats
		
	
fin = open("staff.dat", "r")
tmp = fin.readline()
while True:
	tmp = fin.readline().split(";")
	if len(tmp) > 1:
		Staffs.append(Staff(tmp[0],tmp[1],tmp[2],tmp[3],tmp[4],tmp[5],tmp[6],tmp[7],tmp[8].replace("\n","")))
	else:
		break
		
fin = open("Grouping.dat", "r")
tmp = fin.readline().split(";")
gevents = [str(tmp[i].replace("\n","")) for i in range(3,len(tmp))]
while True:
	tmp = fin.readline().split(";")
	if len(tmp) > 1:
		name = str(tmp[2])
		Grouping[name] = {}
		for i in range(0,len(gevents)):
			Grouping[name][gevents[i]] = int(tmp[i+3])
	else:
		break
for s in Staffs: 
	if not s.name in Grouping:
		Grouping[s.name] = {}
		print "Warning: " + s.name + " is not included in the Grouping!"
		for e in gevents:
			Grouping[s.name][e] = 0

# remove availability because of competing or practising			
for s in Staffs:
	avail[s.name] = {}
	Schedules[s.name] = []
	for g in Groups:
		avail[s.name][g] = 2
for s in Staffs:
	for g in Groups:
		if s.fri == 0 and g[3] == "Friday":
			avail[s.name][g] = 0
		if s.sat == 0 and g[3] == "Saturday":
			avail[s.name][g] = 0
		if s.sun == 0 and g[3] == "Sunday":
			avail[s.name][g] = 0
		if g[1] == 1 and Grouping[s.name][g[0]] in Heats[g]:
			avail[s.name][g] = 0
			Schedules[s.name].append(("c",g))
			if g[0] in s.prac:
				for h in Groups:
					if avail[s.name][h] == 2 and h[4] < g[4] and h[5] > g[4] - datetime.timedelta(minutes=15):
						avail[s.name][h] = 1
		if g[1] > 1 and g[0] in s.proc:
			avail[s.name][g] = 0
			Schedules[s.name].append(("p",g))
			if g[0] in s.prac:
				for h in Groups:
					if avail[s.name][h] == 2 and h[4] < g[4] and h[5] > g[4] - datetime.timedelta(minutes=15):
						avail[s.name][h] = 1

# comparison output for side events
fout = open("output/avail_side.csv", "w")
fout.write("Event,Round,Group,Timeframe,Amount of staff members\n")
for g in Groups:
	if g[0] in side_events:
		avstaff = [s for s in Staffs if avail[s.name][g] > 0] 
		out = g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M") + "," + str(len(avstaff))
		fout.write(out + "\n")
fout.close()
						
# fix conflicts with parallel events						
for s in Staffs:
	for g in Groups:
		if g[0] in main_events:
			for h in Groups:
				if h[0] in side_events:
					if g[4] - datetime.timedelta(minutes=1) < h[5] + datetime.timedelta(minutes=1) and h[4] - datetime.timedelta(minutes=1) < g[5] + datetime.timedelta(minutes=1):
						if avail[s.name][g] == 0 and avail[s.name][h] > 0:
							avail[s.name][h] = -1 # intermediate value to avoid chain reactions	
						if avail[s.name][g] > 0 and avail[s.name][h] == 0:
							avail[s.name][g] = -1
for s in Staffs:
	for g in Groups:
		if avail[s.name][g] == -1:
			avail[s.name][g] = 0
			
			
# initial availability output
fout = open("output/initial_availability.csv", "w")
fout.write("Event,Round,Group,Timeframe,Amount of staff members\n")
for g in Groups:
	avstaff = [s for s in Staffs if avail[s.name][g] > 0] 
	out = g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M") + "," + str(len(avstaff))
	fout.write(out + "\n")
fout.close()

# input check	
errors = False	
print "Input error checks:"
for s in Staffs:
	for e in s.scr1:
		if not (e in main_events or e in side_events):
			print "Error for " + str(s.name) + ": Unknown scr1 event " + str(e) 
			errors = True
	for e in s.scr2:
		if not (e in main_events or e in side_events):
			print "Error for " + str(s.name) + ": Unknown scr2 event " + str(e) 
			errors = True
		if not e in s.scr1:
			print "Error for " + str(s.name) + ": scr2 event " + str(e) + " not in scr1"
			errors = True
	for e in s.prac:
		if not (e in main_events or e in side_events):
			print "Error for " + str(s.name) + ": Unknown prac event " + str(e) 
			errors = True
	for e in s.proc:
		if not (e in main_events or e in side_events):
			print "Error for " + str(s.name) + ": Unknown proc event " + str(e) 
			errors = True
	if s.fri not in [0,1] or s.sat not in [0,1] or s.sun not in [0,1]:
		print "Error for " + str(s.name) + ": Fri/Sat/Sun not boolean."
		errors = True
	if s.run not in [0,1,2]:
		print "Error for " + str(s.name) + ": False Running value."
		errors = True
for e in gevents:
	if not Grouping[s.name][e] in range(0,30):
		print "Error for " + str(s.name) + ": Invalid group for " + str(e) + "."
for e in Events:
	if not e.day in ["Friday","Saturday","Sunday"]:
		print "Error: Unknown day for " + str(e)
if errors == False:
	print "No input errors!"

	
# main part
lastg = 0
workload = {}
curr_wl = {}
for s in Staffs:
	workload[s.name] = datetime.timedelta(0)
	curr_wl[s.name] = datetime.timedelta(0)
for g in Groups:
	if g[0] in main_events:
		if lastg <> 0:
			if g[3] <> lastg[3]:
				lastg = 0
				for s in Staffs:
					curr_wl[s.name] = datetime.timedelta(0)
					
		par_group = 0
		for h in Groups:
			if h[0] in side_events and g[4] - datetime.timedelta(minutes=1) < h[5] + datetime.timedelta(minutes=1) and h[4] - datetime.timedelta(minutes=1) < g[5] + datetime.timedelta(minutes=1):
				par_group = h
				break
				
		h = len(Heats[g])
		
		Scramblers[g] = []
		avstaff = [s for s in Staffs if avail[s.name][g] > 0 and (g[0] in s.scr2 or g[0] in s.scr1)] 
		if len(avstaff) < h*scramblers_main:
			print "PROBLEM: Not enough staff for scrambling Group " + str(g)
			exit(1)
		random.shuffle(avstaff)
		avstaff.sort(key=lambda s: curr_wl[s.name])
		avstaff.sort(key=lambda s: workload[s.name])
		avstaff.sort(key=lambda s: sum(1 for ev in s.scr2 if ev == g[0]), reverse = True)
		avstaff.sort(key=lambda s: avail[s.name][g], reverse = True)
		if par_group <> 0:
			avstaff.sort(key=lambda s: avail[s.name][par_group])
		for i in range(0,h*scramblers_main):
			if lastg <> 0:
				if len(Scramblers[lastg]) >= i+1:
					ls = Scramblers[lastg][i]
					if g[0] in ls.scr2 and avail[ls.name][g] == 2 and curr_wl[ls.name] + g[5] - g[4] <= datetime.timedelta(hours=1):
						Scramblers[g].append(ls)
						Schedules[ls.name].append(("s",g))
						avail[ls.name][g] = 0
						avstaff.remove(ls)
						workload[ls.name] += g[5] - g[4]
						curr_wl[ls.name] += g[5] - g[4]
						if par_group <> 0:
							avail[ls.name][par_group] = 0
			if len(Scramblers[g]) < i+1:
				chs = avstaff[0]
				Scramblers[g].append(chs)
				Schedules[chs.name].append(("s",g))
				avail[chs.name][g] = 0
				avstaff.remove(chs)
				workload[chs.name] += g[5] - g[4]
				curr_wl[chs.name] += g[5] - g[4]
				if par_group <> 0:
					avail[chs.name][par_group] = 0
		
		Runners[g] = []
		avstaff = [s for s in Staffs if avail[s.name][g] > 0 and s.run > 0] 
		if len(avstaff) < h*runners_main:
			print "PROBLEM: Not enough staff for runners of Group " + str(g)
			exit(1)
		random.shuffle(avstaff)
		avstaff.sort(key=lambda s: curr_wl[s.name])
		avstaff.sort(key=lambda s: s.run, reverse = True)
		avstaff.sort(key=lambda s: workload[s.name])
		avstaff.sort(key=lambda s: avail[s.name][g], reverse = True)
		if par_group <> 0:
			avstaff.sort(key=lambda s: avail[s.name][par_group])
		for i in range(0,h*runners_main):
			if lastg <> 0:
				if len(Runners[lastg]) >= i+1:
					ls = Runners[lastg][i]
					if avail[ls.name][g] == 2 and curr_wl[ls.name] + g[5] - g[4] <= datetime.timedelta(hours=1):
						Runners[g].append(ls)
						Schedules[ls.name].append(("r",g))
						avail[ls.name][g] = 0
						avstaff.remove(ls)
						workload[ls.name] += g[5] - g[4]
						curr_wl[ls.name] += g[5] - g[4]
						if par_group <> 0:
							avail[ls.name][par_group] = 0
			if len(Runners[g]) < i+1:
				chs = avstaff[0]
				Runners[g].append(chs)
				Schedules[chs.name].append(("r",g))
				avail[chs.name][g] = 0
				avstaff.remove(chs)
				workload[chs.name] += g[5] - g[4]
				curr_wl[chs.name] += g[5] - g[4]
				if par_group <> 0:
					avail[chs.name][par_group] = 0
				
		Judges[g] = []
		avstaff = [s for s in Staffs if avail[s.name][g] > 0] 
		if len(avstaff) < judges_main[h]:
			print "Warning: Not enough staff for judging Group " + str(g)
			print str(len(avstaff)) + " available, but " + str(judges_main[h]) + " needed!"
		random.shuffle(avstaff)
		avstaff.sort(key=lambda s: curr_wl[s.name])
		avstaff.sort(key=lambda s: workload[s.name])
		avstaff.sort(key=lambda s: avail[s.name][g], reverse = True)
		if par_group <> 0:
			avstaff.sort(key=lambda s: avail[s.name][par_group])
		for i in range(0,judges_main[h]):
			if len(avstaff) == 0:
				for j in range(i,judges_main[h]):
					Judges[g].append("NA")
				break
			if lastg <> 0:
				if len(Judges[lastg]) >= i+1 and Judges[lastg][-1] <> "NA":
					ls = Judges[lastg][i]
					if avail[ls.name][g] == 2 and curr_wl[ls.name] + g[5] - g[4] <= datetime.timedelta(hours=1):
						Judges[g].append(ls)
						Schedules[ls.name].append(("j",g))
						avail[ls.name][g] = 0
						avstaff.remove(ls)
						workload[ls.name] += g[5] - g[4]
						curr_wl[ls.name] += g[5] - g[4]
						if par_group <> 0:
							avail[ls.name][par_group] = 0
			if len(Judges[g]) < i+1:
				chs = avstaff[0]
				Judges[g].append(chs)
				Schedules[chs.name].append(("j",g))
				avail[chs.name][g] = 0
				avstaff.remove(chs)
				workload[chs.name] += g[5] - g[4]
				curr_wl[chs.name] += g[5] - g[4]
				if par_group <> 0:
					avail[chs.name][par_group] = 0
				
		for s in Staffs:
			if not (s in Scramblers[g] or s in Runners[g] or s in Judges[g]):
				curr_wl[s.name] = datetime.timedelta(0)
				
		lastg = g
					
for g in Groups:
	if g[0] in side_events:
		avstaff = [s for s in Staffs if avail[s.name][g] > 0] 
		Avail_side[g] = avstaff
		if g[0] <> "333fm":
			for s in avstaff:
				Schedules[s.name].append(("j",g))
		#print g[0]
		#print len(avstaff)
		
for s in Staffs:
	Schedules[s.name].sort(key=lambda k: k[1][4])
	
# Consistency check
errors = False
for s in Staffs:
	sched = Schedules[s.name]
	for k in range(1,len(sched)):
		if sched[k][1][4] < sched[k-1][1][5]:
			errors = True
			print "Consistency error for " + s.name + "!"
			print sched[k-1]
			print sched[k]
if errors == False:
	print "Consistency check passed!"		
	
# Output
fout = open("output/scramblers_main.csv", "w")
out = "Event,Round,Group,Timeframe" 
for i in range(1,10):
	out += ",Scrambler " + str(i)
fout.write(out + "\n")
for g in Groups:
	if g[0] in main_events:
		out = g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M")
		for s in Scramblers[g]:
			out += "," + str(s)
		fout.write(out + "\n")
fout.close()
		
fout = open("output/runners_main.csv", "w")
out = "Event,Round,Group,Timeframe" 
for i in range(1,10):
	out += ",Runner " + str(i)
fout.write(out + "\n")
for g in Groups:
	if g[0] in main_events:
		out = g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M")
		for s in Runners[g]:
			out += "," + str(s)
		fout.write(out + "\n")
fout.close()
		
fout = open("output/judges_main.csv", "w")
out = "Event,Round,Group,Timeframe" 
for i in range(1,29):
	out += ",Judge " + str(i)
fout.write(out + "\n")
for g in Groups:
	if g[0] in main_events:
		out = g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M")
		for s in Judges[g]:
			out += "," + str(s)
		fout.write(out + "\n")
fout.close()
		
fout = open("output/staff_side.csv", "w")
out = "Event,Round,Group,Timeframe,Available staff members" 
fout.write(out + "\n")
for g in Groups:
	if g[0] in side_events:
		out = g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M")
		for s in Avail_side[g]:
			out += "," + str(s)
		fout.write(out + "\n")
fout.close()

fout = open("output/staff_workloads.csv", "w")
fout.write("Workload of the staff members\n")
for s in Staffs:
	fout.write(s.name + ": " + str(workload[s.name]) + "\n")
fout.close()

fout = open("output/staff_schedules.csv", "w")
for s in Staffs:
	fout.write(s.name + "\n")
	fout.write("\n")
	for k in Schedules[s.name]:
		if k[0] <> "p":
			out = Labels[k[0]] + ","
			g = k[1]
			out += g[0] + ",Round " + str(g[1]) + ",Group " + str(g[2]) + "," + g[3] + " " + g[4].strftime("%H:%M") + " - " + g[5].strftime("%H:%M") + "\n"
			fout.write(out)	
	fout.write("\n")
fout.close()