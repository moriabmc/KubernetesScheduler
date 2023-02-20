import csv
import datetime
import errno
from msilib.schema import Error
from time import time
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
    year = []
    month = []
    day = []
    hour = []

    core_count = []
    r = []
    cpu_utilization = []
    # mem_utilization = []
    submit_time = []
    delta = []

    with open(filename) as file:
        tsv_file = csv.reader(file, delimiter="\t")
        field_count = 0
        while int(field_count) < 20:
            field_count = int(len(next(tsv_file)))

        last_time = -1
        last_hour = -1
        job_count = 0
        last_submitted = -1
        i = 0
        for line in tsv_file:
            if (float(line.__getitem__(3)) > -0.5) and (float(line.__getitem__(4)) > -0.5) and float(
                    line.__getitem__(5)) > -0.5:
                i+=1
                if i == 30000:
                    break
                submitted = int(line.__getitem__(1))
                time = datetime.datetime.fromtimestamp(submitted)
                time_hour = time.hour

                if last_hour == -1:
                    last_hour = time_hour
                    last_time = time
                    
                if last_hour != time_hour:
                    runtime.append(calc_avg(r))
                    nprocs.append(calc_avg(core_count))
                    avg_cpu_time_used.append(calc_avg(cpu_utilization))
                    # used_memory.append(calc_avg(mem_utilization))
                    total_jobs.append(job_count)
                    #submit_time.append(submitted)
                    year.append(last_time.year)
                    month.append(last_time.month)
                    day.append(last_time.day)
                    hour.append(last_time.hour)
                    inter_arrival_time.append(calc_avg(delta))
                    last_time = time
                    job_count = 0
                    core_count.clear
                    r.clear
                    cpu_utilization.clear
                    delta.clear
                    last_submitted = -1
                    # mem_utilization.clear
                
                core_count.append(int(line.__getitem__(4))) # number of allocated processors
                r.append(float(line.__getitem__(3))) # runtime of the job
                cpu_utilization.append(float(line.__getitem__(5))) # average cpu time over all processors
                # mem_utilization.append(float(line.__getitem__(6))) # memory in kb per processor
                if last_submitted > -1:
                    delta.append(submitted - last_submitted)
                job_count += 1
                last_submitted = submitted
                last_hour = time_hour
    return year, month, day, hour, runtime, nprocs, avg_cpu_time_used, total_jobs, inter_arrival_time

# used to parse gwf file
def read_dataframe():
    year, month, day, hour, runtime, nprocs, avg_cpu_time_used, total_jobs, inter_arrival_time = read_data('anon_jobs.gwf')
    df = pd.DataFrame(list(zip(year, month, day, hour, runtime, nprocs, avg_cpu_time_used, total_jobs, inter_arrival_time)), columns=['Year', 'Month', 'Day', 'Hour', 'RunTime', 'NProcs', 'AverageCPUTimeUsed', 'TotalJobs', 'InterArrivalTime'])
    # df.to_pickle('total_jobs_dataframe')
    return df

def generate_plot(x_axis, y_axis, title, x_label, y_label):
    fig = plt.figure()
    fig.canvas.manager.set_window_title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.plot(x_axis, y_axis)
    plt.show()

# Retrieves all entries of a dataframe at the given day
def get_workload_at_day(df: pd.DataFrame, start_date: datetime.datetime, end_date: datetime.datetime):
    idx = pd.date_range(start_date, end_date)
    df.index = pd.DatetimeIndex(df.index)
    df = df.reindex(idx, fill_value=0)
    return df.loc[(df['ds'] >= start_date ) & (df['ds'] < end_date)]

def getCpuUtilization(df: pd.DataFrame):
    cpu = []
    for i in range(0,24):
        cores = df.iloc[i]['NProcs']
        jobs = df.iloc[i]['TotalJobs']
        cpu.append(cores*jobs/400)
    return cpu

def generate_workload(df: pd.DataFrame):
    critical_job_rate = 0.6
    start_time = 17

    f = open('workload_test.csv', 'w', newline='')
    writer = csv.writer(f, lineterminator="\n")  # use linux style line endings
    cpuUsage = getCpuUtilization(df)
    time_counter = 0
    while time_counter < 86400:  # generate for whole day
        # calculating adapted values
        current_hour = int(time_counter / 3600)
        adapted_hour = (current_hour + start_time) % 24         
        #print("current hour: " + str(adapted_hour))
        #print("job interval adapted: " + str(adapted_frame['InterArrivalTime']))

        label = ""
        if random.random() > critical_job_rate:
            label = "not-critical"
        else:
            label = "critical"
        print("cpu percent", cpuUsage[adapted_hour])
        total_cpu_usage = int(cpuUsage[adapted_hour] * 4000) # 4000 millicores rounded
        print("cpu total", total_cpu_usage)
        total_jobs = df.iloc[adapted_hour]['TotalJobs']
        print("jobs total", total_jobs)
        cpu_usage_per_job = total_cpu_usage/total_jobs
        runtime = df.iloc[adapted_hour]['RunTime']
        job_interval = int(3600/total_jobs)
        write_data = [str(int(cpu_usage_per_job)), str(int(runtime)),
                    str(int(job_interval)), label]
        #print(write_data)
        writer.writerow(write_data)
        time_counter = int(time_counter) + int(job_interval)
    f.close()


def main():
    df = pd.read_pickle('job_traces_sharc')
    # df = read_dataframe()
    df = get_workload_at_day(df, datetime.datetime.fromisoformat('2006-02-24'), datetime.datetime.fromisoformat('2006-02-25'))
    #df = interpolate(df, datetime.datetime.fromisoformat('2006-02-24'))
    #generate_workload(df)
    print('\007')
    

main()
    



