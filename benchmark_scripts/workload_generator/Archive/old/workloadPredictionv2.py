import csv
import datetime
from time import time
import matplotlib.pyplot as plt
import random
import winsound

# website used for debugging
# https://timestamp.online/

core_count = []
runtime = []
cpu_utilization = []
mem_utilization = []
# timestamp = []
lines_used = 0
lines_total = 0

interval_count = 24

def calc_avg(x):
    total = 0
    for element in x:
        total += element
    if len(x) == 0:
        return 0
    else:
        return total/len(x)

# initialize the arrays for analysing workload
def read_data():

    timeline = []
    total_cpu_time = []
    system_util = []
    arrival_rate = []
    available_cpu_time = 400 * 10 # total number of CPUs * fixed time interval

    with open("anon_jobs.gwf") as file:
        tsv_file = csv.reader(file, delimiter="\t")
        # skip the header part
        field_count = 0
        while int(field_count) < 20:
            field_count = int(len(next(tsv_file)))

        # iterate over .gwf data
        last_time = -1
        last_hour = -1
        last_day = -1
        total_cpu_time = 0
        total_jobs = 0
        for line in tsv_file:
            #lines_total = lines_total + 1
            if (float(line.__getitem__(3)) > -0.5) and (float(line.__getitem__(4)) > -0.5) and float(
                    line.__getitem__(5)) > -0.5:
                #lines_used = lines_used + 1
                time = datetime.datetime.fromtimestamp(int(line.__getitem__(1)))
                day = time.day
                hour = time.hour

                if last_hour == -1:
                    last_hour = hour
                    last_time = time
                    last_day = day
                    
                if last_hour != hour or last_day != day:
                    timeline.append(last_time.replace(minute=0, second=0, microsecond=0))
                    arrival_rate.append(total_jobs)
                    system_util.append(total_cpu_time/(available_cpu_time*total_jobs))
                    last_time = time
                    total_jobs = 0
                    total_cpu_time = 0

                total_cpu_time += int(line.__getitem__(4)) * float(line.__getitem__(5)) # number of allocated processors * average of CPU time over all allocated processors
                total_jobs += 1
                last_hour = hour
                last_day = day
    return system_util, arrival_rate, timeline

def generate_plot(x_axis, y_axis, title, x_label, y_label):
    fig = plt.figure()
    fig.canvas.manager.set_window_title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.plot(x_axis, y_axis)
    plt.show()

def main():
    print("reading data...")
    system_util, arrival_rate, timeline = read_data()
    print("plotting")
    print("\a")
    generate_plot(timeline, system_util, "system utilization", "t","%")
    generate_plot(timeline, arrival_rate, "arrival rate", "t", "jobs/h")
    print("done!")
main()
    



