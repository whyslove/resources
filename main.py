import pickle
import json
import os
import asyncio
from datetime import datetime, timedelta

from aiohttp import ClientSession
from tortoise import Tortoise
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


import models
from models import Room, Source
from settings import create_logger

DATABASE_URI = os.environ.get('DATABASE_URI')

SCOPES = 'https://www.googleapis.com/auth/admin.directory.resource.calendar'
GOOGLE_API_URI = 'https://www.googleapis.com/admin/directory/v1/customer'

# No need in dev
# NVR_API_URL = os.environ.get('NVR_API_URL')
# NVR_API_KEY = os.environ.get('NVR_API_KEY')
logger = create_logger()


creds = None
TOKEN_PATH = 'creds/tokenAdminSDK.pickle'


def creds_generate():
    global creds
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("No token provided")
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)


creds_generate()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}


async def tortoise_init():
    await Tortoise.init(
        db_url=DATABASE_URI,
        modules={'models': ['models']}
    )


class GoogleResources:
    def __init__(self, customer):
        self.customer = customer

    async def fetch_data(self):
        creds_generate()
        try:
            sem = asyncio.Semaphore(10)
            resources = await self.get_resources()

            room_names = {item.get('floorSection') for item in resources}
            rooms_to_create = []

            if None in room_names:
                room_names.remove(None)

            for room_name in room_names:
                room = await Room.get_or_none(name=room_name)
                if not room:
                    rooms_to_create.append(room_name)
                    logger.info(f"No room {room_name}")
            
            # await asyncio.gather(*[self.create_room(room_name) for room_name in rooms_to_create])
            await asyncio.gather(*[self.use_data(resource, sem) for resource in resources])

        except Exception as err:
            logger.exception(err)

    async def use_data(self, resource: dict, sem: asyncio.Semaphore) -> None:
        room_name = resource.get('floorSection')
        source_data = resource.get('resourceDescription')
        source_name = resource.get('userVisibleDescription')
        external_id = resource.get('resourceId')
        if not (room_name and source_name and source_data):
            return
        
        room = await Room.get(name=room_name)

        source_data = json.loads(source_data)
        source = await Source.get_or_none(external_id=external_id)
        if not source:
            logger.info(f"Creating source {source.name}")
            source = await Source.create(
                **source_data, name=source_name, room_id=room.id,
                external_id=external_id)
        else:
            if source.time_editing >= datetime.utcnow() - timedelta(minutes=5):
                source_data['ip'] = source.ip
                source_data['rtsp_mainstream'] = source.rtsp
                async with sem:
                    res = await self.SendChangesToGoogleSDK(json.dumps(source_data), source.name, external_id)
                logger.info(f"Sending changes to GoogleSDK {res}")

            logger.info(f"Updating source {source.name}")
            source.update_as_obj(
                **source_data, name=source_name, room_id=room.id, external_id=external_id)
            await source.save()

    async def SendChangesToGoogleSDK(self, source_data: str, source_name: str, external_id: str) -> dict:
        body = {
            'resourceDescription': source_data, 
            'source_name': source_name
            }
            
        async with ClientSession() as session:
            resp = await session.patch(f'{GOOGLE_API_URI}/{self.customer}/resources/calendars/{external_id}',
                                       json=body, ssl=False, headers=HEADERS)
            async with resp:
                return await resp.json()

    async def create_room(self, name: str) -> None:
        room = await Room.create(name=name)

        async with ClientSession() as session:
            resp = await session.post(f'{NVR_API_URL}/gconfigure/{name}', headers={'key': NVR_API_KEY})
            async with resp:
                resp_json = await resp.json()

        room.drive = resp_json['drive']
        room.calendar = resp_json['calendar']
        room.save()

    async def get_resources(self) -> list:
        async with ClientSession() as session:
            page_token = ''
            result = []
            while page_token != False:
                async with session.get(f'{GOOGLE_API_URI}/{self.customer}/resources/calendars?pageToken={page_token}', headers=HEADERS, ssl=False) as resp:
                    resp_json = await resp.json()
                    result.extend(resp_json.get('items', []))
                    page_token = resp_json.get('nextPageToken', False)

        return [item for item in result if item.get('resourceType') in ['ONVIF-camera', 'Encoder', 'Enc/Dec']]


async def main():
    try:
        await tortoise_init()
        resources = GoogleResources()
        while True:
            await resources.fetch_data()
            await asyncio.sleep(300)
    finally:
        logger.info("Shutting down")
        await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(main())
