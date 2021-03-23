#!/usr/bin/env /opt/pyenv3.6/bin/python3.6
import numpy as np
from asterisk.agi import AGI
import os
import subprocess


#https://stackoverflow.com/questions/9763471/audioop-rms-why-does-it-differ-from-normal-rms

def get_pause():
  agi = AGI()
  raw_wav = bytearray()
  duration = 1 #в секундах шаги, можно дробное
  sample_rate = 8000
  sample_size_bytes = 2
  count = int(sample_rate * sample_size_bytes * duration)
  energy_threshold = 50#было 30
  pause_value = 3#значение в секундах, сколько мы ждем
  count_pause = 0
  count_sec = 0
  with os.fdopen(3, 'rb') as stream:
    while True:
      buffer = stream.read(count)
      if buffer == b'':
        agi.set_variable('FLAG_PAUSE', 1)
        break
      d = np.frombuffer(buffer, np.int16).astype(np.float)
      e = np.sqrt((d * d).sum() / len(d))
      e = int(np.nan_to_num(e))#если 0 но звуков нет
      if e < energy_threshold:
        count_pause += duration
      else:
        count_pause = 0 #зануляем чтобы учитывать только паузы идущие подряд
      if count_pause >= pause_value and count_sec > 2:#если больше pause_value пауза и первые 2 секунды ждем
        agi.set_variable('FLAG_PAUSE', 0)
        break
      count_sec += duration


get_pause()