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



from pprint import pprint
import numpy as np
import matplotlib as mpl
import json
import time
import random as rand


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

def get_experiment(ID):
	global jobs

	job_index, exp_index, tas_index = parse_ID(ID)
	experiment_name = jobs[job_index]['order'][exp_index]

	experiment = jobs[job_index][experiment_name]

	return experiment

def get_task(jobs, ID):
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

	# Just double-check ID is a string...
	ID = str(ID)

	if ID == '':
		return None

	job_index = int(ID[:2])
	exp_index = int(ID[2:4])
	tas_index = int(ID[4:])

	job = jobs[job_index]
	try:
		experiment = job[ job['order'][exp_index] ]
		task = experiment[tas_index]
	except:
		task = None

	return task

def incriment_ID(ID):
	'''Tries to incriment to the next task in the experiment. 
	Failing that, incriments to the next experiment in the job. 
	Failing that, returns None'''
	global jobs

	# print('Recieved %s' % ID)

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
	experiment = get_experiment(ID)

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
	if get_task(jobs, new_ID):
		return new_ID
	else:
		# print('Couldnt find that task, returning None')
		return None

def decriment_ID(ID):
	'''Tries to decriment to the previous task in the experiment. 
	If the first task in the experiment, goes to the last task in the previous one.
	If the first experiment in the job, returns None.'''
	global jobs

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
			experiment = get_experiment(construct_ID(job_index, exp_index, '00'))
			tas_index = len(experiment)-1

			return construct_ID(job_index, exp_index, tas_index)

def get_exp_time(job, experiment):
	'''Get the minimum number of slots that an experiment will take to complete'''
	exp_time = 0.0
	for task in job[experiment]:
		exp_time += float(task['time'])
	return exp_time

def check_active_slot(slot):
	'''Takes a slot, loops through the IDs and checks how many are active. Returns int.'''
	active = 0
	for ID in slot:
		task = get_task(jobs, ID)
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

def initialise_day(work_hours, workday_start, workday_end):
	# Store the order like this?
	# order[ 010000, 010000, 010001, ..., 020105 ]
	# Where each slot of the list is 5 minutes.

	# Schedule array. index 0 is the first time slot of the day, and lasts the number of work hours.
	work_hours = get_5_min_time(work_hours)
	schedule = [[] for i in range(work_hours)]

	# This will contain only the schedules for the appropriate jobs.
	n_jobs = len(jobs) + 1
	job_schedules = [['' for i in range(work_hours)] for job in range(n_jobs)]
	# # Also add one for night time slots
	# job_schedules.append(['' for i in range(work_hours)])

	## TODO: Impliment Night time
	# schedule[0] is 00:00 on monday. I want both 00:00-08:00 and 16:00-23:55 to be occupied before we start.
	day_length    = get_5_min_time(24,00)

	# print('A day is %d slots long. I want to start at slot %d and finish at slot %d each day.' % 
	# 	(day_length, workday_start, workday_end))

	# Add in a blocking task, to account for night times
	for i in range(work_hours):
		# We only care about where we are in the day, not the week. Use modulo to reduce this down.
		time = i%day_length
		day  = int(i/day_length)
		# If we are before 8AM
		if time < workday_start:
			schedule[i].append('999999')
			job_schedules[-1][i] = '999999'
		# or after 4PM
		elif time > workday_end:
			schedule[i].append('999999')
			job_schedules[-1][i] = '999999'
		# Or on a weekend
		elif day%7 == 5 or day%7 == 6:
			schedule[i].append('999999')
			job_schedules[-1][i] = '999999'

	return schedule, job_schedules

