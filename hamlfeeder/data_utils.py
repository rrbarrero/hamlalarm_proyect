#!/usr/bin/env python

import os
from dateutil.parser import parse
import pandas as pd
from sklearn.preprocessing import LabelBinarizer, MinMaxScaler
from hamlfeeder.models import *
from paramiko import SSHClient, SSHConfig, ProxyCommand, AutoAddPolicy
from scp import SCPClient
import joblib


# FUNCIONES AUXILIARES PARA RECUPERAR LA INFO. DE LA BASE DE DATOS


# 1 HORA DEL DIA EN SEGUNDOS, 2 DIA DE LA SEMANA 0 LUNES, 3 MES, 4 MOVIL #2, 5 MOVIL #2 SINCE SEGUNDOS
# 6 MOVIL #1, 7 MOVIL #1 SINCE SEGUNDOS, 7 LAMPARA SALON, 8 TV, 9 SUNSET EN MINUTOS, 10 SUNRISE EN MINUTOS
# 11 ESTADO SOL: DIA 1, NOCHE 0, 12 SENSOR LUZ DEL SALON, 13 SENSOR PUERTA SINCE SEGUNDOS, TARGET
COL_ORDER = ['s', 'd', 'm', 'mvn', 'mvns', 'mvr', 'mvrs', 'ls', 'tv', 'ss', 'sr', 'sun', 'sl', 'sps', 'target']

def get_uuids():
    """ Devuelve lista de uuids únicos para agrupar por lectura, pasando de mirar el group_by de peewee """
    uuids = []
    for e in SensorState.select():
        uuids.append(e.uuid)
    return set(uuids)


def format_db_row(row):
    data = {}
    data['s'] = row.when.hour * 60 * 60 + row.when.minute * 60 + row.when.second
    data['d'] = row.when.weekday()
    data['m'] = row.when.month
    # data['a'] = row.uuid
    if 'device_tracker.movil1' == row.name:
        data['mvr'] = 1 if row.state == 'home' else 0
        t = parse(row.lastChanged)
        data['mvrs'] = t.hour * 60 * 60 + t.minute * 60 + t.second
    elif 'device_tracker.movil2' == row.name:
        data['mvn'] = 1 if row.state == 'home' else 0
        t = parse(row.lastChanged)
        data['mvns'] = t.hour * 60 * 60 + t.minute * 60 + t.second
    elif 'light.lampara' == row.name:
        data['ls'] = 1 if row.state == 'on' else 0
    # elif 'media_player.android_tv' == row.name:
    #     data['px'] = row.state
    # elif 'media_player.chromecast8292' == row.name:
    #     data['pg'] = row.state
    elif 'media_player.salon' == row.state:
        data['pd'] = row.state
    elif 'media_player.samsung_tv_remote' == row.name:
        data['tv'] = 1 if row.state == 'on' else 0
    elif 'sensor.sunset_time' == row.name:
        h, m = [int(x) for x in row.state.split(':')]
        data['ss'] = h * 60 + m
    elif 'sensor.sunrise_time' == row.name:
        h, m = [int(x) for x in row.state.split(':')]
        data['sr'] = h * 60 + m
    elif 'sun.sun' == row.name:
        data['sun'] = 1 if row.state == 'above_horizon' else 0
    elif 'sensor.illumination_34ce008c1858' == row.name:
        data['sl'] = int(row.state)
    elif 'binary_sensor.door_window_sensor_158d0001bc3a49' == row.name:
        t = parse(row.lastChanged)
        data['sps'] = t.hour * 60 * 60 + t.minute * 60 + t.second
    data['target'] = 1 if row.target else 0
    return data


def get_dataframe(uuid_list):
    """ De las lecturas que tienen en común el uuid, hacemos un filtro con los campos que nos interesan """
    data = {}
    for uuid in uuid_list:
        data[str(uuid)] = {}
        for row in SensorState.select().filter(SensorState.uuid==uuid):
            for k, v in format_db_row(row).items():
                data[str(uuid)][k] = v
    return pd.DataFrame(data.values())

def day_name_binarizer(df):
    DAYS = list('LMXJVSD')
    days_bin = LabelBinarizer().fit(range(0, 7)).transform(df.d)
    #df_days = pd.DataFrame(days_bin, columns=DAYS).astype(bool)
    df_days = pd.DataFrame(days_bin, columns=DAYS)
    return pd.concat([df, df_days], axis=1, join='inner')

def month_name_binarizer(df):
    MONTHS = ['EN', 'FE', 'MA', 'AB', 'MAY', 'JU', 'JUL', 'AG', 'SE', 'OC', 'NO', 'DI']
    months_bin = LabelBinarizer().fit(range(1,13)).transform(df.m)
    # df_months = pd.DataFrame(months_bin, columns=MONTHS).astype(bool)
    df_months = pd.DataFrame(months_bin, columns=MONTHS)
    return pd.concat([df, df_months], axis=1, join='inner')

def update_database():
    if os.uname()[1] in ('workstation',):
        print("Actualizando copia local de la base de datos...")
        host = 'ha-remote'
        ssh = SSHClient()
        ssh_config_file = os.path.expanduser("~/.ssh/config")
        if os.path.exists(ssh_config_file):
            conf = SSHConfig()
            with open(ssh_config_file) as f:
                conf.parse(f)
            host_config = conf.lookup(host)
        proxy = ProxyCommand("ssh {}@{} -p {} nc {} 22".format(
            "pi", "remote-ssh.proxy.host", 2222, 'homeassistant-host'))
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        #ssh.connect(host, username=user, pkey=pkey, sock=proxy)
        ssh.connect(host, username=host_config['user'], sock=proxy)
        with SCPClient(ssh.get_transport()) as scp:
            src = '/home/homeassistant/devel/hamlfeeder/database.sqlite'
            dst = '/home/roberto/devel/python/hamlfeeder/database.sqlite'
            scp.get(src, dst)


def get_normalized(df):
    min_max_columns = ['s', 'mvns', 'mvrs', 'ss', 'sr', 'sl', 'sps']
    bin_columns = ['mvn', 'mvr', 'ls', 'tv', 'sun', 'target']
    df = day_name_binarizer(df).drop('d', axis=1)
    df = month_name_binarizer(df).drop('m', axis=1)
    for colName in min_max_columns:
        scaler = MinMaxScaler()
        df[colName] = scaler.fit_transform(df[colName].values.reshape(-1,1))
        joblib.dump(scaler, 'scaler_{}.joblib'.format(colName))
    #df[bin_columns] = df[bin_columns].astype(bool)
    # POR AHORA QUITAMOS LOS MESES
    df = df.iloc[:, :20]
    return df.drop(['sr', 'ss'], axis=1)




def get_last_row_uuid():
    last_row = SensorState.select().order_by(SensorState.id.desc()).get()
    return last_row.uuid


if __name__ == '__main__':
    update_database()
    df = get_normalized(get_dataframe(get_uuids()))
    print(df.dtypes)
 



