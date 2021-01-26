from tortoise.models import Model
from tortoise import fields
from tortoise import Tortoise
import asyncio


class Room(Model):
    """rooms table schema"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, null=False, unique=True)
    tracking_state = fields.BooleanField(default=False)
    ruz_id = fields.IntField()

    drive = fields.CharField(max_length=200)
    calendar = fields.CharField(max_length=200)
    stream_url = fields.CharField(max_length=300)

    sound_source = fields.CharField(max_length=100)
    main_source = fields.CharField(max_length=100)
    tracking_source = fields.CharField(max_length=100)
    screen_source = fields.CharField(max_length=100)

    auto_control = fields.BooleanField(default=True)

    class Meta:
        table = 'rooms'
        app = 'models'


class Source(Model):
    """source table schema"""
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100, default='источник')
    ip = fields.CharField(max_length=200, null=True)
    port = fields.CharField(max_length=200, null=True)
    rtsp = fields.CharField(max_length=200, default='no', null=True)
    audio = fields.CharField(max_length=200, null=True)
    merge = fields.CharField(max_length=200, null=True)
    tracking = fields.CharField(max_length=200, null=True)
    room = fields.ForeignKeyField('models.Room', )
    external_id = fields.CharField(max_length=200)
    time_editing = fields.DatetimeField(auto_now=True)

    def update_as_obj(self, **kwargs):
        self.name = kwargs.get('name')
        self.ip = kwargs.get('ip')
        self.port = kwargs.get('port')
        self.rtsp = kwargs.get('rtsp_mainstream')
        self.audio = kwargs.get('audio')
        self.merge = kwargs.get('merge')
        self.tracking = kwargs.get('tracking')
        self.room_id = kwargs.get('room_id')

    class Meta:
        table = 'sources'
        app = 'models'

