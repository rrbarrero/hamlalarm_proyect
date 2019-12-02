import os
from peewee import *
import datetime
from playhouse.sqlite_ext import SqliteExtDatabase

dir_path = os.path.dirname(os.path.realpath(__file__))
db = SqliteExtDatabase(os.path.join(dir_path, 'database.sqlite'))


class BaseModel(Model):
    class Meta:
        database = db


class SensorState(BaseModel):
    name = TextField()
    sensor_id = TextField(null=True)
    state = TextField(null=True)
    lastChanged = DateTimeField(null=True)
    when = DateTimeField(default=datetime.datetime.now)
    uuid = UUIDField()
    target = BooleanField()



