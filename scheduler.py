#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

fnames = [	'CMK-F-1.json',
			'CMK-T-2.json',
			'CMk-FT-1.json'
		]

version = 0


# print out debugging?
debug = 0

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
	if ID == None:
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


def get_task(ID):
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
		task = {'name': 'Night Time',
				'time': 1,
				'active': 1,
				'flexible': 0
			}
		return task

	global jobs

	# Just double-check ID is a string...
	ID = str(ID)

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

	if ID == None:
		return None

	new_ID = list(ID)

	job_index = int(''.join(new_ID[:2]))
	exp_index = int(''.join(new_ID[2:4]))
	tas_index = int(''.join(new_ID[4:]))

	# check code against the length of the experiment list in the job
	if len(job[ job['order'][exp_index] ])-1 > tas_index:
		tas_index += 1
	# check the length of the order list agains the experiment code
	elif len(job['order'])-1 > exp_index:
		tas_index = 0
		exp_index += 1

	new_ID = str(job_index).rjust(2, '0')
	new_ID+= str(exp_index).rjust(2, '0')
	new_ID+= str(tas_index).rjust(2, '0')

	if new_ID == ID:
		new_ID = None

	if get_task(new_ID):
		return new_ID
	else:
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
		task = get_task(ID)
		try:
			active += task['active']
		except:
			True
	return active

def str2int(string, base):
	'''Takes a string form of a number in base <base>, and converts to decimal'''
	string = list(string)

	value = 0
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
	job_schedules = [[[] for i in range(work_hours)] for job in jobs]
	# Also add one for night time slots
	job_schedules.append([[] for i in range(work_hours)])

	day_length = get_5_min_time(24,00)

	# print('A day is %d slots long. I want to start at slot %d and finish at slot %d each day.' %
	# 	(day_length, workday_start, workday_end))

	# Add in a blocking task, to account for night times
	for i in range(work_hours):
		# We only care about where we are in the day, not the week. Use modulo to reduce this down.
		time = i%day_length
		# If we are before 8AM
		if time < workday_start:
			schedule[i].append('999999')
			job_schedules[-1][i].append('999999')
		# or after 4PM
		elif time > workday_end:
			schedule[i].append('999999')
			job_schedules[-1][i].append('999999')

	return schedule, job_schedules



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
	print(job['jobName'])

	order = job['order']

	for exp_name in order:
		experiment = job[exp_name]
		print('Experiment %s, will take minimum %d minutes' % (exp_name, 5*get_exp_time(job, exp_name)))
		for task in experiment:
			#Get task ID
			task_ID = construct_ID(jobs.index(job), job['order'].index(exp_name), experiment.index(task))

			print('Task ID: %s' % (task_ID))
			print('- Label:    %-20s\n- Time req: %-5d\n- Active?   %d\n- Flexible? %d' %
				  (task['name'], task['time']*5, task['active'], task['flexible']))
		print('\n')
	print('\n')


# ------------------------------Main Bit---------------------------------- #

# Initialise the schedule
work_hours = 5*24 # 5 day work week
workday_start = get_5_min_time( 8,00)
workday_end   = get_5_min_time(16,00)
day_length    = get_5_min_time(24,00)

schedule, job_schedules = initialise_day(work_hours, workday_start, workday_end)

# Keep a list of the current experiments that we want to consider as the next task to drop into the schedule.
current_tasks = []
for i in range(len(jobs)):
	job_index = str(i).rjust(2,'0')
	current_tasks.append(job_index+'0000')


