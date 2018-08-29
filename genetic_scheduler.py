#!/usr/bin/env python 
# -*- coding: utf-8 -*-

'''
James Wild, August 2018

This is a script that can take an arbitrary number of jobs, and organise them in the most efficient way it can.
To do this, it takes a preferred order of which jobs to do in the form of a chromosome, e.g. for three jobs:
[0,1,2,0,1,2,0,1,2]
will place the next task from job 0 first, then from job 1, and so on.

The ideal order is found using a genetic algorithm, with the fitness of an individual being the number of slots it
requires to fit all the tasks in.
'''

import numpy as np
import json
import time
import random as rand
import datetime
import os
from icalendar import Calendar, Event
import pytz
import socket


def get_5_min_time(hh, mm=0):
	'''takes hours and minutes, and converts it to the proper index for the schedule. Rounds mm DOWN to the nearest 5'''
	# an hour in minutes
	hh = int(float(hh)*60)
	
	mm = int(mm)

	# Make sure it's an int, so it rounds down to the nearest slot
	return int(hh+mm)/5

def read_job_file(fname):
	'''Read in a job JSON file, and scrub the input so we dont have to worry about it later'''
	with open(fname) as f:
			job = json.load(f)

	# I need to add an ID string to each task. The Job ID can be passed to the function, defaults to '00'.
	# The experiments are ordered in their list, so the ID can be taken as their place in that list. 
	# Tasks are again ordered, so can be taken from there too.
	# Hence, I only need to define a /job/ ID, and the others are implicitly tagged. 
	# Store jobs in an ordered list to give them their ID in the same way as experiments and tasks
	for exp_name in job['order']:
		for task in job[exp_name]:
			task['name']     = str(task['name'])
			task['active']   = int(task['active'])
			task['flexible'] = int(task['flexible'])
			# Convert the time to the slots
			task['time']     = get_5_min_time(0, int(task['time']))

	return job

def construct_ID(job_index, exp_index, tas_index):
	'''Quick function to construct the proper ID string'''
	ID = str(job_index).rjust(2, '0')
	ID+= str(exp_index).rjust(2, '0')
	ID+= str(tas_index).rjust(2, '0')

	return ID

def parse_ID(ID):
	'''Takes an ID string and returns the indeces'''
	if ID == None or ID == '':
		return None, None, None
	if ID == '999999':
		return -1, 0, 0

	job_index = int(ID[:2])
	exp_index = int(ID[2:4])
	tas_index = int(ID[4:])

	return job_index, exp_index, tas_index

def get_experiment(jobs, ID):
	job_index, exp_index, tas_index = parse_ID(ID)
	experiment_name = jobs[job_index]['order'][exp_index]

	experiment = jobs[job_index][experiment_name]

	return experiment

def get_task(existing_jobs, jobs, ID):
	'''Gets the appropriate task dict, defined by the given ID string. 
	ID string in the format 'XXYYZZ'
	XX - Job index in [jobs]
	YY - Experiment index in job['order']
	ZZ - Task index in job[experiment] 

	Also, if the ID is 999999, it is night time.
	'''
	if ID == None:
		return None

	if ID == '999999':
		task = {'name': 'Home Time ',
				'time': 1,
				'active': 1,
				'flexible': 0
			}
		return task

	if ID == '999998':
		task = {'name': 'Conflicting',
				'time': 1,
				'active': 1,
				'flexible': 0
			}
		return task

	# Just double-check ID is a string...
	ID = str(ID)

	if ID == '':
		return None

	job_index = int(ID[:2])
	exp_index = int(ID[2:4])
	tas_index = int(ID[4:])

	if job_index == 99:
		job = existing_jobs
		tas_index = int(ID[2:])
		task = job[tas_index]
		return task

	job = jobs[job_index]
	try:
		experiment = job[ job['order'][exp_index] ]
		task = experiment[tas_index]
	except:
		task = None

	return task

