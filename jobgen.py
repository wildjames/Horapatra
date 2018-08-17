#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script should be a temporary script that takes a human 
#  input and converts it to the format I'll save jobs as.
# For now, this will be a dict of lists, saved to file as JSON?
#
#
# The naming hierarchy of the jobs should be:
# Job
## Experiment
### Task
# Jobs are executed in any order, overlapping each other. And experiment and task within a job must be executed in the orders given.
#
# job{ experiment0: [task0{name, time, active}, task1task0{name, time, active}, taskntask0{name, time, active}], 
#      experiment1: [task0{name, time, active}, task1task0{name, time, active}, taskntask0{name, time, active}], 
#      order: [experiment0, experiment1],
#	   jobName: 'Job Name'
#     }

import json

# I need a way of ordering the experiments. Have a variable to store the order?
# A list wouldn't store the name of the experiment, so I'd need a second list to 
# pass about the names. This is obviously not ideal.
job = { 
	'jobName': '',
    'order': []
    }

job['jobName'] = raw_input("What would you like to call the job?: ")

cont = 'y'
newTask = 'y'
while cont == 'y':
	ex_name = raw_input('Experiment Label: ')
	# Create the experiment slot in the job dictionary
	job['order'].append(ex_name)
	job[ex_name] = []

	flex = int(raw_input('Is this experiment flexible (0/1): '))

	newTask = 'y'
	while newTask == 'y':
		# Can be any string
		T_name = raw_input('Task Label: ')
		
		# Check it's binary
		active = raw_input('Is this task active or inactive? 1/0: ')
		while active != '1' and active != '0':
			active = raw_input('Is this task active or inactive? 1/0: ')
		active = int(active)

		# 5 min incriments. Check that it's a integer
		time = raw_input('Time to complete task (5 minute incriments): ')
		time = int(time)
		while time%5 != 0:
			time += 1


		# Save as a dict
		task = {
			'name': T_name,
			'active': active,
			'time': time,
			'flexible': flex
			}
		# Save that bad boy
		job[ex_name].append(task.copy())

		newTask = raw_input('Add another task? y/n: ').lower()

	cont = raw_input('Would you like to add an experiment? y/n: ').lower()

# Dump the data to a JSON file, with the jobname as the filename
j = json.dumps(job, indent = 4)
fname = job['jobName'].replace(' ', '_') + '.json'
f = open(fname, 'w')
print >> f, j
f.close()