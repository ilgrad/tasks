import os
from datetime import datetime
import wave
import pandas as pd
import numpy as np
import audioop
from rcgn_tool import rcgn_kaldi_docker, rcgn_google, rcgn_kaldi_local, rcgn_kaldi_vosk
from vosk import Model, KaldiRecognizer
import pymorphy2
import re
import string


class WavTools:
    @classmethod
    def get_duration_wav(cls, path_wav, step_duration):
        with wave.open(path_wav, 'r') as f:
            duration = f.getnframes() / float(f.getframerate() * f.getnchannels())
        if (duration % 1) > 0.5:
            return round(duration / step_duration) * step_duration
        else:
            return round(duration)

    @classmethod
    def get_wav_info(cls, path_wav):
        with wave.open(path_wav, 'r') as f:
            sample_rate = f.getframerate()
            sample_size_bytes = f.getsampwidth()
        return sample_rate, sample_size_bytes

    @classmethod
    def get_energy_say(cls, wav_path, sample_rate, sample_size_bytes, step_duration, energy_threshold):
        lst_time_say = []
        count = int(sample_rate * sample_size_bytes * step_duration)
        k = 0
        in_wav_e = []
        with open(wav_path, 'rb') as f:
            while True:
                data = f.read(count)
                if len(data) == 0:
                    break
                e = audioop.rms(data, sample_size_bytes)#rms - считаем мощность сигнала, если 0 но звуков нет
                in_wav_e.append(e)
                k += step_duration
        #подбор в некоторых случаях
        #energy_threshold = 100
        #energy_threshold = 800
        #energy_threshold = int(np.sort(in_wav_e)[::-1][:5].min())
        for i in range(len(in_wav_e)):
            flag_say = False
            if all(item > energy_threshold for item in in_wav_e[i:i + 2]):  # быстро сказал (i, i+1)
                flag_say = True
            if i != 0 and i != len(in_wav_e):
                if all(item > energy_threshold for item in in_wav_e[i - 1:i + 2]):  # точно что-то сказал (i-1, i, i+1)
                    flag_say = True
                if all(item > energy_threshold for item in in_wav_e[i - 1:i + 1]):  # быстро сказал (i-1, i)
                    flag_say = True
                if all(item > energy_threshold for item in in_wav_e[i:i + 2]):  # быстро сказал (i, i+1)
                    flag_say = True
            if flag_say:
                lst_time_say.append(i * step_duration)  # на какой секунде (step_duration) человек что-то говорил
        return lst_time_say

    @classmethod
    def find_period_say(cls, lst_time, step_duration):
        '''
        функция расчитывает временные интервалы когда абонент или бот говорили
        :param lst_time: время когда говорили в секундах с шагом step_duration
        :param step_duration: шаг времени
        :return: периоды фраз когда говорили
        '''
        period = []
        for i in range(len(lst_time)):
            if i != len(lst_time) - 1:
                if np.abs(lst_time[i + 1] - lst_time[i]) == step_duration:
                    if not period:
                        period.append([lst_time[i]])
                    elif len(period[-1]) == 2:
                        period.append([lst_time[i]])
                else:
                    period[-1].append(lst_time[i])
            else:
                period[-1].append(lst_time[i])
        return period

    @classmethod
    def get_part_wav_bytes(cls, path_wav, count, count_start_answer, count_stop_answer):
        k = 0
        with open(path_wav, 'rb') as f:
            while True:
                if k == count_start_answer:
                    data = f.read(count * int(count_stop_answer - count_start_answer))
                    break
                else:
                    f.read(count)
                k += 1
        return data




def check_city_isincluded(text, lst_cities, lst_sub):
    text_normal_form = [morph.normal_forms(i)[0] for i in text.lower().split()]
    city = ' '.join([i for i in text_normal_form if any(i in j.split() for j in  lst_cities)])
    sub = ' '.join([i for i in text_normal_form if any(i in j.split() for j in lst_sub)])
    return ';'.join([sub, city])