def generate_schedule(jobs, permutation, debug=0, work_hours=7*24):
	'''Generates a schedule from a given permutation.
	returns:
	schedule, job_schedules, skipped_tasks'''

	# Re-initialise the schedules
	schedule, job_schedules = initialise_day(work_hours, workday_start, workday_end)

	# Re-initialise the current_tasks list
	current_tasks = []
	for i in range(len(jobs)):
		job_index = str(i).rjust(2,'0')
		current_tasks.append(job_index+'0000')

	# Store skipped tasks
	skipped_tasks = []

	# Get this permutation as a list
	# permutation = list(permutation)

	perm_index = 0
	while current_tasks.count(None) != len(current_tasks):
		starter_ID = ''
		# Start with the longest experiment?
		# !!! Or the one with the highest score !!! ##### -- TODO -- ######
		
		# Start off with the ideal next task ID
		next_task_ID = current_tasks[permutation[perm_index]]
		
		if debug:
			print('\n\n--------------------------------------------\nConsidering the following tasks for the next thing:')
			print('Checking permutation %s' % ''.join([str(x) for x in permutation]))
			for ID in filter(None, current_tasks):
				job_index, exp_index, tas_index = parse_ID(ID)
				task = get_task(jobs, ID)

				print('ID: %s\n- Job:       %s\n- Task Name: %s' % 
					(ID, jobs[job_index]['order'][exp_index], task['name']))
			print('Preferring the next task in job %d' % permutation[perm_index])

		# If this is None, go to the next item in the list
		i = 1
		while next_task_ID == None:
			if debug:
				print('Next task in job is None. Going to next Job')
			next_task_ID = current_tasks[(permutation[perm_index] + i) % n_jobs]
			i+=1

		# incriment to the next index for the next loop
		perm_index += 1

		# Store it here so I don't lose it.
		starter_ID = next_task_ID
		if debug:
			print('Next experiment to queue will be %s' % next_task_ID)

		# Construct a mini-schedule for this task, to slide over the main schedule until it fits.
		task = get_task(jobs, next_task_ID)
		task_schedule = []
		if task['flexible']:
			if debug:
				print('Task %s is flexible. Constructing a bloc for it...' % next_task_ID)
			# get just the next task's slots
			req_slots = task['time']
			task_schedule = [[next_task_ID] for i in range(req_slots)]

		else:
			# We must create a schedule with all the tasks from that experiment
			job_index, exp_index, tas_index = parse_ID(next_task_ID)
			experiment_name = jobs[job_index]['order'][exp_index]
			experiment = jobs[job_index][experiment_name]
			
			if debug:
				print('Task %s is inflexible. Constructing a pseudo-task of this experiment...' % next_task_ID)
			
			ID = next_task_ID
			
			for task in experiment:
				# if debug:
				# 	print('Task - %s' % task)
				# 	print('ID   - %s' % ID)

				task_schedule += [[ID] for i in range(task['time'])]
				ID = incriment_ID(ID)
		
		if debug > 1:
			for i in range(len(task_schedule)):
				print('Slot: %3d - ID: %s' % (i, task_schedule[i]))

		# Try to place the task_schedule into schedule. If two active slots overlap, shift it downstream by a slot and check again.
		## i will be the first slot we try to fill with this task

		# Find the location of the last task in the job
		prev_ID = decriment_ID(starter_ID)
		if debug:
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

		if debug:
			print('The last task before %s, %s, was in location %d' % (starter_ID, prev_ID, last_loc))
		

		flag = 0
		for i in range(last_loc+1, n_slots-len(task_schedule)):
			flag = 0
			for j in range(len(task_schedule)):
				# Check schedule[i+j] against task_schedule[j]
				slot = [m[i+j] for n,m in enumerate(job_schedules)]

				active = check_active_slot(slot + task_schedule[j])
				if active >= 2:
					# Conflicting tasks
					#  if debug:
					# 	print('When starting from slot %d in the schedule, Slot %d has a conflict' % (i, i+j))
					flag = 1
					break

			if not flag:
				if debug:
					print('Success! Pushing the task schedule into main schedule, starting from slot %d' % i)
				
				# Do that
				for j in range(len(task_schedule)):
					schedule[i+j].append(task_schedule[j][0])

					job_index, exp_index, tas_index = parse_ID(task_schedule[j][0])
					job_schedules[job_index][i+j] = task_schedule[j][0]
				# Don't check any more slots.

				break
		if flag == 1:
			print("Sorry! I couldn't fit in the task %s. I'll skip it, " % 
				starter_ID)
			skipped_tasks.append(starter_ID)

		# Now, incriment the current tasks to the next one.
		if task['flexible']:
			next_task_ID = incriment_ID(starter_ID)
		else:
			next_task_ID = ID
		if debug:
			print('The next task ID after %s is %s' % (starter_ID, next_task_ID))
		current_tasks = [next_task_ID if y==starter_ID else y for y in current_tasks]

		if debug:
			print('Current tasks are:')
			print(current_tasks)


	# Remove trailing whilespace
	slot = ['' for job in job_schedules]
	active = check_active_slot(slot)
	
	while not active:
		for i, j in enumerate(job_schedules):
			job_schedules[i] = job_schedules[i][:-1]
		
		slot = [j[-1] for n,j in enumerate(job_schedules)]
		if '999999' in slot:
			slot.remove('999999')

		active = check_active_slot(slot)

	return schedule, job_schedules, skipped_tasks