# This version is rewritten to satisfy new constraints - i.e. allow for some experiments to not be flexible.
# I'll instead consider inflexible experiments as pseudo-tasks.
# This time, I will try to place the next 'task' that is prefereable, and slide it along the schedule from the beginning until it fits in.
# This version will always queue the longest experiment's next task.
if version == 0:
	# print out debugging?
	debug = 1

	if debug:
		print("\n\nUsing the new version of the scheduler.")

	skipped_tasks = []

	while current_tasks.count(None) != len(current_tasks):
		starter_ID = ''
		# Start with the longest experiment?
		# !!! Or the one with the highest score !!! ##### -- TODO -- ######
		if debug:
			print('\n\n--------------------------------------------\nConsidering the following tasks for the next thing:')
			for ID in filter(None, current_tasks):
				job_index, exp_index, tas_index = parse_ID(ID)
				task = get_task(ID)

				print('ID: %s\n- Job:       %s\n- Task Name: %s' %
					(ID, jobs[job_index]['order'][exp_index], task['name']))

		longest_exp = 0
		next_task_ID = ''
		for ID in filter(None, current_tasks):
			# Get the time for that experiment
			job_index, exp_index, tas_index = parse_ID(ID)
			experiment_name = jobs[job_index]['order'][exp_index]

			req_slots = get_exp_time(jobs[job_index], experiment_name)
			if req_slots > longest_exp:
				next_task_ID = ID
				longest_exp  = req_slots

		# Store it here so I don't lose it.
		starter_ID = next_task_ID
		if debug:
			print('Next experiment to queue will be %s' % next_task_ID)

		# Construct a mini-schedule for this task, to slide over the main schedule until it fits.
		task = get_task(next_task_ID)
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
				if debug:
					print(task)

				task_schedule += [ID for i in range(task['time'])]
				ID = incriment_ID(ID)

		# if debug:
		# 	for i in range(len(task_schedule)):
		# 		print('Slot: %3d - ID: %s' % (i, task_schedule[i]))

		# Try to place the task_schedule into schedule. If two active slots overlap, shift it downstream by a slot and check again.
		## i will be the first slot we try to fill with this task

		# Find the location of the last task in the job
		prev_ID = decriment_ID(starter_ID)
		if debug:
			print('Searching for the experiment before %s, %s' % (starter_ID, prev_ID))
		last_loc = -1
		if prev_ID != None:
			for i in range(len(schedule)-1, -1, -1):
				if prev_ID in schedule[i]:
					last_loc = i
					break

		if debug:
			print('The last task before %s, %s, was in location %d' % (starter_ID, prev_ID, last_loc))

		flag = 1
		for i in range(last_loc+1, len(schedule)-len(task_schedule)):
			# if debug:
			# 	print('Trying to push the new bloc into slot %d...' % i)
			flag = 0
			for j in range(len(task_schedule)):
				# Check schedule[i+j] against task_schedule[j]

				active = check_active_slot(schedule[i+j]+task_schedule[j])
				if active >= 2:
					# Conflicting tasks
					#  if debug:
					# 	print('When starting from slot %d in the schedule, Slot %d has a conflict' % (i, i+j))
					flag = 1
					break

			# If flag == 0
			if not flag:
				if debug:
					print('Success! Pushing the task schedule into main schedule, starting from slot %d' % i)
				# Do that
				for j in range(len(task_schedule)):
					schedule[i+j].append(task_schedule[j][0])

					job_index, exp_index, tas_index = parse_ID(task_schedule[j][0])
					job_schedules[job_index][i+j].append(task_schedule[j][0])
				# Don't check any more slots.

				break
		if flag == 1:
			print("Sorry! I couldn't fit in the task %s. I'll skip it, but please try something else if it still needs to be done." % starter_ID)
			skipped_tasks.append(starter_ID)

		# Now, incriment the current tasks to the next one.
		if task['flexible']:
			next_task_ID = incriment_ID(starter_ID)
		else:
			next_task_ID = ID
		if debug:
			print('The next task ID after %s is %s' % (starter_ID, next_task_ID))
		current_tasks = [next_task_ID if x==starter_ID else x for x in current_tasks]

		if debug:
			print('Current tasks are:')
			print(current_tasks)
		# current_tasks = [None]


