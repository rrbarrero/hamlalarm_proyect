#!/usr/bin/env python

import warnings
import os
import requests
import json
from joblib import load
from dateutil.parser import parse
from datetime import timedelta, datetime
import pandas as pd
from sklearn.preprocessing import LabelBinarizer, MinMaxScaler
import joblib

def warn(*args, **kwargs):
    pass


warnings.warn = warn

dir_path = os.path.dirname(os.path.realpath(__file__))
saves_path = '/home/roberto/devel/python/ml/curses/hamlalarm/'

TOKEN = 'homeassistant-token'
HOST = 'homeassistant-host'
AUTH_HEADER = 'Bearer {}'.format(TOKEN)
BASE_URL = 'https://{}/api/'.format(HOST)

headers = {
    'Authorization': AUTH_HEADER,
    'content-type': 'application/json',
}


def format_data(states):
    now = datetime.now()
    data = {}
    data['s'] = now.hour * 60 * 60 + now.minute * 60 + now.second
    data['d'] = now.weekday()
    data['m'] = now.month
    for state in states:
        if 'device_tracker.movil1' == state['entity_id']:
            data['mvr'] = 1 if state['state'] == 'home' else 0
            t = state['last_changed']
            data['mvrs'] = t.hour * 60 * 60 + t.minute * 60 + t.second
        elif 'device_tracker.movil2' == state['entity_id']:
            data['mvn'] = 1 if state['state'] == 'home' else 0
            t = state['last_changed']
            data['mvns'] = t.hour * 60 * 60 + t.minute * 60 + t.second
        elif 'light.lampara' == state['entity_id']:
            data['ls'] = 1 if state['state'] == 'on' else 0
        elif 'media_player.salon' == state['state']:
            data['pd'] = state['state']
        elif 'media_player.samsung_tv_remote' == state['entity_id']:
            data['tv'] = 1 if state['state'] == 'on' else 0
        elif 'sensor.sunset_time' == state['entity_id']:
            h, m = [int(x) for x in state['state'].split(':')]
            data['ss'] = h * 60 + m
        elif 'sensor.sunrise_time' == state['entity_id']:
            h, m = [int(x) for x in state['state'].split(':')]
            data['sr'] = h * 60 + m
        elif 'sun.sun' == state['entity_id']:
            data['sun'] = 1 if state['state'] == 'above_horizon' else 0
        elif 'sensor.illumination_34ce008c1858' == state['entity_id']:
            data['sl'] = int(state['state'])
        elif 'binary_sensor.door_window_sensor_158d0001bc3a49' == state['entity_id']:
            t = state['last_changed']
            data['sps'] = t.hour * 60 * 60 + t.minute * 60 + t.second
    return data


def day_name_binarizer(df):
    DAYS = list('LMXJVSD')
    days_bin = LabelBinarizer().fit(range(0, 7)).transform(df.d)
    df_days = pd.DataFrame(days_bin, columns=DAYS)
    return pd.concat([df, df_days], axis=1, join='inner')


def month_name_binarizer(df):
    MONTHS = ['EN', 'FE', 'MA', 'AB', 'MAY',
              'JU', 'JUL', 'AG', 'SE', 'OC', 'NO', 'DI']
    months_bin = LabelBinarizer().fit(range(1, 13)).transform(df.m)
    df_months = pd.DataFrame(months_bin, columns=MONTHS)
    return pd.concat([df, df_months], axis=1, join='inner')

def get_normalized(df):
    min_max_columns = ['s', 'mvns', 'mvrs', 'ss', 'sr', 'sl', 'sps']
    bin_columns = ['mvn', 'mvr', 'ls', 'tv', 'sun']
    df = day_name_binarizer(df).drop('d', axis=1)
    df = month_name_binarizer(df).drop('m', axis=1)
    for colName in min_max_columns:
        scaler_path = os.path.join(
            saves_path, 'scaler_{}.joblib'.format(colName))
        scaler = joblib.load(scaler_path)
        df[colName] = scaler.transform(df[colName].values.reshape(-1,1))
    df[bin_columns] = df[bin_columns]
    # POR AHORA QUITAMOS LOS MESES
    df = df.iloc[:, :19]
    return df.drop(['sr', 'ss'], axis=1)


def request_live_data():
    with requests.session() as s:
        with open(os.path.join(dir_path, 'entities.dat')) as fo:
            states = []
            for entity in fo:
                url = BASE_URL + 'states/' + entity.strip()
                response = s.get(url, headers=headers)
                if response.status_code == 200:
                    state = json.loads(response.content)
                    state['last_changed'] = parse(state['last_changed']) + timedelta(hours=1)
                    states.append(state)
            return get_normalized(pd.DataFrame([format_data(states)]))


if __name__ == '__main__':
    print("Utilizando modelo Sklearn/SVM")
    alarm_state = 'Apagada'
    msg = "La alarma debería estar {}"
    X = request_live_data()
    model = joblib.load(os.path.join(saves_path, 'sklearn_svm_model.joblib'))
    if model.predict(X)[0]:
        alarm_state = 'Encendida'
    print(msg.format(alarm_state))