def breed(cohort, cohort_results, debug=0):
	'''Takes a set of individuals, and breeds them according to their fitness.'''

	# Take the top 50% of individuals, and breed them randomly to generate the next cohort
	new_cohort = []
	i = False
	j = 0
	mum = cohort[j]
	while len(new_cohort) < len(cohort):
		new_individual = []

		# Mother cycles down the list, moving on after 2 offspring
		if i:
			j += 1
			mum = cohort[j]
		i = not i

		# Dad is a random father from the upper 50%
		dad = rand.randint(0, len(cohort)/2)
		# ensure they're different
		while dad == mum:
			dad = rand.randint(0, len(cohort)/2)
		dad = cohort[dad]

		y = 0
		which_parent = 0
		while len(new_individual) < n_tasks:
			# Choose a random integer between 1 and half a third of a chromosome to swap genes for
			n_swap = rand.randint(1,n_tasks/3)
			# Check we have enough genes left to do this
			if y + n_swap >= n_tasks:
				n_swap = n_tasks - y

			print('New chromosome is now %s' % ''.join( [str(c) for c in new_individual] ))
			
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
		
		
		if debug:
			print('breeding %s and %s' % (''.join([str(c) for c in mum]), ''.join([str(c) for c in dad])))
			print('%s was born' % ''.join([str(c) for c in new_individual]))
			print(len(new_individual))

		new_cohort.append(new_individual)

	return new_cohort

def print_schedule(jobs, individual, work_hours):
	schedule, job_schedules, skipped_tasks = generate_schedule(jobs, individual, 0, work_hours=work_hours)	
	
	day_length    = get_5_min_time(24,00)

	print('Final schedule is %d slots long' % len(job_schedules[0]))

	# print the schedule.
	tot_active = 0
	actual = 0
	print('Final Schedule:')
	title = ''
	for j, job in enumerate(jobs):
		add = ('  %33s  |' % job['jobName'].center(33))
		title += add
	print('                        |  Night time?  |%s' % title)

	days = ['Mon',
			'Tue',
			'Wed',
			'Thu',
			'Fri',
			'Sat',
			'Sun']

	for i in range(len(job_schedules[0])):
		ID = ''
		active = 0

		IDs = ['' for job in range(n_jobs+1)]
		for j, k in enumerate(IDs):
			ID = job_schedules[j][i]
			IDs[j] = ID
			# if len(ID) != 0:
			# 	IDs[j] = ID

		active += check_active_slot(IDs)

		tot_active += active
		actual += 1

		if '999999' in IDs:
			night = 'Night Time.'
			active = 0
		else:
			night = ''

		if active == 1:
			active = 'ACTIVE'
		elif active > 1:
			active = 'ERROR!'
		else:
			active = ''

		time = i % day_length
		time *= 5
		mm = time%60
		hh = (time - mm)/60
		time = '%02d:%02d' % (hh, mm)

		day = int(i/day_length)%7
		day = days[day]

		if time == '00:00':
			break_line = '-----------------------------------------'
			for ID in IDs[:-1]:
				break_line += '--------------------------------------'
			print(break_line)
		line = '%5s, %5s |  %6s  |  %11s  |' % (day, time, active, night)
		for ID in IDs[:-1]:

			task = get_task(jobs, ID)

			job_index, exp_index, tas_index = parse_ID(ID)
			if exp_index == None:
				exp_index = ''

			experiment_name = ''
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
		print(line)

	naiive_time = 0.0
	for job in jobs:
		for exp_name in job['order']:
			naiive_time += get_exp_time(job, exp_name)

	eff = 100* tot_active / actual
	print('Efficiency (higher is better) - %d%%' % eff)

	return


# ------------------------------Main Bit---------------------------------- #

# Variables #

# Print out debugging info?
debug = 0