def main():
    flag_verbose = True
    model_path_kaldi_local = os.path.join('data', 'models', 'kaldi-ru-0.6')
    folder_record = os.path.join('/', 'mnt', 'monitor', '2020-01-28')
    #### dict users #########################
    users = {'903*******': 'user1',
             '903*******': 'user2'}
    ########################################
    path_cities_all = os.path.join('data', 'pop_cities_all_2019.xlsx')
    path_privet_wav = os.path.join('data', 'sounds', 'privet.wav')
    path_repeat_answer_wav = os.path.join('data', 'sounds', 'repeat_answer.wav')
    path_what_city_answer_wav = os.path.join('data', 'sounds', 'what_city.wav')
    path_bye_wav = os.path.join('data', 'sounds', 'bye.wav')
    step_duration = 0.5
    sample_rate, sample_size_bytes = 8000, 2
    model_vosk = Model(os.path.join('data', 'models', 'alphacep-model-android-ru-0.3'))#хотя модель только на 16 kz
    kaldi_rec_vosk = KaldiRecognizer(model_vosk, sample_rate)
    energy_threshold_in = 100 # для человека кто отвечает на звонок
    energy_threshold_out = 1 # запись или google tts
    output_folder = 'output'
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    writer = pd.ExcelWriter(os.path.join(output_folder, folder_record.split('/')[-1] + '_.xlsx'))
    wav_info = WavTools()
    #получаем длительности звуковых приветствий с точностью до step_duration
    privet_dur = wav_info.get_duration_wav(path_privet_wav, step_duration)
    repeat_answer_dur = wav_info.get_duration_wav(path_repeat_answer_wav, step_duration)
    what_city_answer_dur = wav_info.get_duration_wav(path_what_city_answer_wav, step_duration)
    bye_dur = wav_info.get_duration_wav(path_bye_wav, step_duration)
    df_citi_all = pd.read_excel(path_cities_all)
    lst_cities = df_citi_all['gor'].values.tolist()
    lst_sub = df_citi_all['sub'].values.tolist()
    del df_citi_all
    lst_cities = [re_only_text.sub(' ', re_cyr_only.sub(' ', i)).lower() for i in lst_cities] #оставляем толко кириллицу
    lst_cities = [' '.join([morph.normal_forms(j)[0] for j in i.split()]) for i in lst_cities]#приводим города в нормальную форму
    lst_cities = np.unique(lst_cities).tolist()
    lst_sub = [re_only_text.sub(' ', re_cyr_only.sub(' ', i)).lower() for i in lst_sub]
    lst_sub = [' '.join([morph.normal_forms(j)[0] for j in i.split()]) for i in lst_sub]
    lst_sub = np.unique(lst_sub).tolist()
    if flag_verbose:
        print(100*'#')
        print(f'длительность звуковых файлов в секундах с округлением до {step_duration} секунд:')
        print(f'privet.wav = {privet_dur}')
        print(f'repeat_answer.wav = {repeat_answer_dur}')
        print(f'what_city.wav = {what_city_answer_dur}')
        print(f'bye.wav = {bye_dur}')
        print(100*'#')
        print('список городов:')
        print(', '.join(lst_cities))
    for address, dirs, files in os.walk(folder_record):
        lst_wav = []
        for file_wav in files:
            if file_wav.endswith('wav'):
                lst_wav.append(file_wav)
        sheet_name = address.split('/')[-1]
        if lst_wav:
            lst_wav = sorted(lst_wav)
            lst_wav = [(lst_wav[i], lst_wav[i+1]) for i in range(0, len(lst_wav), 2)]
        else:
            continue

        df_info_wav = pd.DataFrame(columns=['id', 'user', 'number', 'time', 'duration', 'privet_question', 'privet_answer',
                                   'repeat_question', 'repeat_answer', 'city_question',
                                   'city_answer', 'bye', 'simultaneously_with_bot', 'Результат', 'Update',
                                   'Комментарий'])
        df_city_answer = pd.DataFrame(
            columns=['id', 'user', 'number', 'time', 'kaldi_docker', 'kaldi_local', 'kaldi_vosk', 'google',
                     'city_isincluded_kaldi_docker', 'city_isincluded_kaldi_local', 'city_isincluded_kaldi_vosk',
                     'city_isincluded_google'])
        for item in lst_wav:
            temp_dict = {k: '' for k in df_info_wav.columns.tolist()}
            temp_dict_city = {k: '' for k in df_city_answer.columns.tolist()}
            abonent = item[0].split('-')[2][1:]
            temp_dict['id'] = '-'.join(item[0].split('-')[:-1])
            temp_dict['user'] = users[abonent]
            temp_dict['number'] = abonent
            part_data = ''.join(item[0].split('-')[:2])
            date_time_str = part_data[:4] + str('-') + part_data[4:6] + str('-') + part_data[6:8] + str(
                ' ') + part_data[8:10] + \
                            str(':') + part_data[10:12] + str(':') + part_data[12:14]
            date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
            temp_dict['time'] = date_time_obj
            in_wav = item[0]
            out_wav = item[1]
            in_dur = wav_info.get_duration_wav(os.path.join(address, in_wav), step_duration)
            temp_dict['duration'] = in_dur
            lst_time_say_in = wav_info.get_energy_say(os.path.join(address, in_wav), sample_rate,
                sample_size_bytes, step_duration, energy_threshold_in)#время в секундах когда человек говорил
            lst_time_say_out = wav_info.get_energy_say(os.path.join(address, out_wav), sample_rate,
                                                       sample_size_bytes, step_duration, energy_threshold_out)#время в секундах когда робот задавал вопрос
            period_say_in = wav_info.find_period_say(lst_time_say_in, step_duration)#преобразование времени в интервалы когда говорил человек
            period_say_out = wav_info.find_period_say(lst_time_say_out, step_duration)#преобразование времени в интервалы когда говорил робот

            out_dict = {}
            count_none = 0
            for item in period_say_out:
                if (item[1] - item[0]) == privet_dur:
                    out_dict['privet'] = item#приветствие проиграло полностью
                elif (item[1] - item[0]) == what_city_answer_dur or (item[1] - item[0]) == int(what_city_answer_dur) + 1:#вопрос про город проиграл полностью
                    out_dict['what_city'] = item
                elif (item[1] - item[0]) == repeat_answer_dur or (item[1] - item[0]) == int(repeat_answer_dur) + 1:#просьба повторить проиграла полностью
                    out_dict['repeat'] = item
                elif (item[1] - item[0]) == bye_dur:#прощание проиграло полностью
                    out_dict['bye'] = item
                else:
                    out_dict['none_' + str(count_none)] = item #не распознанный интервал
                    count_none += 1
            del count_none

            out_dict = dict(sorted(out_dict.items(), key=lambda x: x[1]))# словарь временных интервалов робота
            count_bytes = int(sample_rate * sample_size_bytes * step_duration)# сколько байтов в одном шаге step_duration
            if 'privet' in out_dict.keys():
                temp_dict['privet_question'] = 1
                count_start_answer = out_dict['privet'][1] / step_duration #время окончания приветствия
                count_stop_answer = out_dict[list(out_dict.keys())[list(out_dict.keys()).index('privet') + 1]][
                                        0] / step_duration #время начала следующего вопроса за приветствием
                temp_dict['privet_answer'] = rcgn_kaldi_docker(path_wav=os.path.join(address, in_wav), count=count_bytes,
                                                      count_start_answer=count_start_answer,
                                                      count_stop_answer=count_stop_answer)
            else:
                temp_dict['privet_question'] = 0


            if 'repeat' in out_dict.keys():
                temp_dict['repeat_question'] = 1
                count_start_answer = out_dict['repeat'][1] / step_duration#время окончания просьбы повторить ответ
                count_stop_answer = out_dict[list(out_dict.keys())[list(out_dict.keys()).index('repeat') + 1]][
                                        0] / step_duration #время начала следующего вопроса
                temp_dict['repeat_answer'] = rcgn_kaldi_docker(path_wav=os.path.join(address, in_wav), count=count_bytes,
                                                      count_start_answer=count_start_answer,
                                                      count_stop_answer=count_stop_answer)
            else:
                temp_dict['repeat_question'] = 0

            if 'what_city' in out_dict.keys():
                temp_dict['city_question'] = 1
                '''
                может быть несколько фраз
                count_start_answer - всегда после речи бота 
                count_stop_answer - из  period_say_in
                '''
                count_start_answer = out_dict['what_city'][1] / step_duration #время окончания вопроса про город
                # count_start_answer = int([i for i in period_say_in if i[0] >= out_dict['what_city'][1]][0][0]/step_duration)
                # [i for i in period_say_in if i[0] >= out_dict['what_city'][1]] - все периоды
                count_stop_answer = out_dict[list(out_dict.keys())[list(out_dict.keys()).index('what_city') + 1]][
                                        0] / step_duration
                # count_stop_answer = int([i for i in period_say_in if i[0] >= out_dict['what_city'][1]][0][-1] / step_duration) + 2
                temp_dict['city_answer'] = rcgn_kaldi_docker(path_wav=os.path.join(address, in_wav), count=count_bytes,
                                                    count_start_answer=count_start_answer,
                                                    count_stop_answer=count_stop_answer)
                temp_dict_city['id'] = temp_dict['id']
                temp_dict_city['user'] = temp_dict['user']
                temp_dict_city['time'] = temp_dict['time']
                temp_dict_city['kaldi_docker'] = temp_dict['city_answer']
                frame_data = wav_info.get_part_wav_bytes(path_wav=os.path.join(address, in_wav), count=count_bytes,
                                                count_start_answer=count_start_answer,
                                                count_stop_answer=count_stop_answer)

                temp_dict_city['kaldi_vosk'] = rcgn_kaldi_vosk(frame_data=frame_data, kaldi_rec_vosk=kaldi_rec_vosk)
                temp_dict_city['kaldi_local'] = rcgn_kaldi_local(model_path=model_path_kaldi_local, frame_data=frame_data, sample_rate=sample_rate,
                                                             sample_size_bytes=sample_size_bytes)

                temp_dict_city['google'] = rcgn_google(frame_data=frame_data, sample_rate=sample_rate,
                                                       sample_size_bytes=sample_size_bytes)

                ###### city is included #####
                temp_dict_city['city_isincluded_kaldi_docker'] = check_city_isincluded(temp_dict_city['kaldi_docker'], lst_cities, lst_sub)
                temp_dict_city['city_isincluded_kaldi_local'] = check_city_isincluded(temp_dict_city['kaldi_local'], lst_cities, lst_sub)
                temp_dict_city['city_isincluded_kaldi_vosk'] = check_city_isincluded(temp_dict_city['kaldi_vosk'], lst_cities, lst_sub)
                temp_dict_city['city_isincluded_google'] = check_city_isincluded(temp_dict_city['google'], lst_cities, lst_sub)


            else:
                temp_dict['city_question'] = 0

            if 'bye' in out_dict.keys():
                temp_dict['bye'] = 1
            else:
                temp_dict['bye'] = 0

            period_speak_bot = [item_in for item_in in period_say_in if any(
                item_out[0] <= item_in[0] and item_out[1] >= item_in[1] for item_out in period_say_out)]

            if period_speak_bot:
                speak_bot_text = []
                for item in period_speak_bot:
                    count_start_answer = item[0] / step_duration
                    count_stop_answer = (item[1] / step_duration) + 2
                    speak_bot_text.append(rcgn_kaldi_docker(path_wav=os.path.join(address, in_wav), count=count_bytes,
                                                   count_start_answer=count_start_answer,
                                                   count_stop_answer=count_stop_answer))
                speak_bot_text = [item for item in speak_bot_text if item != str()]
                if speak_bot_text:
                    temp_dict['simultaneously_with_bot'] = ';'.join(speak_bot_text)
                else:
                    temp_dict['simultaneously_with_bot'] = 1
            else:
                temp_dict['simultaneously_with_bot'] = 0



            df_info_wav = df_info_wav.append(temp_dict, ignore_index=True)
            if temp_dict['city_question'] == 1:
                df_city_answer = df_city_answer.append(temp_dict_city, ignore_index=True)


        df_info_wav.to_excel(writer, index=False, sheet_name=str(sheet_name))
        df_city_answer.to_excel(writer, index=False, sheet_name='city_answer'+str(sheet_name))

    writer.save()
    writer.close()






if __name__ == '__main__':
    morph = pymorphy2.MorphAnalyzer()
    re_cyr_only = re.compile(r'[^А-Яа-я]')
    re_only_text = re.compile(r"[{}]".format(string.punctuation + string.whitespace))
    main()





