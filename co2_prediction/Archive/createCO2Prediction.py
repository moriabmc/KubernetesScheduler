import csv
import datetime
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from skforecast.ForecasterAutoreg import ForecasterAutoreg
from skforecast.ForecasterAutoregCustom import ForecasterAutoregCustom
from skforecast.ForecasterAutoregDirect import ForecasterAutoregDirect
from skforecast.model_selection import grid_search_forecaster
from skforecast.model_selection import backtesting_forecaster
from skforecast.utils import save_forecaster
from skforecast.utils import load_forecaster


file_to_use = 'C:\\Users\\moria\\OneDrive\\Universität\\Bachelor\\Project\\KubernetesScheduler\\co2_prediction\\Germany_CO2_Signal_2018.csv'
savename = 'avg_co2_ger'

# co2_emission_column = 3  # 2018 column = 3, 2020 & 2021 = 5
# unix_timestamp_column = 1  # 2018 column = 1, 2020 & 2021 = 3

def csv_to_dataframe(filePath: str, co2_emission_column: int, unix_timestamp_column: int):
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
    return pd.DataFrame(list(zip(time, emission)), columns=['time', 'y'])

def load_dataframe(filePath: str):
    return pd.read_pickle(filePath)

#Main
df = csv_to_dataframe(file_to_use, 3, 1)
df['time'] = pd.to_datetime(df['time'])
print(df.loc[0, 'time'].day_name())
#df = df.interpolate(method='bfill')
#df = df.drop_duplicates(subset=['time'])
df = df.set_index('time')
df = df.asfreq('H')

df.to_pickle(file_to_use[:-4])
#pd.set_option('display.max_rows', 10)
#df = pd.read_pickle(file_to_use[:-4])
print(f'Number of rows with missing values: {df.isnull().any(axis=1).mean()}')
steps = 36
data_train = df[:-steps]
data_test  = df[-steps:]

print(f"Train dates : {data_train.index.min()} --- {data_train.index.max()}  (n={len(data_train)})")
print(f"Test dates  : {data_test.index.min()} --- {data_test.index.max()}  (n={len(data_test)})")
print("missing vals", data_train.isnull().sum())
'''
fig, ax=plt.subplots(figsize=(9, 4))
data_train['y'].plot(ax=ax, label='train')
data_test['y'].plot(ax=ax, label='test')
ax.legend()
fig.show()
'''

forecaster = ForecasterAutoreg(
                regressor = RandomForestRegressor(random_state=123),
                lags      = 6
             )
print(data_train['y'])
forecaster.fit(y=data_train['y'])

steps = 36
predictions = forecaster.predict(steps=steps)
print(predictions.head(5))

fig, ax = plt.subplots(figsize=(9, 4))
data_train['y'].plot(ax=ax, label='train')
data_test['y'].plot(ax=ax, label='test')
predictions.plot(ax=ax, label='predictions')
ax.legend()
fig.show()

error_mse = mean_squared_error(
                y_true = data_test['y'],
                y_pred = predictions
            )

print(f"Test error (mse): {error_mse}")
