#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.graphics.instructions import Canvas
from kivy.graphics.instructions import InstructionGroup

from os import listdir
# kv_path = './kv/'
# for kv in listdir(kv_path):
#     print('Built %s' % (kv_path+kv))
#     Builder.load_file(kv_path+kv)

class WriteJobButton(Button):
    pass

class JobNameTextInput(TextInput):
    pass

class NewExpButton(Button):
    pass

class NewTaskButton(Button):
    pass

class NewTaskTextInput(TextInput):
    pass

class ExpButton(Button):
    def build(self):
        self.exp_name = ''

    def remove_experiment(self):
        for i in dir(self.parent.parent.parent):
            print(i)
        self.parent.parent.parent.remove_experiment(self.exp_name)


class NewExpTextInput(TextInput):
    pass

class ReportTable(GridLayout):
    pass

class RowText(Label):
    pass

class BlankRow(Label):
    pass

class ActiveLabel(Button):
    def build(self):
        self.exp_name = ''
        self.task_index = 0

    def verify(self):
        self.parent.parent.parent.remove_task(self.exp_name, self.task_index)

class Container(GridLayout):
    def __init__(self, **kwargs):
        super(Container, self).__init__(**kwargs)

        self.labels = []

        self.job = {'JobName': 'Default', 'order': []}

        self.exit_button = Button(text='Done', size_hint=(None, None), height=30, width=75)
        self.ids.LastRow.add_widget(self.exit_button)

        self.Table = ReportTable()
        self.ids.ReportBox.add_widget(
            self.Table
            )

    def update_report(self):
        '''Construct a table of experiments.
        Rather than updating the table with every change, redraw the whole thing since it's cheap.'''

        job = self.job
        order = job['order']

        try:
            self.ids.ReportBox.remove_widget(self.Table)
        except:
            pass

        # Reinitialise the table
        self.Table = ReportTable()

        # Repopulate the table
        for exp_name in order:
            experiment = job[exp_name]

            # How long will this experiment take?
            exp_time = 0.0
            for task in experiment:
                exp_time += float(task['time'])

            # Create an experiment button
            self.btn = ExpButton(text=('%s - %d min' % (exp_name, exp_time)))
            self.btn.exp_name = exp_name

            # Add it to the table
            self.Table.add_widget(self.btn)

            for i, task in enumerate(job[exp_name]):
                if i > 0:
                    self.Table.add_widget(BlankRow())

                self.Table.add_widget(  RowText(text=task['name'] ) )

                self.active_text = ActiveLabel(text=str(task['active']))
                self.active_text.exp_name = exp_name
                self.active_text.task_index = i
                self.Table.add_widget(self.active_text)

                self.Table.add_widget(  RowText(text=str(task['flexible']) ) )

                self.Table.add_widget(  RowText(text=str(task['time']) ) )

        self.ids.ReportBox.add_widget(self.Table)

    def remove_experiment(self, exp_name):
        # Remove the entry from the dict
        del self.job[exp_name]
        # and the reference from the order list
        self.job['order'] = [ x for x in self.job['order'] if (x!=exp_name) ]
        # then update the report table
        self.update_report()

    def update_flexible(self):
        '''When flexible is toggled, update the whole experiment.'''
        exp_name = self.ids.NewExpInput.text

        try:
            for i, task in enumerate(self.job[exp_name]):
                self.job[exp_name][i]['flexible'] = self.ids.Flex.state=='down'
        except:
            True
        self.update_report()

    def write_to_file(self):
        '''Write the job to the specified file'''

        # Check that the job has been named.
        if self.ids.JobNameInput == '':
            self.ids.JobNameInput.hint_text = 'Please enter a job name!'
            return
        if self.job['order'] == []:
            return

        # Get the filename
        self.job['JobName'] = self.ids.JobNameInput.text

        j = json.dumps(self.job, indent = 4)
        fname = './Jobs/'+self.job['JobName'].replace(' ', '_') + '.json'
        f = open(fname, 'w')
        f.write(j)
        f.close()

        self.popup = Popup(title='', content=Label(text="Done!"), size_hint=(.3, .3))
        self.popup.open()

    def remove_task(self, exp_name, task_index):
        self.job[exp_name][task_index]['active'] = (not self.job[exp_name][task_index]['active'])
        self.update_report()

    def add_new_task(self):
        # First, check that the inputs are valid
        name = self.ids.TaskName.text
        duration = self.ids.TaskDuration.text
        active = self.ids.Active.state

        flag = 0
        try:
            duration = int(duration)
            5/duration
        except:
            self.ids.TaskDuration.text = ''
            self.ids.TaskDuration.hint_text = 'Invalid Time!'
            flag = 1

        if self.ids.NewExpInput.text == '':
            self.ids.NewExpInput.text = ''
            self.ids.NewExpInput.hint_text = 'Please enter a Name!'
            flag = 1

        if self.ids.TaskName.text == '':
            self.ids.TaskName.text = ''
            self.ids.TaskName.hint_text = 'Please enter a Name!'
            flag = 1

        # If any of the flags were raised, dont save the task.
        if flag:
            return

        # If we are ok, construct the task
        task = {'name': name,
                'time': duration,
                'active': active=='down',
                'flexible': self.ids.Flex.state=='down'
                }

        # Commit to the Job. This is in a try statement to catch the first task in an experiment.
        try:
            self.job[self.ids.NewExpInput.text].append(task)
        except:
            self.job[self.ids.NewExpInput.text] = []
            self.job['order'].append(self.ids.NewExpInput.text)
            self.job[self.ids.NewExpInput.text].append(task)

        # Update the report
        self.update_report()

# class JobGeneratorApp(App):

#     def build(self):
#         self.title = 'Job Generator'
#         return Container()
