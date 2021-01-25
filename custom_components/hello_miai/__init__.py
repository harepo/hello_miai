import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import json
import requests
import os
import re
import random
import string
import hashlib
import time
import base64
import hass_frontend
from urllib import parse
from threading import Thread, Event


import logging
_LOGGER = logging.getLogger(__name__)


class xiaomi_tts:

    def __init__(self, hass, config, appId=None, token=None, deviceId=None):
        requests.packages.urllib3.disable_warnings()
        self.config = config
        self.hass = hass
        self._CONFIGURING = {}
        self._appId = appId
        self._token = token
        self._deviceId = deviceId

        self._cookies = {}
        self._request = requests.session()
        # self._headers = {'Host': 'account.xiaomi.com',
        #                  'Connection': 'keep-alive',
        #                  'Upgrade-Insecure-Requests': '1',
        #                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        #                  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        #                  'Accept-Encoding': 'gzip, deflate, br',
        #                  'Accept-Language': 'zh-CN,zh;q=0.9'}

        self._headers = {
            'Host': 'api.home.mi.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'APP-ID': self._appId,
            'SPEC-NS': 'miot-spec-v2',
            'ACCESS-TOKEN': self._token,
        }

    def _text_to_speech(self, aid, text):
        try:
            url = "https://api.home.mi.com/api/v1/action"
            _data = json.dumps({
                "aid": "{}.{}".format(self._deviceId, aid),
                "in": [
                    text
                ]
            })
            _LOGGER.debug(_data)
            r = self._request.put(url, headers=self._headers,
                                  data=_data, timeout=10, verify=False)
            rjson = json.loads(r.text)
            if rjson.get('oid') != None:
                return True
            _LOGGER.error(rjson)
        except AttributeError as e:
            _LOGGER.warning(e)
        except BaseException as e:
            _LOGGER.warning(e)
        return False

    def player_set_volume(self, pid, volume):
        if volume > 100:
            volume = 100
        elif volume < 0:
            volume = 0
        try:
            url = "https://api.home.mi.com/api/v1/properties"
            _data = json.dumps({
                "properties": [
                    {
                        "pid": "{}.{}".format(self._deviceId, pid),
                    }
                ]
            })
            _LOGGER.debug(_data)
            r = self._request.put(url, headers=self._headers,
                                  data=_data, timeout=10, verify=False)
            rjson = json.loads(r.text)
            if rjson.get('properties') != None:
                return True
            _LOGGER.error(rjson)
        except AttributeError as e:
            _LOGGER.warning(e)
        except BaseException as e:
            _LOGGER.warning(e)
        return False

    def execution_operation(self, aid, operation, silent='false'):
        try:
            url = "https://api.home.mi.com/api/v1/action"
            _data = json.dumps({
                "aid": "{}.{}".format(self._deviceId, aid),
                "in": [
                    operation,
                    silent,
                ]
            })
            _LOGGER.debug(_data)
            r = self._request.put(url, headers=self._headers,
                                  data=_data, timeout=10, verify=False)
            rjson = json.loads(r.text)
            if rjson.get('oid') != None:
                return True
            _LOGGER.error(rjson)
        except AttributeError as e:
            _LOGGER.warning(e)
        except BaseException as e:
            _LOGGER.warning(e)
        return False


CONF_USER = 'appid'
CONF_PASSWORD = 'token'
CONF_DEVICEID = 'deviceid'
CONF_PARAMS = 'params'

WAIT_TIME = 'wait_time'
ATTR_MESSAGE = 'message'
ATTR_VOLUME = 'vol'
ATTR_IID = 'iid'
ATTR_OPERATION = 'operation'
ATTR_SILENT = 'silent'

DEFAULT_MIAI_NUM = '0'
DEFAULT_MIAI_SPEED = 0.27
DEFAULT_WAIT_TIME = 0

DOMAIN = 'hello_miai'

SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_IID): cv.string,
})

