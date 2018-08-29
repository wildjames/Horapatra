#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Modules kivy needs
from kivy.config import Config
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.graphics.instructions import Canvas
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.dropdown import DropDown
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

# Modules I need
import json
from datetime import date, timedelta
import datetime
from functools import partial
import threading

# System libraries
import sys
import os

# My libraries
import genetic_scheduler as sched
import datepicker
import JobGenerator

kv_path = './kv/'
for kv in os.listdir(kv_path):
    print('Built %s' % (kv_path+kv))
    Builder.load_file(kv_path+kv)



class CustomDropDown(DropDown):
    pass

class JobButton(Button):
    def build(self):
        self.job_name = 0

    def remove_job(self):
        self.parent.parent.parent.remove_job(self.job_name)

class DropDownButton(Button):
    pass

class ReportTable(GridLayout):
    pass

class ExperimentButton(Button):
    def build(self):
        self.job_name = ''
        self.exp_name = ''

    def preview_experiment(self):
        app.root.preview_experiment(self.job_name)

class JobTable(GridLayout):
    pass

class RowText(Label):
    pass

class BlankRow(Label):
    pass

class ExistingEventPicker(BoxLayout):
    def getcwd(self):
        return os.getcwd()

    def load(self, path, selection):
        if selection != []:
            app.root.existing = os.path.join(path, selection[0])
            file = selection[0].split('/')[-1]
            app.root.ids.ExistingFile.text = file
        else:
            app.root.existing = ''
            app.root.ids.ExistingFile.text = ''

        ### Close the popup
        self.parent.parent.parent.dismiss()