def incriment_ID(existing_jobs, jobs, ID):
	'''Tries to incriment to the next task in the experiment. 
	Failing that, incriments to the next experiment in the job. 
	Failing that, returns None'''
	
	if ID == None:
		return None

	new_ID = list(ID)
	
	job_index = int(''.join(new_ID[:2]))
	exp_index = int(''.join(new_ID[2:4]))
	tas_index = int(''.join(new_ID[4:]))

	# print('Incrimenting %s' % ID)
	# print('Number of tasks in that experiment: %d' % len(job[ job['order'][exp_index] ]))
	# print('task index: %d' % tas_index)

	# check code against the length of the experiment list in the job
	job = jobs[job_index]
	experiment = get_experiment(jobs, ID)

	if len(experiment)-1 > tas_index:
		# print('First conditional entered')
		tas_index += 1
	# check the length of the order list agains the experiment code
	elif int(len(job['order'])-1) > exp_index:
		# print('Second conditional entered')
		tas_index = 0
		exp_index += 1
	
	new_ID = str(job_index).rjust(2, '0')
	new_ID+= str(exp_index).rjust(2, '0')
	new_ID+= str(tas_index).rjust(2, '0')					

	if new_ID == ID:
		new_ID = None

	# print('Returning %s' % new_ID)
	if get_task(existing_jobs, jobs, new_ID):
		return new_ID
	else:
		# print('Couldnt find that task, returning None')
		return None

def decriment_ID(jobs, ID):
	'''Tries to decriment to the previous task in the experiment. 
	If the first task in the experiment, goes to the last task in the previous one.
	If the first experiment in the job, returns None.'''
	
	new_ID = list(ID)

	job_index = int(''.join(new_ID[:2]))
	exp_index = int(''.join(new_ID[2:4]))
	tas_index = int(''.join(new_ID[4:]))

	# Check to see if task is 0
	if tas_index > 0:
		tas_index -= 1
		return construct_ID(job_index, exp_index, tas_index)
	elif tas_index == 0:
		# Is this the first experiment in the list?
		if exp_index == 0:
			return None
		# Otherwise, decriment that too
		else:
			exp_index -= 1
			# Now we need to know how many tasks are in that experiment.
			experiment = get_experiment(jobs, construct_ID(job_index, exp_index, '00'))
			tas_index = len(experiment)-1

			return construct_ID(job_index, exp_index, tas_index)

def get_exp_time(job, experiment):
	'''Get the minimum number of slots that an experiment will take to complete'''
	exp_time = 0.0
	for task in job[experiment]:
		exp_time += float(task['time'])
	return exp_time

def check_active_slot(existing_jobs, jobs, slot):
	'''Takes a slot, loops through the IDs and checks how many are active. Returns int.'''
	active = 0
	for ID in slot:
		task = get_task(existing_jobs, jobs, ID)
		try:
			active += task['active']
		except:
			True
	return active

def str2int(string, base):
	'''Takes a string form of a number in base <base>, and converts to decimal'''
	string = list(string)

	value = 0.
	for i, l in enumerate(string[::-1]):
		l = int(l)
		value += l* (base**i)

	return value

