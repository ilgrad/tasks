# asterisk_record_processing

Обработка записей asterisk

В распознавании текста используются модели:
1) https://github.com/alphacep/kaldi-websocket-python
2)  http://alphacephei.com/kaldi/kaldi-ru-0.6.tar.gz
3) https://github.com/alphacep/vosk-api                                  
  сама модель:
https://github.com/alphacep/kaldi-android-demo/releases/download/2020-01/alphacep-model-android-ru-0.3.tar.gz
4) google с помощью  https://github.com/Uberi/speech_recognition 


Записи звонков находятся в папке */var/spool/asterisk/monitor/* на сервере с asterisk.
Записи аудиофайлов(приветствия, вопросы) находятся в папке */var/lib/asterisk/sounds/*.
Скрипты *agi(eagi)* обычно находятся */var/lib/asterisk/agi-bin/*.


Формат записей в папке */var/spool/asterisk/monitor/*, YYYYMMDD-HHMMSS-8**********  например:

1. ответ на звонок: 20200128-160117-8**********-in.wav
2. звонок из asterisk:  20200128-160117-8**********-out.wav

После запуска скрипта main.py, он считает временные интервалы вопросов и ответов, и исходя из этого делает распознование разными моделями.
