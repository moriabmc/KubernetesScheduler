import csv
import datetime
from turtle import pd
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import random

# website used for debugging
# https://timestamp.online/

# calculates the average of values in a list
def calc_avg(lst):
    total = 0
    for element in lst:
        total += element
    if len(lst) < 1:
        return 0
    else:
        return total/len(lst)

def read_data(filename):
    nprocs = []
    runtime = []
    avg_cpu_time_used = []
    # used_memory = []
    total_jobs = []
    inter_arrival_time = []

    core_count = []
    r = []
    cpu_utilization = []
    # mem_utilization = []
    submit_time = []

    with open(filename) as file:
        tsv_file = csv.reader(file, delimiter="\t")
        field_count = 0
        while int(field_count) < 20:
            field_count = int(len(next(tsv_file)))

        last_time = -1
        last_hour = -1
        job_count = 0
        last_submitted = -1
        delta = 0
        for line in tsv_file:
            if (float(line.__getitem__(3)) > -0.5) and (float(line.__getitem__(4)) > -0.5) and float(
                    line.__getitem__(5)) > -0.5:
                submitted = int(line.__getitem__(1))
                time = datetime.datetime.fromtimestamp(submitted)
                hour = time.hour

                if last_hour == -1:
                    last_hour = hour
                    last_time = time
                    

                if last_hour != hour:
                    runtime.append(calc_avg(r))
                    nprocs.append(calc_avg(core_count))
                    avg_cpu_time_used.append(calc_avg(cpu_utilization))
                    # used_memory.append(calc_avg(mem_utilization))
                    total_jobs.append(job_count)
                    submit_time.append(last_time.replace(minute=0, second=0, microsecond=0))
                    inter_arrival_time.append(delta/job_count)
                    last_time = time
                    job_count = 0
                    core_count.clear
                    r.clear
                    cpu_utilization.clear
                    delta = 0
                    last_submitted = -1
                    # mem_utilization.clear
                
                core_count.append(int(line.__getitem__(4))) # number of allocated processors
                r.append(float(line.__getitem__(3))) # runtime of the job
                cpu_utilization.append(float(line.__getitem__(5))) # average cpu time over all processors
                # mem_utilization.append(float(line.__getitem__(6))) # memory in kb per processor
                if last_submitted > -1:
                    delta += submitted - last_submitted
                job_count += 1
                last_submitted = submitted
                last_hour = hour

    return submit_time, runtime, nprocs, avg_cpu_time_used, total_jobs, inter_arrival_time

# used to parse gwf file
def read_dataframe():
    submit_time, runtime, nprocs, avg_cpu_time_used, total_jobs, inter_arrival_time = read_data('anon_total_jobs.gwf')
    df = pd.DataFrame(list(zip(submit_time, runtime, nprocs, avg_cpu_time_used, total_jobs, inter_arrival_time)), columns=['SubmitTime', 'RunTime', 'NProcs', 'AverageCPUTimeUsed', 'TotalJobs', 'InterArrivalTime'])
    df.to_pickle('total_jobs_dataframe')
    return df

# used to load dataframe from pickle
def load_dataframe():
    return pd.read_pickle('total_jobs_dataframe')

def generate_plot(x_axis, y_axis, title, x_label, y_label):
    fig = plt.figure()
    fig.canvas.manager.set_window_title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.plot(x_axis, y_axis)
    plt.show()

def main():
    print("no")
    df = read_dataframe()
    print(df.head())
    print('\007')

main()
    