def toStr(n,base):
	'''Converts a number in base 10 to its string representation in base <base>'''
	convertString = "0123456789ABCDEF"
	if n < base:
		return convertString[n]
	else:
		return toStr(n//base,base) + convertString[n%base]

def initialise_day(jobs, work_hours, workday_start, workday_end, existing_jobs, initial_date):
	# Store the order like this?
	# order[ 010000, 010000, 010001, ..., 020105 ]
	# Where each slot of the list is 5 minutes.

	# Schedule array. index 0 is the first time slot of the day, and lasts the number of work hours.
	work_hours = get_5_min_time(work_hours)
	
	# This will contain only the schedules for the appropriate jobs.
	n_jobs = len(jobs) + 1
	job_schedules = [['' for i in range(work_hours)] for job in range(n_jobs)]

	# schedule[0] is 00:00 on monday. I want both 00:00-08:00 and 16:00-23:55 to be occupied before we start.
	day_length = get_5_min_time(24,00)

	init_day = initial_date.isoweekday() -1

	# Add in existing tasks
	j = 0
	for task in existing_jobs:
		task_ID = '99'+str(j).rjust(4, '0')
		j+= 1
		start_slot = task['first_slot']
		time = int(task['time'])
		for i in range(-1, time+1):
			try:
				if job_schedules[-1][start_slot+i] == '':
					job_schedules[-1][start_slot+i] = task_ID
				else:
					job_schedules[-1][start_slot+i] = '999998'
			except:
				break

	# Add in a blocking task, to account for night times. Overwrite existing tasks with this
	for i in range(work_hours):
		# We only care about where we are in the day, not the week. Use modulo to reduce this down.
		time = i%day_length
		day  = (i//day_length) + init_day

		# If we are before 8AM
		if time < workday_start:
			job_schedules[-1][i] = '999999'
		# or after 4PM
		elif time >= workday_end:
			job_schedules[-1][i] = '999999'
		# Or on a weekend
		elif day%7 == 5 or day%7 == 6:
			job_schedules[-1][i] = '999999'

	return job_schedules

def generate_schedule(initial_date, existing_jobs, jobs, permutation, workday_start, workday_end, debug=0, work_hours=7*24):
	'''Generates a schedule from a given permutation.
	returns:
	schedule, job_schedules, skipped_tasks'''

	# Re-initialise the schedules
	job_schedules = initialise_day(jobs, work_hours, workday_start, workday_end, existing_jobs, initial_date)

	# Re-initialise the current_tasks list
	n_jobs = len(jobs)
	current_tasks = []
	for i in range(n_jobs):
		job_index = str(i).rjust(2,'0')
		current_tasks.append(job_index+'0000')

	# Store skipped tasks
	skipped_tasks = []

	# Get this permutation as a list
	# permutation = list(permutation)

	perm_index = 0
	while current_tasks.count(None) != n_jobs:
		starter_ID = ''
		# Start with the longest experiment?
		# !!! Or the one with the highest score !!! ##### -- TODO -- ######
		
		# Start off with the ideal next task ID
		next_task_ID = current_tasks[permutation[perm_index]]
		
		if debug > 1:
			print('\n\n--------------------------------------------\nConsidering the following tasks for the next thing:')
			print('Checking permutation %s' % ''.join([str(x) for x in permutation]))
			for ID in filter(None, current_tasks):
				job_index, exp_index, tas_index = parse_ID(ID)
				task = get_task(existing_jobs, jobs, ID)

				print('ID: %s\n- Job:       %s\n- Task Name: %s' % 
					(ID, jobs[job_index]['order'][exp_index], task['name']))
			print('Preferring the next task in job %d' % permutation[perm_index])

		# If this is None, go to the next item in the list
		i = 1
		while next_task_ID == None:
			if debug > 1:
				print('Next task in job is None. Going to next Job')
			next_task_ID = current_tasks[(permutation[perm_index] + i) % n_jobs]
			i+=1

		# Legacy code, which queues the longest experiment next, always.
		# longest_exp = 0
		# next_task_ID = ''
		# for ID in filter(None, current_tasks):
		# 	# Get the time for that experiment
		# 	job_index, exp_index, tas_index = parse_ID(ID)
		# 	experiment_name = jobs[job_index]['order'][exp_index]

		# 	req_slots = get_exp_time(jobs[job_index], experiment_name)
		# 	if req_slots > longest_exp:
		# 		next_task_ID = ID
		# 		longest_exp  = req_slots

		# incriment to the next index for the next loop
		perm_index += 1

		# Store it here so I don't lose it.
		starter_ID = next_task_ID
		if debug > 1:
			print('Next experiment to queue will be %s' % next_task_ID)

		# Construct a mini-schedule for this task, to slide over the main schedule until it fits.
		task = get_task(existing_jobs, jobs, next_task_ID)
		task_schedule = []
		if task['flexible']:
			if debug > 2:
				print('Task %s is flexible. Constructing a bloc for it...' % next_task_ID)
			# get just the next task's slots
			req_slots = task['time']
			task_schedule = [next_task_ID for i in range(req_slots)]

		else:
			# We must create a schedule with all the tasks from that experiment
			job_index, exp_index, tas_index = parse_ID(next_task_ID)
			experiment_name = jobs[job_index]['order'][exp_index]
			experiment = jobs[job_index][experiment_name]
			
			if debug > 2:
				print('Task %s is inflexible. Constructing a pseudo-task of this experiment...' % next_task_ID)
			
			ID = next_task_ID
			
			for task in experiment:
				task_schedule += [ID for i in range(task['time'])]
				ID = incriment_ID(existing_jobs, jobs, ID)
		
		if debug > 2:
			for i, task_ID in enumerate(task_schedule):
				print('Slot: %3d - ID: %s' % (i, task_ID))

		# Try to place the task_schedule into schedule. If two active slots overlap, shift it downstream by a slot and check again.
		## i will be the first slot we try to fill with this task

		# Find the location of the last task in the job
		prev_ID = decriment_ID(jobs, starter_ID)
		if debug > 2:
			print('Searching for the experiment before %s, %s' % (starter_ID, prev_ID))
		last_loc = 0
		n_slots = len(job_schedules[0])
		if prev_ID != None:
			# Start at the end and work forwards
			last_loc = n_slots
			
			while last_loc > 0:
				last_loc -= 1
				slot = [m[last_loc] for n,m in enumerate(job_schedules)]
				if prev_ID in slot:
					break

		if debug > 2:
			print('The last task before %s, %s, was in location %d' % (starter_ID, prev_ID, last_loc))
		
		flag = 1
		for i in range(last_loc+1, n_slots-len(task_schedule)):
			flag = 0
			for j, task_ID in enumerate(task_schedule):
				# Check schedule[i+j] against task_schedule[j]
				slot = [m[i+j] for n,m in enumerate(job_schedules)]
				slot.append(task_ID)

				active = check_active_slot(existing_jobs, jobs, slot)
				if active > 1:
					# Conflicting tasks
					if debug > 3:
						print('When starting from slot %d in the schedule, Slot %d has a conflict' % (i, i+j))
					flag = 1
					break

			if not flag:
				if debug > 1:
					print('Success! Pushing the task schedule into main schedule, starting from slot %d' % i)
				
				# Do that
				for j, task_ID in enumerate(task_schedule):
					# schedule[i+j].append(task_schedule[j][0])
					# Generate the indexes from the task ID
					job_index, exp_index, tas_index = parse_ID(task_ID)
					job_schedules[job_index][i+j] = task_ID
				# Don't check any more slots.
				break
				
		# If we see the flag, that means we checked the entire schedule and couldn't fit it in.
		if flag == 1:
			# print("Sorry! I couldn't fit in the task %s. I'll skip it, " % 
			# 	starter_ID)
			skipped_tasks.append(starter_ID)

		# Now, incriment the current tasks to the next one.
		if task['flexible']:
			next_task_ID = incriment_ID(existing_jobs, jobs, starter_ID)
		else:
			next_task_ID = ID
		if debug > 1:
			print('The next task ID after %s is %s' % (starter_ID, next_task_ID))
		current_tasks = [next_task_ID if y==starter_ID else y for y in current_tasks]

		if debug > 1:
			print('Current tasks are:')
			print(current_tasks)


	# Remove trailing whilespace
	slot = ['' for job in job_schedules]
	active = check_active_slot(existing_jobs, jobs, slot)
	
	while not active:
		for i, j in enumerate(job_schedules):
			job_schedules[i] = job_schedules[i][:-1]
		try:
			slot = [j[-1] for n,j in enumerate(job_schedules)]
			if '999999' in slot:
				slot.remove('999999')

			active = check_active_slot(existing_jobs, jobs, slot)
		except:
			break

	return job_schedules, skipped_tasks

def breed(n_jobs, mutation_rate, threshold, n_individuals, n_tasks, cohort, cohort_results, debug=0):
	'''Takes a set of individuals, and breeds them according to their fitness.'''

	if n_jobs == 1:
		return cohort

	# Take the top 50% of individuals, and breed them randomly to generate the next cohort
	new_cohort = []
	i = False
	j = 0
	mum = cohort[j]
	
	for j in range(len(cohort)//2):
		new_individual = []

		# Mother cycles down the list, moving on after 2 offspring
		if i:
			mum = cohort[j]
		i = not i

		# Dad is a random father from the upper 50%
		dad = rand.randint(0, len(cohort)/2)
		dad = cohort[dad]
		# ensure they're different
		# while dad == mum:
		# 	dad = rand.randint(0, len(cohort))
		# 	dad = cohort[dad]

		y = 0
		which_parent = 0
		while len(new_individual) < n_tasks:
			print('Breeding...')
			# Choose a random integer between a fifth and a third of a chromosome to swap genes for
			n_swap = rand.randint(n_tasks/5,n_tasks/3)
			# Check we have enough genes left to do this
			if y + n_swap >= n_tasks:
				n_swap = n_tasks - y

			# print('New chromosome is now %s' % ''.join( [str(c) for c in new_individual] ))
			
			which_parent = (not which_parent)
			if which_parent:
				new_individual[y:y+n_swap] = mum[y:y+n_swap]
			else:
				new_individual[y:y+n_swap] = dad[y:y+n_swap]

			y += n_swap

		# mutate the individual
		for i, val in enumerate(new_individual):
			if rand.random() < mutation_rate:
				# print('Mutation! Changing value %s' % new_individual[i])
				new_individual[i] = rand.randint(0, n_jobs-1)
				# print('to %s' % new_individual[i])
		
		if debug > 2:
			print('breeding %s and %s' % (''.join([str(c) for c in mum]), ''.join([str(c) for c in dad])))
			print('%s was born' % ''.join([str(c) for c in new_individual]))
			print(len(new_individual))

		new_cohort.append(new_individual)
	
	while len(new_cohort) < len(cohort):
		# Randomly generate new offspring a la abiogenesis
		new_individual = []
		for j in range(n_tasks):
			new_individual.append(rand.randint(0, n_jobs-1))
		new_cohort.append(new_individual)
	
	return new_cohort

def print_schedule(initial_date, existing_jobs, workday_start, workday_end, jobs, individual, work_hours):
	# Get the schedule from the chromosome
	job_schedules, skipped_tasks = generate_schedule(
		initial_date, existing_jobs, jobs, individual, workday_start, workday_end, 0, work_hours=work_hours)	
	
	# I need this later
	day_length = get_5_min_time(24,00)
	n_jobs = len(jobs)

	print('Final schedule is %d slots long' % len(job_schedules[0]))

	# print the schedule.
	tot_active = 0
	actual = 0
	print('Final Schedule:')
	title = ''
	for j, job in enumerate(jobs):
		add = ('  %33s  |' % job['JobName'].center(33))
		title += add
	print('                        |  Night time?  |%s' % title)

	for i in range(len(job_schedules[0])):
		ID = ''
		active = 0

		IDs = ['' for job in range(n_jobs+1)]
		for j, k in enumerate(IDs):
			ID = job_schedules[j][i]
			IDs[j] = ID
			# if len(ID) != 0:
			# 	IDs[j] = ID

		active += check_active_slot(existing_jobs, jobs, IDs)

		tot_active += active
		actual += 1

		night = ''
		for ID in IDs:
			if ID[:2] == '99':
				night = 'Previous'
			if ID == '999999':
				night = 'Night Time.'
				active = 0
			if ID == '999998':
				night = 'Multiples'
			if night != '':
				break
			

		if active == 1:
			active = 'ACTIVE'
		elif active > 1:
			active = 'ERROR!'
		else:
			active = ''

		slot_time = initial_date + datetime.timedelta(minutes=5*i)

		time = datetime.datetime.strftime(slot_time, '%H:%M')
		day  = datetime.datetime.strftime(slot_time, '%a')

		if time == '00:00':
			break_line = '-----------------------------------------'
			for ID in IDs[:-1]:
				break_line += '--------------------------------------'
			print(break_line)

		line = '%5s, %5s |  %6s  |  % 11s  |' % (day, time, active, night)

		for ID in IDs[:-1]:

			task = get_task(existing_jobs, jobs, ID)

			job_index, exp_index, tas_index = parse_ID(ID)
			if exp_index == None:
				exp_index = ''

			experiment_name = ''
			try:
				if task == None:
					name = ''
				else:
					experiment_name = jobs[job_index]['order'][exp_index]
					name = task['name']
					exp_index = str(exp_index+1)
					if len(experiment_name) > 11:
						experiment_name = experiment_name[:9] + '..'
					if len(name) > 15:
						name = name[:13] + '..'
				report = '  %15s - %-15s  |' % (experiment_name, name)
				line += report
			except:
				report = '                  -                  |'
				line += report
		print(line)

	naiive_time = 0.0
	for job in jobs:
		for exp_name in job['order']:
			naiive_time += get_exp_time(job, exp_name)

	eff = 100* tot_active / actual
	print('Efficiency (higher is better) - %d%%' % eff)

	return

def parse_ical_event(event, initial_date):
	# Get the name
	name = str(event['SUMMARY'])+' --- '+str(event['DESCRIPTION'])

	# Get the interval time between the start and end of the event
	start = event['DTSTART'].dt
	end   = event['DTEND'].dt

	# This is a hack workaround to deal with daylight savings bullshit
	localtime = pytz.timezone('Europe/London')
	now = datetime.datetime.now()
	localtime = localtime.localize(now)
	if bool(localtime.dst()):
		print('We are currently in daylight savings time.')
		print(start.strftime('%H:%M'))
		start = start + datetime.timedelta(hours=1)
		print(start.strftime('%H:%M'))
		end   = end   + datetime.timedelta(hours=1)

	interval_time = end - start
	interval_time = interval_time.total_seconds()//(5*60)

	# If the last word in the description is 'False,', then this is an inactive task. Otherwise, it's active.
	active = event['DESCRIPTION'].split(' ')[-1].lower() != 'false'
	
	# Get the first slot equivalent of this event
	# Detect and fix datetime.date objects
	if (type(start)) == datetime.date:
		start = datetime.datetime.combine(start, datetime.datetime.min.time())
		start = start.replace(tzinfo=pytz.timezone('Europe/London'))
		
	first_slot = start - initial_date
	first_slot = int(first_slot.total_seconds()//(5*60))

	task = {'name': name,
			'time': interval_time,
			'active': active,
			'flexible': 0,
			'first_slot': first_slot,
		}

	return task

def parse_csv_event(line, initial_date):
	# Split into columns
	line = line.split(',')
	
	# Get the event name
	name = line[0]

	# If the last word in the description is 'False,', then this is an inactive task
	active = line[6].split(' ')[-1].lower() != 'false'
	
	# Get the start and end time/dates
	start_date, start_time, end_date, end_time = line[1:5]

	# convert strings to datetime objects
	start_time = datetime.datetime.strptime(start_date.strip()+' '+start_time.strip(), '%m/%d/%Y %H:%M')
	end_time   = datetime.datetime.strptime(end_date.strip()+' '+end_time.strip(), '%m/%d/%Y %H:%M')

	start_time = start_time.replace(tzinfo=pytz.timezone('Europe/London'))
	end_time = end_time.replace(tzinfo=pytz.timezone('Europe/London'))

	# Get the interval between them
	interval_time = end_time - start_time
	interval_time = interval_time.total_seconds()//(5*60)

	# compute what slot the event will begin in
	first_slot = start_time - initial_date
	first_slot = int(first_slot.total_seconds()//(5*60))

	# Construct the task
	task = {'name': line[0],
			'time': interval_time,
			'active': active,
			'flexible': 0,
			'first_slot': first_slot,
		}
	return task

def run_scheduler(fnames, destination='./', initial_date=None, existing_tasks=None):
	# Print out debugging info?
	debug = 1

	# print(datetime.datetime.strftime(initial_date, '%m/%d/%Y %H:%M'))
	initial_date = initial_date.replace(tzinfo=pytz.timezone('Europe/London'))
	print(bool(initial_date.dst()))

	# Initialise the schedule
	work_hours    = 2*24
	workday_start = get_5_min_time( 8,00)
	workday_end   = get_5_min_time(16,00)
	day_length    = get_5_min_time(24,00)

	# Mutation rate (fraction)
	mutation_rate = 0.05

	# Threshold for success
	threshold = 0.10

	# Number of individuals in a generation
	n_individuals = 20

	# Read in the job files
	jobs = []
	for fname in fnames:
		job = read_job_file(fname)
		jobs.append(job)

	# how many jobs?
	n_jobs = len(jobs)

	# how many tasks are there in my jobs?
	n_tasks = 0
	for job in jobs:
		for experiment_name in job['order']:
			if job[experiment_name][0]['flexible']:
				n_tasks += len(job[experiment_name])
			else:
				n_tasks += 1

	existing_jobs = []

	# Read in a csv file, if the extension matches
	if existing_tasks[-4:]=='.csv':

		with open(existing_tasks, 'r') as f:
		# Get the headers, just 'cos
			headers = f.readline()
			headers = headers.split(',')
			j=0
			for line in f:
				existing_jobs.append(parse_csv_event(line, initial_date))

	# Or, read in an icalendar file
	elif existing_tasks[-4:]=='.ics':
		file = open(existing_tasks, 'rb')
		cal = Calendar.from_ical(file.read())

		for event in cal.walk('vevent'):
			existing_jobs.append(parse_ical_event(event, initial_date))

	for task in existing_jobs:
		print(task)

	# Each permutation list will be of the length n_tasks, and contain any combination of the numbers 0 - (n_jobs-1)
	# i.e. [ [0,0,0,0], [0,0,0,1], [0,0,0,2], [0,0,1,0], ... [2,2,2,2] ]
	# Generate each permutation list as a number in base (n_jobs) between 00000... and 99999... or whatever (base-1) is
	# This can then be converted to a list of integers that will suggest the next task to attempt
	final_perm = str(n_jobs-1) * n_tasks
	final_perm = str2int(final_perm, n_jobs)
	print('Using a genetic algorithm to search for the best of %.3g different permutations.' % (final_perm))

	# initialise the cohort
	# cohort =  rand.sample(xrange(final_perm), n_individuals) # Doesnt work for large parameter spaces
	# cohort =  [toStr(permutation, n_jobs).rjust(n_tasks, '0') for permutation in cohort]
	cohort = []
	for i in range(n_individuals):
		new_individual = []
		for j in range(n_tasks):
			new_individual.append(rand.randint(0, n_jobs-1))
		cohort.append(new_individual)
	cohort_results = [0 for x in cohort]

	# History
	best_scores = []
	best_score  = 0
	deviations  = []
	best_individuals = []
	n = 0

	# Stop the algorithm after seeing no new minimum for 3 generations
	stop = 0

	print('Generation  - Best - std. dev. - fitness')

	cont = True
	while cont:
		n += 1

		times = []
		# Consider each individual in the cohort 
		for x, permutation in enumerate(cohort):			
			# Evaluate the individual
			
			t0 = time.time()

			job_schedules, skipped_tasks = generate_schedule(
				initial_date, 
				existing_jobs, jobs, 
				permutation, 
				workday_start, workday_end, 
				debug, 
				work_hours=work_hours
				)

			times.append(time.time()-t0)
			perm_index = 0

			cohort_results[x] = len(job_schedules[0])

			if skipped_tasks:
				cohort_results[x] = None
				if debug:
					print('This guy had to skip some tasks. Adding an extra day to the schedule...')
				work_hours += 24
				if debug:
					print('The workday is now %d hours long' % work_hours)

		while None in cohort_results and len(cohort_results)!=0:
			print('This individual had to skip some tasks. Killing the weak.')
			index = cohort_results.index(None)
			del cohort[index]
			del cohort_results[index]

		if len(cohort) <= 1:
			print("'I couldn't find a solution to this set of jobs.")
			print(" I'll run again with debugging enabled to show you what tasks are causing problems.")
			debug = 1
			permutation = []
			for j in range(n_tasks):
				permutation.append(rand.randint(0, n_jobs-1))

			job_schedules, skipped_tasks = generate_schedule(
				initial_date, 
				existing_jobs, jobs, 
				permutation, 
				workday_start, workday_end, 
				debug, 
				work_hours=work_hours
				)
			
			cont = False

		# Save the best individual, std, and best score for each generation
		best_scores.append(min(cohort_results))
		best_individuals.append(cohort[cohort_results.index(best_scores[-1])])
		std = np.std(cohort_results[:int(2*len(cohort_results)/3)])
		deviations.append(std)
		
		# breed cohort - score is the number of slots it needs.
		## Sort by ascending score
		cohort_results, cohort = (list(t) for t in zip(*sorted(zip(cohort_results, cohort))))

		if debug > 1:
			for individual, result in zip(cohort, cohort_results):
				print('%s - %d' % (''.join([str(x) for x in individual]), result))
			print('This cohort took an average of %lfs to generate.' % np.mean(times))
		
		# If the standard deviation of the cohort is less than 20%, we are converged
		print('      %3d   - %4d - %9.2lf - %.2lf' % (n, min(cohort_results), std, std/min(cohort_results)))

		if n-1:
			if min(cohort_results) < best_scores[n-2]:
				stop = 0
			else:
				stop += 1

		if stop >= 5:
			cont = False

		if std/min(cohort_results) < threshold:
			print('Threshold reached!')
			cont = False

		cohort = breed(n_jobs, mutation_rate, threshold, n_individuals, n_tasks, cohort, cohort_results)
		cohort_results = [0 for x in cohort]
		
	#### Done! ####

	best_individual = best_individuals[best_scores.index(min(best_scores))]
	print('The best individual was %s' % ''.join([str(x) for x in best_individual]))

	# print_schedule(initial_date, existing_jobs, workday_start, workday_end, jobs, best_individual, work_hours)

	## Generate a .csv file that can be imported into a google calendar ##

	now = datetime.datetime.now()

	# The name of the csv file to produce
	oname = 'Schedule_%s_%s-jobs.ics' % (now.strftime("%d-%m-%y-%Hh%Mm"), n_jobs) 

	print('Creating a .ics file of this schedule for importing into google calendar.')

	if destination == '':
		destination = os.getcwd()
		destination += '/Schedules'

	oname = destination+'/'+oname
	print('File will be called %s' % oname)

	if not os.path.isdir(destination):
		os.makedirs(destination)


	cal = Calendar()
	cal.add('version', '2.0')
	for j, schedule in enumerate(job_schedules[:-1]):
		# Get the first task in the schedule
		task_ID = filter(None, schedule)[0]
		while task_ID:
			# Get the first and last slots of this task
			start_slot = schedule.index(task_ID)
			end_slot   = len(schedule) - schedule[::-1].index(task_ID)

			# retrieve the task data
			task = get_task(existing_jobs, jobs, task_ID)
			job_index, exp_index, tas_index = parse_ID(task_ID)

			# Compute the date and time of the starting slot
			start_time = initial_date + datetime.timedelta(minutes = (5*start_slot))
			end_time   = initial_date + datetime.timedelta(minutes = (5*end_slot))

			# Construct the csv entry
			# Subject: '<Job Name>, <Experiment Name>'
			# Description: '<Task Name'>
			subject     = '"%s - %s"' % (jobs[j]['JobName'], jobs[j]['order'][exp_index])
			description = '%s - Active? %r' % (task['name'], bool(task['active']))

			# Some calendars (e.g. Outlook) require a globally unique UID. I'll use <JobGen_[start_time]-[end_time]@[device_name]>
			UID = 'JobGen_%s-%s@%s' % (start_time, end_time, socket.gethostname())

			# Build the event
			event = Event()

			event.add('dtstart', start_time)
			event.add('dtend', end_time)
			event.add('summary', subject)
			event.add('description', description)
			event.add('dtstamp', datetime.datetime.now())
			event.add('uid', UID)

			# Add it to the calendar
			cal.add_component(event)

			task_ID = incriment_ID(existing_jobs, jobs, task_ID)

	f = open(oname, 'wb')
	f.write(cal.to_ical())
	f.close()

	### .CSV LEGACY CODE. DISUSED.
	# f = open(oname, 'w')
	# # This seems poorly documented. Use the following format:
	# #        string , MM/DD/YYYY, 24H time  , MM/DD/YYYY, 24H   , bool         , string     , 
	# f.write('Subject, Start Date, Start Time, End Date, End Time, All Day Event, Description, Location, Private \n')

	# # Subject: '<Job Name>, <Experiment Name>'
	# # Description: '<Task Name'>

	# # f.write("Example subject, 08/18/2018, 00:00, 08/18/2018, 01:00, false, 'Description String', , \n")

	# # These will be the date and time of the first slot, i.e. midnight of Sunday, leading into monday.
	# if initial_date == None:
	# 	initial_date = datetime.datetime(now.year, now.month, now.day, minute=0, hour=0)
	# 	initial_date += datetime.timedelta(days=(7 - initial_date.weekday()))	

	# # For each job, loop through the schedule and detect the start and end slots of each task. 
	# # Convert these slot indexes to times, and create a new entry in teh csv file for this event.
	# for j, schedule in enumerate(job_schedules[:-1]):
		
	# 	task_ID = filter(None, schedule)[0] 
		
	# 	while task_ID:
	# 		# Get the first and last slots of this task
	# 		start_slot = schedule.index(task_ID)
	# 		end_slot   = len(schedule) - schedule[::-1].index(task_ID)

	# 		# retrieve the task data
	# 		task = get_task(existing_jobs, jobs, task_ID)
	# 		job_index, exp_index, tas_index = parse_ID(task_ID)

	# 		# Compute the date and time of the starting slot
	# 		start_time = initial_date + datetime.timedelta(minutes = (5*start_slot))
	# 		end_time   = initial_date + datetime.timedelta(minutes = (5*end_slot))

	# 		start_date = start_time.strftime("%m/%d/%Y")
	# 		end_date   = end_time.strftime("%m/%d/%Y")

	# 		start_time = start_time.strftime("%H:%M")
	# 		end_time   = end_time.strftime("%H:%M")

	# 		# Construct the csv entry
	# 		subject     = '"%s - %s"' % (jobs[j]['jobName'], jobs[j]['order'][exp_index])
	# 		description = task['name']

	# 		f.write('%s,%s,%s,%s,%s,,%s - Active? %r,,\n' % 
	# 			(subject, start_date, start_time, end_date, end_time, description, bool(task['active']) )
	# 			)

	# 		task_ID = incriment_ID(existing_jobs, jobs, task_ID)

	# f.close()
