#!/usr/bin/env python
# coding: utf-8

# In[120]:


import csv
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.metrics import mean_absolute_percentage_error as mape
from sklearn.ensemble import RandomForestRegressor

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
df = pd.DataFrame(list(zip(time, emission)), columns=['Date', 'y'])


# In[121]:


df['Date'] = pd.to_datetime(df['Date'])
df = df.drop_duplicates(subset=['Date'])

df = df.set_index('Date')
df = df.asfreq('H')
df = df.interpolate('ffill')


# In[122]:


df.head()


# In[123]:


steps = 36
data_train = df[:-steps]
data_test  = df[-steps:]
fig, ax=plt.subplots(figsize=(9, 4))
data_train['y'].plot(ax=ax, label='train')
data_test['y'].plot(ax=ax, label='test')
ax.legend()


# In[124]:


df.isnull().any()


# In[125]:


forecaster = ForecasterAutoreg(
                regressor = RandomForestRegressor(random_state=123),
                lags      = 6
             )
forecaster.fit(y=data_train['y'])


# In[126]:


predictions = forecaster.predict(steps=36)
print(predictions.head(5))


# In[127]:


fig, ax = plt.subplots(figsize=(9, 4))
data_train['y'].plot(ax=ax, label='train')
data_test['y'].plot(ax=ax, label='test')
predictions.plot(ax=ax, label='predictions')
ax.legend()


# In[128]:


error = mape(data_test['y'], predictions)
print(error)


# In[ ]:




