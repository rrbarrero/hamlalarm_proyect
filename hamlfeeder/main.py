import os
import json
import requests
import uuid
from dateutil.parser import parse
from datetime import timedelta
from flask import Flask, abort
from models import *

dir_path = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
app.secret_key = 'secret'

TOKEN = 'homeassistant token'
HOST = 'host'
AUTH_HEADER = 'Bearer {}'.format(TOKEN)
BASE_URL = 'https://{}/api/'.format(HOST)

db.create_tables([SensorState, ])

headers = {
    'Authorization': AUTH_HEADER,
    'content-type': 'application/json',
}


def _save_states(target):
    common_uuid = uuid.uuid1()
    with requests.session() as s:
        with open(os.path.join(dir_path, 'entities.dat')) as fo:
            for entity in fo:
                url = BASE_URL + 'states/' + entity.strip()
                response = s.get(url, headers=headers)
                if response.status_code == 200:
                    state = json.loads(response.content)
                    sensor = SensorState()
                    sensor.name = state['entity_id']
                    sensor.sensor_id = state['context']['id']
                    sensor.state = state['state']
                    sensor.lastChanged = parse(state['last_changed']) + timedelta(hours=1)
                    sensor.uuid = common_uuid
                    sensor.target = target
                    sensor.save()


@app.route('/true')
@app.route('/alarm_feed/true')
def true():
    _save_states(True)
    return '', 204


@app.route('/false')
@app.route('/alarm_feed/false')
def false():
    _save_states(False)
    return '', 204
    

@app.route('/')
def root():
    abort(404)
    



    