# This version is rewritten to satisfy new constraints - i.e. allow for some experiments to not be flexible.
# I'll instead consider inflexible experiments as pseudo-tasks.
# This time, I will try to place the next 'task' that is prefereable, and slide it along the schedule from the beginning until it fits in.
# This version will check all permutations of the experiments.
if version == 1:

	import random as rand

	if debug:
		print("\n\nUsing the brute-force version of the scheduler.")


	# how many tasks are there in my list?
	n_tasks = 0
	# how many jobs?
	n_jobs = len(jobs)

	for job in jobs:
		for experiment_name in job['order']:
			n_tasks += len(job[experiment_name])
	# Each permutation list will be of the length n_tasks, and contain any combination of the numbers 0 - (n_jobs-1)
	# i.e. [ [0,0,0,0], [0,0,0,1], [0,0,0,2], [0,0,1,0], ... [2,2,2,2] ]
	# Generate each permutation list as a number in base (n_jobs). This can then be converted to a list of integers.
	final_perm = str(n_jobs-1) * n_tasks

	final_perm = str2int(final_perm, n_jobs)
	print('In the worst-case, I need to check %d different permutations.' % (final_perm))


	best_schedule = [9999999, []]

	n_individuals = 20
	task_keys = list(range(final_perm))
	cohort =  rand.sample(task_keys, n_individuals)

	for permutation in cohort:
		# Re-initialise the schedules
		schedule, job_schedules = initialise_day(work_hours, workday_start, workday_end)

		# Re-initialise the current_tasks list
		current_tasks = []
		for i in range(len(jobs)):
			job_index = str(i).rjust(2,'0')
			current_tasks.append(job_index+'0000')


		skipped_tasks = []

		# Get this permutation...
		permutation = toStr(permutation, n_jobs)
		permutation = list(permutation.rjust(n_tasks, '0'))

		if debug:
			print('Checking permutation %s' % ''.join(permutation))

		perm_index = 0
		while current_tasks.count(None) != len(current_tasks):
			starter_ID = ''
			# Start with the longest experiment?
			# !!! Or the one with the highest score !!! ##### -- TODO -- ######
			if debug:
				print('\n\n--------------------------------------------\nConsidering the following tasks for the next thing:')
				for ID in filter(None, current_tasks):
					job_index, exp_index, tas_index = parse_ID(ID)
					task = get_task(ID)

					print('ID: %s\n- Job:       %s\n- Task Name: %s' %
						(ID, jobs[job_index]['order'][exp_index], task['name']))

			# Start off with the ideal next task ID
			next_task_ID = current_tasks[int(permutation[perm_index])]
			if debug:
				print('Preferring the next task in job %d' % int(permutation[perm_index]))

			# If this is None, go to the next item in the list
			i = 1
			while next_task_ID == None:
				if debug:
					print('Next task in job is None. Going to next Job')
				next_task_ID = current_tasks[(int(permutation[perm_index]) + i) % n_jobs]
				i+=1

			# incriment to the next index for the next loop
			perm_index += 1

			# Store it here so I don't lose it.
			starter_ID = next_task_ID
			if debug:
				print('Next experiment to queue will be %s' % next_task_ID)

			# Construct a mini-schedule for this task, to slide over the main schedule until it fits.
			task = get_task(next_task_ID)
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
					if debug:
						print(task)

					task_schedule += [[ID] for i in range(task['time'])]
					ID = incriment_ID(ID)

			# if debug:
			# 	for i in range(len(task_schedule)):
			# 		print('Slot: %3d - ID: %s' % (i, task_schedule[i]))

			# Try to place the task_schedule into schedule. If two active slots overlap, shift it downstream by a slot and check again.
			## i will be the first slot we try to fill with this task

			# Find the location of the last task in the job
			prev_ID = decriment_ID(starter_ID)
			if debug:
				print('Searching for the experiment before %s, %s' % (starter_ID, prev_ID))
			last_loc = -1
			if prev_ID != None:
				for i in range(len(schedule)-1, -1, -1):
					if prev_ID in schedule[i]:
						last_loc = i
						break

			if debug:
				print('The last task before %s, %s, was in location %d' % (starter_ID, prev_ID, last_loc))

			flag = 1
			for i in range(last_loc+1, len(schedule)-len(task_schedule)):
				# if debug:
				# 	print('Trying to push the new bloc into slot %d...' % i)
				flag = 0
				for j in range(len(task_schedule)):
					# Check schedule[i+j] against task_schedule[j]

					active = check_active_slot(schedule[i+j]+task_schedule[j])
					if active >= 2:
						# Conflicting tasks
						#  if debug:
						# 	print('When starting from slot %d in the schedule, Slot %d has a conflict' % (i, i+j))
						flag = 1
						break

				# If flag == 0
				if not flag:
					if debug:
						print('Success! Pushing the task schedule into main schedule, starting from slot %d' % i)
					# Do that
					for j in range(len(task_schedule)):
						schedule[i+j].append(task_schedule[j][0])

						job_index, exp_index, tas_index = parse_ID(task_schedule[j][0])
						job_schedules[job_index][i+j].append(task_schedule[j][0])
					# Don't check any more slots.

					break
			if flag == 1:
				print("Sorry! I couldn't fit in the task %s. I'll skip it, but please try something else if it still needs to be done." % starter_ID)
				skipped_tasks.append(starter_ID)

			# Now, incriment the current tasks to the next one.
			if task['flexible']:
				next_task_ID = incriment_ID(starter_ID)
			else:
				next_task_ID = ID
			if debug:
				print('The next task ID after %s is %s' % (starter_ID, next_task_ID))
			current_tasks = [next_task_ID if x==starter_ID else x for x in current_tasks]

			if debug:
				print('Current tasks are:')
				print(current_tasks)
			# current_tasks = [None]

		if skipped_tasks:
			print('Sorry, but I had to skip some tasks to fit everything in.')
			for ID in skipped_tasks:
				job_index, exp_index, tas_index = parse_ID(ID)
				task = get_task(ID)

				print('ID: %s\n- Job:       %s\n- Task Name: %s\n- slots:     %s' %
					(ID, jobs[job_index]['order'][exp_index], task['name'], task['time']))


		while schedule[-1] == [] or schedule[-1] == ['999999']:
			schedule = schedule[:-1]

		print('Permutation %s is %d slots long' % (''.join(permutation), len(schedule)))
		if len(schedule) < best_schedule[0]:
			if len(skipped_tasks) == 0:
				best_schedule = [len(schedule), job_schedules, schedule]