SERVICE_SCHEMA_FOR_QUEUE = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_IID): cv.string,
    vol.Optional(WAIT_TIME): cv.string,
})

SERVICE_SCHEMA_FOR_SET_VOLUME = vol.Schema({
    vol.Required(ATTR_VOLUME): cv.string,
    vol.Optional(ATTR_IID): cv.string,
})

SERVICE_SCHEMA_FOR_EXECUTION_OPERATION = vol.Schema({
    vol.Required(ATTR_OPERATION): cv.string,
    vol.Optional(ATTR_IID): cv.string,
    vol.Optional(ATTR_SILENT): cv.string,
})


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USER): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_DEVICEID): cv.string,
        vol.Optional(CONF_PARAMS): dict,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    conf = config.get(DOMAIN, {})
    appid = conf.get(CONF_USER)
    token = conf.get(CONF_PASSWORD)
    deviceid = conf.get(CONF_DEVICEID)
    params = conf.get(CONF_PARAMS, {})
    _LOGGER.debug(params)

    client = xiaomi_tts(hass, config, appid, token, deviceid)
    msg_queue = []

    def listen_to_msg():
        while not Event().isSet():
            if len(msg_queue) > 0:
                send_finish = client._text_to_speech(
                    msg_queue[0]['iid'],
                    msg_queue[0]['msg']
                )
                if send_finish == True:
                    try:
                        time.sleep(
                            len(msg_queue[0]['msg'])*DEFAULT_MIAI_SPEED+int(msg_queue[0]['wait_time']))
                    except:
                        time.sleep(
                            len(msg_queue[0]['msg'])*DEFAULT_MIAI_SPEED)
                    msg_queue.pop(0)

                else:
                    time.sleep(1)
            else:
                time.sleep(1)

    def send_message(call):
        msg_queue = []
        default_iid = params.get('force_send', None)
        iid = call.data.get(ATTR_IID, default_iid)
        message = call.data.get(ATTR_MESSAGE)

        if not client._text_to_speech(iid, message):
            _LOGGER.error("参数异常，操作失败！")

    def add_msg2queue(call):
        wait_time = call.data.get(WAIT_TIME, DEFAULT_WAIT_TIME)
        message = call.data.get(ATTR_MESSAGE)
        default_iid = params.get('add2msgqueue', None)
        iid = call.data.get(ATTR_IID, default_iid)
        msg_queue.append(
            {'msg': message, 'iid': iid, 'wait_time': wait_time})

    def player_set_volume(call):

        default_iid = params.get('set_vol', None)
        iid = call.data.get(ATTR_IID, default_iid)
        vol = call.data.get(ATTR_VOLUME)

        if not client.player_set_volume(iid, int(vol)):
            _LOGGER.error("参数异常，操作失败！")

    def execution_operation(call):

        default_iid = params.get('execution', None)
        iid = call.data.get(ATTR_IID, default_iid)
        operation = call.data.get(ATTR_OPERATION)
        silent = call.data.get(ATTR_SILENT, 'false')

        if not client.execution_operation(iid, operation, silent):
            _LOGGER.error("参数异常，操作失败！")

    def listen():
        """Start listening."""
        thread = Thread(target=listen_to_msg, args=())
        thread.daemon = True
        thread.start()

    listen()

    def _stop_listener(_event):
        Event.set()

    hass.bus.listen_once(
        "homeassistant_stop",
        _stop_listener
    )

    hass.services.register(DOMAIN, 'force_send', send_message,
                           schema=SERVICE_SCHEMA)
    hass.services.register(DOMAIN, 'add2MsgQueue', add_msg2queue,
                           schema=SERVICE_SCHEMA_FOR_QUEUE)
    hass.services.register(DOMAIN, 'set_vol', player_set_volume,
                           schema=SERVICE_SCHEMA_FOR_SET_VOLUME)
    hass.services.register(DOMAIN, 'execution', execution_operation,
                           schema=SERVICE_SCHEMA_FOR_EXECUTION_OPERATION)

    return True
