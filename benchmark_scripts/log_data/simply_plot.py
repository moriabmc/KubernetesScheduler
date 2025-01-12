import matplotlib.pyplot as plt
import csv

xLabelCount = 24

x = []
y = []

with open('utilization-logs.csv', 'r') as csvfile:
    lines = csv.reader(csvfile, delimiter=',')
    for row in lines:
        x.append(row[0])
        y.append(float(row[7]))

plt.plot(x, y, color='b', linestyle='solid', label="CPU reservation")

x_tics = []
x_labels = []

for date in range(1, len(x), int(len(x) / xLabelCount)):
    x_tics.append(date)
    x_labels.append(x[date])


axes = plt

plt.xticks(rotation=45)
plt.xticks(x_tics, x_labels)

plt.fill_between(x, y)
plt.xlabel('Times')
plt.ylabel('CPU Reservation in %')
plt.title('Kubernetes Cluster cpu reservation', fontsize=20)
plt.grid()
plt.ylim([0, 100])
plt.xlim([0, len(y) - 1])
plt.legend()
plt.show()