schedule = best_schedule[2]
job_schedules = best_schedule[1]



### OLD VERSION. ALLOWS ALL TASKS TO HAVE GAPS BETWEEN THEM ###
if version == 2:
	# test that we can grab the required time for an experiment properly
	print('\n\nThe first experiments will take:')

	longest_exp = 0
	next_task_ID = ''

	for job in jobs:
		experiment = job['order'][0]

		exp_time = get_exp_time(job, experiment)

		print('\nJob: %s (%s)\nExperiment: %s -- Time: %d min\n' %
			(job['jobName'], str(jobs.index(job)).rjust(2, '0'), experiment, exp_time*5))
		if exp_time > longest_exp:
			longest_exp = exp_time
			next_task_ID = construct_ID(jobs.index(job), 0, 0)
	# This works fine.

	print('Task %s is the first step in the longest experiment' % next_task_ID)

	# Set this to the first slot of the schedule.
	schedule[0].append(next_task_ID)

	job_index = int(''.join(list(next_task_ID)[:2]))
	job_schedules[job_index][0].append(next_task_ID)

	print('\n------------------------------\n')

	# Loop through the schedule
	for i in range(work_hours):
		print('-- Slot %d' % i)
		if current_tasks.count(None) == len(current_tasks):
			print('Completed all our jobs!')
			break

		# Figure out which of the available experiments are next, by checking against the schedule for what the latest is
		slot = schedule[i]
		# Write out the state of the slot
		print('Current tasks are: %s' % current_tasks)
		print('Current slot contains:')
		for ID in slot:
			task = get_task(ID)
			print('ID: %s --- Active: %d' % (ID, task['active']))

		# Check that the last task we were looking at has been fully allocated
		for job in jobs:
			job_index = str(jobs.index(job)).rjust(2, '0')

			# Look at the previous slot
			for ID in schedule[i-1]:
				# If the slot's ID matches the job code, grab the ID.
				if ID[:2] == job_index:
					print('Considering ID %s for slot %d' % (ID, i))
					# Check if the task has filled its required slots. Start by grabbing the task
					task = get_task(ID)
					# Check that it's an active task
					if task['active']:
						# Check that the ID occurs the right number of times
						if sum(row.count(ID) for row in schedule) < task['time']:
							print('This task needs more time: %s. Adding it to the next slot.' % ID)
							# Get the next slot in the schedule, and pop it with this task ID
							schedule[i].append(ID)
							job_schedules[int(job_index)][i].append(ID)

						# If it has filled the required slots, incriment the current_tasks entry and continue the loop without passing
						else:
							print('Required slots filled for task %s.' % ID)

							new_ID = incriment_ID(ID)

							print('Next task ID for that job is %s...' % new_ID)

							current_tasks[int(job_index)] = new_ID
							task = get_task(new_ID)
							if task != None:
								print('The next task is (active? %d), and takes %d slots.' % (task['active'], task['time']))
								# if inactive, add the proper number of elements to the list
								start_index = i
								while (not task['active']):
									print('Popping an inactive task, %s, to the queue, from %d to %d' %
										(new_ID, start_index+1, start_index+1+task['time']))
									print('---')
									for j in range(start_index, start_index+task['time']):
										print('Popping %s to slot %d...' % (new_ID, j))
										schedule[j].append(new_ID)
										job_schedules[int(job_index)][j].append(new_ID)
										print(schedule[j])

									start_index+= task['time']

									# Incriment the ID again
									new_ID = incriment_ID(new_ID)
									current_tasks[int(job_index)] = new_ID
									task = get_task(new_ID)

									# Check if we're finished with that job
									if task == None:
										# print('Next task is None!')
										break

		# Re-grab the current slot
		slot = schedule[i]


		print('Finished first loop. Searching for best next tasks. Slot is currently:')
		print(slot)
		# We need to figure out what task to do next. I'll prefer tasks from longer experiments.
		longest_exp = 0
		next_task_ID = ''

		for ID in current_tasks:
			task = get_task(ID)
			# If the task
			# First determine what the active tasks are.
			if task != None:
				# We want to only consider tasks that fill two criteria:
				# - Active tasks
				# - If a previous inactive task, we must check that enough time has passed that it's completed.
				# I can do the latter by checking that the slot doesnt contain the previous ID in the sequence
				if task['active']:
					prev_ID = list(ID)
					last_digits = ''.join(prev_ID[-2:])
					last_digits = int(last_digits) - 1 # THIS CAN BE NEGATIVE! but I think it should be ok...
					last_digits = str(last_digits).rjust(2,'0')

					prev_ID = prev_ID[:4] + list(last_digits)
					prev_ID = ''.join(prev_ID)

					print('ID: %s --- previous ID: %s\nslot:' % (ID, prev_ID))
					print(slot)

					if not prev_ID in slot:
						print('Previous ID not found in slot!')
						## SELECTION CRITERIA CAN GO HERE RELATIVELY EASILY! ##
						# See if it's the longest available experiment
						if task['time'] > longest_exp:
							next_task_ID = ID
							longest_exp = task['time']
					else:
						True
						print('The waiting period is not over.')
			print('---')

		print('Checking for activity in this slot...')
		# Is this slot active?
		active_slot = 0
		for ID in slot:
			task = get_task(ID)
			active_slot += task['active']
		if active_slot:
			True
			print('This slot is currently active.')
		else:
			print('This slot is inactive, so can take another task. Adding preferred task, [%s]...' % next_task_ID)
			if next_task_ID != '':
				print('Adding in task %s' % next_task_ID)
				schedule[i].append(next_task_ID)

				job_index = ''.join(list(next_task_ID)[:2])

				job_schedules[int(job_index)][i].append(next_task_ID)


		print('Current slot contains:')
		active_slot = 0
		for ID in slot:
			task = get_task(ID)
			print('ID: %s --- Active: %d' % (ID, task['active']))
			active_slot += task['active']
		print('-----------')

