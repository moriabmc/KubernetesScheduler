import csv
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.metrics import mean_absolute_error as mae
from sklearn.metrics import mean_absolute_percentage_error as mape
from sklearn.ensemble import RandomForestRegressor
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



filePathGer = 'C:\\Users\\moria\\OneDrive\\Universität\\Bachelor\\Project\\KubernetesScheduler\\co2_prediction\\Germany_CO2_Signal_2018.csv'
filePathFra = 'C:\\Users\\moria\\OneDrive\\Universität\\Bachelor\\Project\\KubernetesScheduler\\co2_prediction\\France_CO2_Signal_2018.csv'

co2_emission_column = 3
unix_timestamp_column = 1
df = pd.DataFrame
a = 0
time = []
emission = []
timezone_unix_factor = 3600 # factor is necessary, as the unix timestamp is not standard compliant as timezone is set to UTC + 1
with open(filePathFra, 'r') as csvfile:
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

df['Date'] = pd.to_datetime(df['Date'])
df = df.drop_duplicates(subset=['Date'])
df = df.set_index('Date')
df = df.asfreq('H')
df = df.interpolate('ffill')

steps = 24
data_train = df[:-steps*2]
data_test  = df[-steps*2:]

result = pd.DataFrame(columns=['lags', 'n_estimators', 'max_depth', 'error'])
i = 0
max_depth = 25
for lags in range(1,30):
    for n_estimators in range(1,30):
        print(i)
        i += 1
        forecaster_df = ForecasterAutoreg(
                        # regressor = RandomForestRegressor(random_state=123),
                        regressor = RandomForestRegressor(max_depth=max_depth, n_estimators = n_estimators, random_state=123),
                        lags      = lags
                    )
        forecaster_df.fit(y=data_train['y'])
        predictions_df = forecaster_df.predict(steps=steps*2)
        error_mae_df = mae(data_test['y'], predictions_df)
        result.loc[len(result.index)] = [lags, n_estimators, max_depth, error_mae_df]
result.to_pickle(path='results')
result = result.sort_values(ascending=True, by='error')
print(result.head())
