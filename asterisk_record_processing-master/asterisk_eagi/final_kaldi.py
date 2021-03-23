#!/usr/bin/env /opt/pyenv3.6/bin/python3.6
import os
import sys
import subprocess
from asterisk.agi import AGI
import asyncio
import websockets
import json
import numpy as np

uri = 'wss://api.alphacephei.com/asr/ru/'
sample_rate = 8000
sample_size_bytes = 2
duration = 1
count = int(sample_rate * sample_size_bytes * duration)
agi = AGI()


def check_answer(rcgn_text):
    yes_word = ['да', 'конечно', 'хотел', 'давайте', 'согласен']
    no_word = ['нет', 'отстаньте', 'отвалите', 'достали', 'не хочу', 'не согласен',
               'не смейте', 'не буду', 'жаловаться', 'пожалуюсь', 'ни в коем случае', 'не в коем случае',
               'да ни за что',
               'да не за что', 'да не', 'не звоните', 'никогда']
    if any(item in rcgn_text for item in no_word):
        return 1
    elif any(item in rcgn_text for item in yes_word):
        return 0
    else:
        return 2


async def rcgn_text():
    raw_wav = None  # bytearray()
    replay_count = 1
    replay_value = 5
    energy_threshold = 50  # было 30 ранее, 200 значение тихого голоса
    pause_value = 3  # значение в секундах, сколько мы ждем
    count_pause = 0
    count_sec = 0
    async with websockets.connect(uri) as websocket:
        with os.fdopen(3, 'rb') as stream:
            while True:
                data = stream.read(count)
                count_sec += duration
                if len(data) == 0:
                    break
                raw_wav = data
                if raw_wav:
                    d = np.frombuffer(data, np.int16).astype(np.float)
                    e = np.sqrt((d * d).sum() / len(d))
                    e = int(np.nan_to_num(
                        e))  # если 0 но звуков нет
                    if e < energy_threshold:
                        count_pause += duration
                    else:
                        count_pause = 0
                    if count_pause >= pause_value and count_sec > 2:  # если больше pause_value пауза и первые 2 секунды ждем
                        agi.set_variable('FLAG_YES_NO', 2)
                        break
                    await websocket.send(raw_wav)
                    rcgn_text = json.loads(await websocket.recv())
                    if 'text' not in rcgn_text.keys():
                        continue
                    elif rcgn_text['text'] == str():
                        continue
                    else:
                        rcgn_text = rcgn_text['text']
                        if check_answer(rcgn_text) == 0:
                            agi.set_variable('FLAG_YES_NO', 0)
                            agi.verbose(str('количество попыток: ') + str(replay_count) + str('\nтекст: ') + str(
                                rcgn_text) + str('\n'))
                            break
                        elif check_answer(rcgn_text) == 1:
                            agi.set_variable('FLAG_YES_NO', 1)
                            agi.verbose(str('количество попыток: ') + str(replay_count) + str('\nтекст: ') + str(
                                rcgn_text) + str('\n'))
                        else:
                            replay_count += 1
                            if replay_count >= replay_value:
                                agi.set_variable('FLAG_YES_NO', 2)
                                agi.verbose(str('количество попыток: ') + str(replay_count) + str('\nтекст: ') + str(
                                    rcgn_text) + str('\n'))
                                break
            await websocket.send('{"eof" : 1}')
            await websocket.recv()


asyncio.get_event_loop().run_until_complete(rcgn_text())
