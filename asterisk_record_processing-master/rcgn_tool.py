from websockets import connect
import json
import asyncio
import os
import subprocess
import wave
import speech_recognition as sr

uri = 'wss://api.alphacephei.com/asr/ru/'

async def kaldi_docker(data):
    async with connect(uri) as websocket:
        await websocket.send(data)
        await websocket.recv()
        await websocket.send('{"eof" : 1}')
        text = json.loads(await websocket.recv())
        if 'text' not in text.keys():
            return str()
        else:
            return text['text']


def rcgn_kaldi_docker(path_wav, count, count_start_answer, count_stop_answer):
    k = 0
    with open(path_wav, 'rb') as f:
        while True:
            if k == count_start_answer:
                data = f.read(count * int(count_stop_answer - count_start_answer))
                break
            else:
                f.read(count)
            k += 1
    return asyncio.get_event_loop().run_until_complete(kaldi_docker(data))



def rcgn_kaldi_vosk(frame_data, kaldi_rec_vosk):
    if kaldi_rec_vosk.AcceptWaveform(frame_data):
        res = json.loads(kaldi_rec_vosk.Result())
        return res['text']
    else:
        res = json.loads(kaldi_rec_vosk.PartialResult())
        return res['partial']



def rcgn_kaldi_local(model_path, frame_data, sample_rate, sample_size_bytes):
    s = ''
    os.chdir(model_path)
    with wave.open('decoder-test.wav', 'wb') as f:
        f.setframerate(sample_rate)
        f.setsampwidth(sample_size_bytes)
        f.setnchannels(1)
        f.writeframesraw(frame_data)
    proc = subprocess.Popen('/bin/bash decode.sh', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()
    output = proc.communicate()
    os.chdir('../../../')
    text = [i for i in output[1].decode("utf-8").split('\n') if i[:12] == 'decoder-test'][0]
    text = ' '.join(text.split('decoder-test')[1].split())
    if text:
        s = text
    return s


def rcgn_google(frame_data, sample_rate, sample_size_bytes):
    text = ''
    r = sr.Recognizer()
    audio = sr.AudioData(frame_data, sample_rate, sample_size_bytes)
    try:
        text = r.recognize_google(audio, language='ru-RU', show_all=False)
    except Exception as e:
        pass
        #print("Exception: " + str(e))
    return text


