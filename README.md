# Horapatra
This is a scheduling algorthim, written to help in arranging overlapping chemistry experiments in the most efficient way we can. 

The name is a portmanteau of two historical figures - Cleopatra (not the queen) was famously an ancient alchemist. From wikipedia:

> Cleopatra the Alchemist who likely lived during the 3rd century, was a Greek Egyptian alchemist, author, and philosopher. She experimented with practical alchemy but is also credited as one of the four female alchemists that could produce the Philosopher's stone. She is considered to be the inventor of the Alembic, an early tool for analytic chemistry.

The other component is from the Horae, the greek gods of the passage of time, from which we get the word "hours". 

## Job Structure
The code should be able to take an arbitrary number of jobs, and insert them into a workday around each other in the most optimal way. A job has the following structure:

- Job
  - Experiment 0
    - Task 0
    - Task 1
    - ...
  - Experiment 1
    - Task 0
    - ...
  - Experiment N
    - Task 0
    - ...

The script `jobgen.py` is used to take user input and covert to the JSON format that we store job data as.

## Requirements
Tasks are ordered within an experiment, and experiments are in turn ordered within a job. Jobs, however, are unordered, hence this script.

Each experiment can be either flexible or iflexible, in that it might be important that the tasks in an experiment MUST proceed directly form one to the next. This is defined by the user when defining the job parameters. If the task is flexible, this flags that we can do one step and move one whenever it is convenient rather than immediately.

The tasks themselves can also be either active or inactive. Only one task can be active at a time, but multiple experiments can be in an inactive phase at once (e.g. a reaction might take 6 hours to proceed, but doesn't need constant surveillance)

The final schedule should account for the length of the working day, and weekends. 

> TODO? Make it push in a 5 minute slot between active tasks to ensure that the schedule isn't too tight to follow?

## Schedule Solving 
The code was intentionally structured to recieve some preferred next job to push into the schedule at the first possible slot, then do that. If no slot could be found, an extra workday would be added to the schedule template in an effort to remedy this. In this way, the schedule produced is largely dependant on the input permutation of which jobs to pop in next.

## Optimisation Method
The main issue with this project was how to decide which task to prefer to queue for the next insertion. Because this is a problem in which we are searching for the optimum permutation, not an optimum value, (therefore, the parameter space is highly complex - a small change can propegate to a significant difference in solution) I could not think of an easy method to search all possible permutations of job order. For example, with 2 jobs each of 3 experiments and 3 (flexible) tasks, a very limited version of the problem, there would be 262,143 different permutations to check. More realistic examples become fairly prohibitive in calculation time, expecially as the required time to generate a schedule increases as more jobs are supplied.

Initially, the code followed a simple prescription; the longest experiment available was the preferred one. However, while this does generally produce a servicable schedule, it fails to robustly find the *best* schedule. To this end, I designed a genetic algortihm that breeds better schedules. However, due to having to generate multiple schedules (typical generations only need to be 10-20 individuals, but this still increases the processing time by a factor of 10-20), this is much more expensive for instances with few jobs to place.

Each permutation is treated as a "chromosome", and is evaluated. The fitness of each is the length of the schedule it produces, and the top 50% are bred together. Each takes two random partners and produces an offspring with them, by taking subsequent chunks of each (of random length between 1 and 10 genes long) until the child is fully formed. Convergence is reached if the cohort becomes too inbred (the standard deviaiton falls below 10% of the best schedule length), or if no change is seen for 10 generations. This version of the code typically takes several minutes to run, mostly due to the long time it takes to evaluate an individual which can be on the order of 1-2 seconds per chromosome.

## Usage
The GUI follows a few steps. From the beginning;
- Create Jobs
- Add jobs to queue
- Add previous events
- Set start date
- Generate Schedule
- Import result into your calendar


### Creating a Job
Here, a new experiment can be defined by filling in the box. When the `Add Task` button is clicked, that task is added to the experiment name in the input box. This can be done 'out of order', i.e. you can add tasks to a new experiment, and go back and add more tasks to a previous experiment. Don't forget to define the duration, and flag for if each task is active or inactive (this can be toggled by clicking the labels, though). There is also a `flexible` tag, which tells the code that the tasks in that experiment don't absolutely need to be next to each other in the final schedule. This can also be retrospectively toggled, by re-entering the experiment name and clicking the flexible button. The name of the task, and its duration are not alterable after entry, but this could probably be implimented if needed. For now, it's easy enough to just delete the experiment and re-enter the fields.

Finally, click the `Commit to file` button to save your job. Don't forget to set a memorable name so you can find it later.

### Add Jobs
To add a job to the queue, click the `Add Job` button to open a drop-down box. This should contain any jobs you defined in the `Create Job` popup. Clicking a jobs name adds it to the queue, and pushes it to the main table. Clicking on a job in the table will remove it. Note that the queue can have duplicate jobs in it, but they will create events with the same names in the final calendar.

### Add previous events
It's likely that you will have events in your calendar that you'd like the schedule to work around. To do this, you must first get your calendar in CSV form. When writing this, I didn't realise that google calendar doesnt export .csv, only .ical. I will re-write this part of the code to accept .ical, but for now, this section is considered broken.

### Set start date
Easy enough, click the button and select the date from the calendar. The default start date is set to the next monday.

### Generate Schedule
Clicking this button launches the optimisation code. This is a genetic algoithm, in an attempt to explore the massive parameter space created by the problem, and 'breeds' schedules to have as short a length as possible. This can take a while, so don't close the main window until it's done.

When the program is finished, you should have a new schedule .csv in the Schedules directory. This contains the information needed to import the events into your calendar.

### Importing the calendar
Navigate to your [import settings](https://calendar.google.com/calendar/r/settings/import), and upload the file there. Choose which calendar you want to add it to, and click import to push them all in. Alternatively, double-clicking an .ics file should import the events into your calendar program, if you have one (e.g. Calendar on OSX).

## Future Work
The project is currently incomplete. Plans are to integrate google calendar, to allow users to click a link that imports the generated schedule into their calendar automatically, rather than having to either copy by hand or print the final schedule out like some kind of cave troll. This idea is on the backburner until I can figure out why the google API is not working properly on my new (mac) laptop...
