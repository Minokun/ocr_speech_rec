# -*- coding: utf-8 -*-
import whisper
import zhconv
import time
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
import os, json
from math import ceil
import queue
from recorder import read_audio_stream
from threading import Thread
import wave
import numpy as np

error_logger = logging.getLogger(__name__)
 
# 日志文件
ai_log_path = '/data/ai/ai.log'    
ai_audio_path = '/data/ai/audio'
# 字典文件 json字典文件中char_map为替换的单字,words为替换的词语
with open('speech_command_dict.json', 'r') as f:
    speech_command_dict = json.load(f)
    
#  正式：rtsp://127.0.0.1:554/stream0/asound_rockchiphdmi   测试用：export RTSP_URL=rtmp://192.168.1.8:1935/live/1
# 设置错误信息日志的保存位置和文件名
file_handler = RotatingFileHandler(ai_log_path, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
error_logger.addHandler(file_handler)
error_logger.setLevel(logging.ERROR)

if not os.path.exists(ai_audio_path):
    os.makedirs(ai_audio_path)
else:
    # 清理掉ai_audio_path下的所有文件
    for file_name in os.listdir(ai_audio_path):
        file_path = os.path.join(ai_audio_path, file_name)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            error_logger.error("Unable to delete file: " + str(e))

def speech_rec(wait_rec_audio_queue, message_queue,):
        
    """
    语音识别函数
    :param wait_rec_audio_queue: 存放音频文件地址和能量阈值的队列
    :param message_queue: 存放识别结果的队列
    """

    speech_config = '/data/ai/speech_config.json'
    rtsp_url_env = os.environ.get('RTSP_URL')
    try: 
        with open(speech_config, 'r') as f:
            config = json.load(f)
            rtsp_url = config['RTSP_URL'] if not rtsp_url_env else rtsp_url_env
            model_type = str(config['MODEL_TYPE'])
    except Exception as e:
        rtsp_url = '......'
        model_type = '1'
        
    if model_type == '1':  
        model = whisper.load_model("/usr/lib/wpm/base.pt")
    elif model_type == '2':
        model = whisper.load_model("/usr/lib/wpm/small.pt")
    elif model_type == '3':
        model = whisper.load_model("/usr/lib/wpm/medium.pt")
    else:
        model = whisper.load_model("/usr/lib/wpm/tiny.pt")
    # 第一次启动程序识别
    # result = model.transcribe('start_voice.mp3', language="Chinese")
    # print(result['text'])
    result = model.transcribe('start_test.wav', language="Chinese")
    print(result['text'])

    while True:
        wav_path, ENERGY_THRESHOLD = wait_rec_audio_queue.get()
        start_time = time.time()
        # with wave.open(wav_path, 'rb') as wav_file:
        #     audio_data = wav_file.readframes(-1)
        #     audio_data = np.frombuffer(audio_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0
        if not os.path.exists(wav_path):
            continue

        for i in range(5):
            try:
                print("%s speech rec start..." % wav_path)
                result = model.transcribe(wav_path, language="Chinese")
                break
            except Exception as e:
                print(e)
                time.sleep(0.1)

        audio_rec_time = time.time() - start_time
        audio_start_time = int(wav_path.split('/')[-1].split('.')[0]) - 1

        segments = result['segments']
        if len(segments) == 0:
            print("No speech content recgnation")
            continue

        duration = ceil(max([i['end'] for i in segments])) + 1
        text_result = zhconv.convert(result['text'], 'zh-cn')
        text_result = text_translate(text_result)
        # 清理音频文件
        if os.path.exists(wav_path):
            os.remove(wav_path)

        print("********************************************************* 推理时间: %d 等待时间：%f 音频时长：%f " % (audio_rec_time, time.time() - audio_start_time, duration))
        print("********************************************************* 识别内容: " + result['text'])
        print("********************************************************* 翻译内容: " + text_result)
        
        # 组织返回的数据
        data = {
            "rtsp_id": rtsp_url,
            "start_time": audio_start_time,
            "duration": duration,
            "text": text_result,
            "energy_threashold": ENERGY_THRESHOLD
        }
        # 发送消息
        message_queue.put((1, data))

def main(message_queue):
    # 注意 这个队列中存的是两个值，一个音频文件地址 一个energy_threashold
    wait_rec_audio_queue = queue.Queue()
    get_rec_audio = Thread(target=read_audio_stream, args=(wait_rec_audio_queue,))
    rec_audio = Thread(target=speech_rec, args=(wait_rec_audio_queue, message_queue,))
    get_rec_audio.start()
    rec_audio.start()
    wait_rec_audio_queue.join()
    get_rec_audio.join()
    rec_audio.join()
    
def text_translate(text):
    """
    翻译文本
    :param text: 待翻译文本
    :return: 翻译后文本
    """
    global speech_command_dict
    char_map = speech_command_dict['char_map']
    words = speech_command_dict['words']

    translate_text = ""
    for o_char in text:
        if o_char in char_map:
            translate_text += char_map[o_char]
        else:
            translate_text += o_char
    
    for i in words:
        translate_text = translate_text.replace(i[0], i[1]).replace("音响", "影响").replace("Go", "9")
        
    return translate_text

if __name__ == "__main__":
    message_queue = queue.Queue()
    main(message_queue)