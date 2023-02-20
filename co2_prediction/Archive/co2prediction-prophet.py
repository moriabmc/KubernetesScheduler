import csv
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_percentage_error as mape
import prophet

filePath = 'C:\\Users\\moria\\OneDrive\\Universität\\Bachelor\\Project\\KubernetesScheduler\\co2_prediction\\Germany_CO2_Signal_2018.csv'
savename = 'avg_co2_ger'
co2_emission_column = 3
unix_timestamp_column = 1

df = pd.DataFrame
a = 0
time = []
emission = []
timezone_unix_factor = 3600 # factor is necessary, as the unix timestamp is not standard compliant as timezone is set to UTC + 1
with open(filePath, 'r') as csvfile:
    lines = csv.reader(csvfile, delimiter=',')
    next(lines)  # skip the label field
    for row in lines:
        a = a + 1
        day = datetime.datetime.fromtimestamp(
            int(row[unix_timestamp_column]) - timezone_unix_factor)  # correction as timestamp is UTC not UTC + 1
        time.append(day)
        try:
            emission.append(float(row[co2_emission_column]))
        except:
            emission.append(None)
df = pd.DataFrame(list(zip(time, emission)), columns=['ds', 'y'])


df['ds'] = pd.to_datetime(df['ds'])

#df = df.set_index('ds') # Do not use for Prophet model
df = df.drop_duplicates(subset=['ds'])
#df = df.interpolate('ffill') # Do not use for Prophet model
print(df.isnull().any())

steps = 24
data_train = df[:-steps]
data_test  = df[-steps:]

m = prophet.Prophet()
m.fit(data_train)

future = m.make_future_dataframe(periods=steps, freq='H')
print("Future dataframe", future.tail(24))

forecast = m.predict(future)
print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail())

fig1 = m.plot(forecast)
fig2 = m.plot_components(forecast)

fig1.show()
fig2.show()


#error = mape(data_test['y'], predictions)
#print(error)