# Job files
fnames = [	'CMK-F-1.json',
			# 'CMK-F-1.json',
			# 'CMK-T-2.json',
			'CMK-T-2.json',
			'CMk-FT-1.json'
		]

# Initialise the schedule
work_hours    = 14*24 # 5 day work week
workday_start = get_5_min_time( 8,00)
workday_end   = get_5_min_time(16,00)
day_length    = get_5_min_time(24,00)

# Mutation rate (fraction)
mutation_rate = 0.02

# Threshold for success
threshold = 0.10

# Number of individuals in a generation
n_individuals = 15

# ------------------------------------------------------------------------ #

# Read in the job files
jobs = []
for fname in fnames:
	job = read_job_file(fname)
	jobs.append(job)


# Summarise inputs.
print("I have %d jobs, called:" % len(jobs))
for job in jobs:
	print('- ' + job['jobName'])

print("\nThe tasks we need to get done are: ")
available = []
for job in jobs:
	print('### Job: %s ###' % job['jobName'])

	order = job['order']
	
	for exp_name in order:	
		experiment = job[exp_name]
		print('- Experiment %s, will take minimum %d minutes' % (exp_name, 5*get_exp_time(job, exp_name)))
		for task in experiment:
			#Get task ID
			task_ID = construct_ID(jobs.index(job), job['order'].index(exp_name), experiment.index(task))

			print('-- Task ID: %s' % (task_ID))
			print('    Label:    %-20s\n    Time req: %-5d\n    Active?   %d\n    Flexible? %d' % 
				  (task['name'], task['time']*5, task['active'], task['flexible']))
		print('')

# Initialise the workday
schedule, job_schedules = initialise_day(work_hours, workday_start, workday_end)

# how many jobs?
n_jobs = len(jobs)

# how many tasks are there in my jobs?
n_tasks = 0
for job in jobs:
	for experiment_name in job['order']:
		n_tasks += len(job[experiment_name])

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
		schedule, job_schedules, skipped_tasks = generate_schedule(jobs, permutation, debug, work_hours=work_hours)
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

	while None in cohort_results:
		print('This individual had to skip some tasks. Killing the weak.')
		index = cohort_results.index(None)
		del cohort[index]
		del cohort_results[index]

	if len(cohort) <= 1:
		break

	# Save the best individual, std, and best score for each generation
	best_scores.append(min(cohort_results))
	best_individuals.append(cohort[cohort_results.index(best_scores[-1])])
	std = np.std(cohort_results[:int(2*len(cohort_results)/3)])
	deviations.append(std)
	
	# breed cohort - score is the number of slots it needs.
	## Sort by ascending score
	cohort_results, cohort = (list(t) for t in zip(*sorted(zip(cohort_results, cohort))))

	if debug:
		for individual, result in zip(cohort, cohort_results):
			print('%s - %d' % (''.join([str(x) for x in individual]), result))
		print('This cohort took an average of %lfs to generate.' % np.mean(times))
	
	# If the standard deviation of the cohort is less than 20%, we are converged
	print('      %3d   - %4d - %9.2lf - %.2lf' % (n, min(cohort_results), std, std/min(cohort_results)))

	if n-1:
		if min(cohort_results) == best_scores[n-2]:
			stop += 1
		else:
			stop = 0
	
	if stop >= 10:
		cont = False

	if std/min(cohort_results) < threshold:
		print('Threshold reached!')
		cont = False

	cohort = breed(cohort, cohort_results)
	cohort_results = [0 for x in cohort]

#### Done! ####

best_individual = best_individuals[best_scores.index(min(best_scores))]
print('The best individual was %s' % ''.join([str(x) for x in best_individual]))

print_schedule(jobs, best_individual, work_hours)


exit()

### TODO: Add a calendar export function to push the schedule to a google calendar
cred_file = 'credentials.json'
with open(cred_file) as f:
		credentials = json.load(f)

pprint(credentials)


"""Shows basic usage of the Google Calendar API.
Prints the start and name of the next 10 events on the user's calendar.
"""
store = file.Storage('token.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('calendar', 'v3', http=creds.authorize(Http()))

# Call the Calendar API
now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
print('Getting the upcoming 10 events')
events_result = service.events().list(calendarId='primary', timeMin=now,
                                    maxResults=10, singleEvents=True,
                                    orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    print(start, event['summary'])