# Truncate the schedule to trim off empty slots at the end
while schedule[-1] == [] or schedule[-1] == ['999999']:
	schedule = schedule[:-1]
	for i in range(len(job_schedules)):
		job_schedules[i] = job_schedules[i][:-1]

print('Final schedule is %d slots long' % len(schedule))

# print the schedule. Currently hardcoded to accept only 3 jobs
tot_active = 0
print('Final Schedule:')
print('                              |  Job 00  |  Job 01  |  Job 02  |  Night time?')
for i in range(len(schedule)):
	ID = ''
	active = 0

	IDs = ['' for job in jobs]
	for j in range(len(jobs)):
		ID = job_schedules[j][i]
		active += check_active_slot(ID)
		if len(ID) != 0:
			IDs[j] = ID[0]

	if '999999' in schedule[i]:
		night = 'Night Time.'
	else:
		night = ''

	tot_active += active

	if active == 1:
		active = 'ACTIVE'
	elif active > 1:
		print('active returned %d' % active)
		active = 'ERROR!'
	else:
		active = ''

	time = i % day_length
	time *= 5
	mm = time%60
	hh = (time - mm)/60
	time = '%02d:%02d' % (hh, mm)

	if time == '00:00':
		print('-----------------------------------------------------------------------------')
	print('%5d, Time: %5s |  %6s  |  %6s  |  %6s  |  %6s  |  %s' % (i, time, active, IDs[0], IDs[1], IDs[2], night))
if skipped_tasks:
	print('Sorry, but I had to skip some tasks to fit everything in.')
	for ID in skipped_tasks:
		job_index, exp_index, tas_index = parse_ID(ID)
		task = get_task(ID)

		print('ID: %s\n- Job:       %s\n- Task Name: %s\n- slots:     %s' %
			(ID, jobs[job_index]['order'][exp_index], task['name'], task['time']))


# tot_active = 0
# print('Total Schedule:')
# for i in range(len(schedule)):
# 	if check_active_slot(schedule[i]) == 1:
# 		tot_active += 1
# 		active = 'ACTIVE'
# 	elif check_active_slot(schedule[i]) > 1:
# 		active = 'ERROR'
# 	else:
# 		active = ''
# 	print('Slot %3d -- %6s -- %s' % (i, active, schedule[i]))


naiive_time = 0.0
for job in jobs:
	for exp_name in job['order']:
		naiive_time += get_exp_time(job, exp_name)

actual = len(schedule)

# print('(req. time)/(sum exp. times) = (%d min/%d min), or %d%%' % (actual*5, naiive_time*5, (actual / naiive_time)*100))

eff = 100* tot_active / actual
print('Efficiency (higher is better) - %d%%' % eff)