class PrimaryWindow(GridLayout):
    def __init__(self, **kwargs):
        super(PrimaryWindow, self).__init__(**kwargs)
        
        # Set the minimum window width?

        # Get the dropdown box ready
        self.dropdown = CustomDropDown()
        self.ids.mainbutton.JobName = ''
        self.ids.mainbutton.bind(on_release=self.dropdown.open)
        self.dropdown.bind(
            on_select=lambda instance, x: self.add_job(x)
            )

        # Get the existing jobs
        self.json_path = 'Jobs/'
        self.update_dropdown()

        # Some stuff for the scheduler part
        self.dest = os.path.dirname('./schedules/')
        self.existing = ''
        self.ids.ExistingFile.text = self.existing

        # Track the jobs we want to optimise, and initialise the table that reports what we have so far
        self.jobList = []

        # Initialise the start date of the schedule as the next monday from today
        now = datetime.datetime.now()
        initial_date = datetime.datetime(now.year, now.month, now.day, minute=0, hour=0)
        initial_date += datetime.timedelta(days=(7 - initial_date.weekday()))
        # and set the label to its value
        self.date = initial_date
        self.date_string = self.date.strftime("%a, %Y-%m-%d")
        self.ids.DateLabel.text = 'Start Date: '+self.date_string

        self.update_job_list()
        # Schedule the updates
        Clock.schedule_interval(self.update_dropdown, 1)
        Clock.schedule_interval(self.update_job_list, 10)

    def update_dropdown(self, *args):
        # Instantiate the dropdown menu for job JSONs in our folder
        self.dropdown.clear_widgets()
        
        fnames = []
        
        for file in os.listdir(self.json_path):
            if '.json' in file:
                fnames.append(file[:-5])

        fnames.sort()

        for i in fnames:
            self.dropdown.add_widget(
                DropDownButton(text=i
                    )
                )

    def get_job(self, fname):
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
                task['time']     = int(task['time'])
        return job

    def get_exp_time(self, job, experiment):
        '''Get the minimum number of slots that an experiment will take to complete'''
        exp_time = 0.0
        for task in job[experiment]:
            exp_time += float(task['time'])
        return exp_time

    def get_existing(self):
        self.popup = Popup(title='Existing schedule picker',
            content=ExistingEventPicker(),
            size_hint=(0.7, 0.7)
            )

        self.popup.content.ids.exit_button.bind(
            on_release=self.popup.dismiss
            )

        self.popup.open()

    def update_job_list(self, *args):
        # Reset the list
        self.ids.JobReportBox.clear_widgets()

        self.JobsTable = JobTable()

        # Repopulate the list
        j=0
        for job in self.jobList:
            # Job name cell
            btn = JobButton(text=job[:-5])
            btn.job_name = j
            self.JobsTable.add_widget(btn)

            # retrieve job data
            job_data = self.get_job(self.json_path+job)

            # Loop through each experiment and get the length of it, then add that here
            for i, exp_name in enumerate(job_data['order']):
                exp_length = self.get_exp_time(job_data, exp_name)
                exp_length = '%dh:%dm' % (int(exp_length)//60, int(exp_length)%60)
                
                # Fill in the job column as blank
                if i:
                    self.JobsTable.add_widget(BlankRow())
                
                # self.JobsTable.add_widget(RowText(text=exp_name, size_hint_x=1.5))
                self.ExpButton = ExperimentButton(text=exp_name, size_hint_x=1.5)
                self.ExpButton.job_name = job
                self.ExpButton.exp_name = exp_name
                self.JobsTable.add_widget(self.ExpButton)

                self.JobsTable.add_widget(RowText(text=exp_length, size_hint_x=0.5))
            j += 1
        
        # Push to the visible window
        self.ids.JobReportBox.add_widget(self.JobsTable)

    def remove_job(self, job):
        del self.jobList[job]
        self.update_job_list()

    def preview_experiment(self, job_name):
        print(job_name)
        job = self.get_job(self.json_path+job_name)

        order = job['order']

        # Reinitialise the table
        self.ExperimentPreview = ReportTable()
        
        # Repopulate the table
        for exp_name in order:  
            experiment = job[exp_name]

            # How long will this experiment take?
            exp_time = 0.0
            for task in experiment:
                exp_time += float(task['time'])
            
            # Create an experiment button, and add it to the table
            self.ExperimentPreview.add_widget(
                Label(
                    text=( '%s\n%d min' % (exp_name, exp_time) ) )
                )

            for i, task in enumerate(job[exp_name]):
                if i > 0:
                    self.ExperimentPreview.add_widget(BlankRow())

                self.ExperimentPreview.add_widget(  RowText(text=task['name'] ) )
                
                self.ExperimentPreview.add_widget(  RowText(text='%r' % bool(task['active']) ) )
                
                self.ExperimentPreview.add_widget(  RowText(text='%r' % bool(task['flexible']) ) )
                
                self.ExperimentPreview.add_widget(  RowText(text=str(task['time']) ) )

        content = ScrollView(size_hint_y=1)
        content.add_widget(self.ExperimentPreview)

        self.popup = Popup(title='Job Preview',
            content = content,
            size_hint= (0.9, 0.7)
            )

        self.popup.open()


    def initial_date(self, x):
        self.date = x
        self.date_string = self.date.strftime("%a, %Y-%m-%d")
        self.ids.DateLabel.text = 'Start Date: '+self.date_string
        self.popup.dismiss()

    def select_date(self):
        self.popup = Popup(title='Select a start date for the schedule',
            content=datepicker.DatePicker(),
            size_hint=(None, None), 
            size=(400, 400)
            )

        self.popup.content.exit_button.bind(on_release=lambda x: self.initial_date(self.popup.content.date))

        self.popup.open()

    def close(self):

        app.stop()

    def create_job(self):
        self.popup = Popup(title='Job Generator',
            content=JobGenerator.Container(),
            size_hint=(0.95, 0.95)
            )

        self.popup.content.exit_button.bind(
            on_release=self.popup.dismiss
            )

        self.popup.open()

    def add_job(self, JobName):
        if JobName != '':
            self.jobList.append(JobName+'.json')
            self.update_job_list()

    def generate_schedule(self):
        if self.jobList == []:
            print('Empty Job List!')
            return

        # print('Using the following arguments to generate a schedule:')
        # print('Genetic: %s' % (self.ids.GeneticButton.state=='down'))
        # print('Jobs:')
        # for job in self.jobList:
        #     print('- %s' % job)
        # print('')

        # Construct the arguments in the right format to pass to the scheduler
        fnames = [self.json_path+x for x in self.jobList]
        initial_date = datetime.datetime.combine(self.date, datetime.datetime.min.time())
        self.dest = os.path.dirname(self.existing)

        try:
            if self.thread.is_alive():
                print("I'm already optimising a schedule! If you REALLY need to kill it, close the main app window.")
                return
        except:
            pass

        self.thread = threading.Thread(
            target=sched.run_scheduler, args=(fnames, self.dest, initial_date, self.existing)
            )
        self.thread.daemon = True
        self.thread.start()

class SchedulerApp(App):

    def build(self):
        self.title = 'Big Booty Bitches'
        return PrimaryWindow()

if __name__ in '__main__':
    app = SchedulerApp()
    app.run()