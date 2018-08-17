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
The main issue with this project was how to decide which task to prefer to queue for the next insertion. Because this is a problem in which we are searching for the optimum permutation, not an optimum value, (and even then, the parameter space for the optimum is highly complex - a small change at the wrong time can propegate to a significant difference in the solution) I could not think of an easy method to search all possible permutations of job order. For example, with 2 jobs each of 3 experiments and 3 (flexible) tasks, a highly limited version of the intended problem, there would be 262,143 different permutations to check. More realistic examples become fairly prohibitive in calculation time, expecially as the required time to generate a schedule increases as more jobs are supplied.

Initially, the code followed a simple prescription; the longest experiment available was the preferred one. However, wile this does robustly produce a servicable schedule, it fails to robustly find the /best/ schedule. To this end, I designed a genetic algortihm that breeds better schedules as time goes on. However, due to having to generate multiple schedules (typical generations only need to be 10-20 individuals, but this still increases the processing time by a factor of 10-20), this is much more expensive.

Each permutation is treated as a "chromosome", and is evaluated. The fitness of each is the length of the schedule it produces, and the top 50% are bred together. Each takes two random partners and produces an offspring with them, by taking subsequent chunks of each (of random length between 1 and 10 genes long) until the child is fully formed. Convergence is reached if the cohort becomes too inbred (the standard deviaiton falls below 10% of the best schedule length), or if no change is seen for 10 generations. This version of the code typically takes several minutes to run, mostly due to the long time it takes to evaluate an individual which can be on the order of 1-2 seconds per chromosome.

## Usage
The usage is fairly simple to the causal user. Simply use `jobgen.py` to define the jobs you'd like to queue, and (for now at least) edit the filenames into the code of either `scheduler.py` or `genetic_scheduler.py`. Then, simply run it to recieve the results as a plain text table.
> TODO: Make this more user friendly. Maybe generate a file with the job files listed and read this in in the main code? it would allow for reuse of job files...


## Future Work
The project is currently incomplete. Plans are to integrate google calendar, to allow users to click a link that imports the generated schedule into their calendar automatically, rather than having to either copy by hand or print the final schedule out like some kind of cave troll. This idea is on the backburner until I can figure out why the google API is not working properly on my new (mac) laptop...
