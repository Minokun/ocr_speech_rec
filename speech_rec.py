# -*- coding: utf-8 -*-
import whisper
import zhconv
import time
from collections import deque
import paho.mqtt.client as mqtt
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
            logger.error("Unable to delete file: " + str(e))
 
#  正式：rtsp://127.0.0.1:554/stream0/asound_rockchiphdmi   测试用：export RTSP_URL=rtmp://192.168.1.8:1935/live/1
# 设置错误信息日志的保存位置和文件名
file_handler = RotatingFileHandler(ai_log_path, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
error_logger.addHandler(file_handler)
error_logger.setLevel(logging.ERROR)

reconnect_count = 0
def connect_mqtt():
    '''发送MQTT消息的函数'''
    def on_connect(client, userdata, flags, rc):
        '''连接成功回调函数'''
        print("Connected with result code "+str(rc))
    def on_publish(client, userdata, result):
        '''消息发布成功回调函数'''
        print("Data published successfully")
        
    def on_disconnect(client, userdata, rc=0):
        global reconnect_count 
        reconnect_count = reconnect_count + 1
        print("Disconnected with result code "+str(rc))
        print("Reconnecting ", reconnect_count)
        # 等待3秒后重连
        time.sleep(3)
        client.connect("127.0.0.1", 1883)

    global logger
    client = mqtt.Client(client_id="ai202305061516")
    client.username_pw_set(username="ts", password="123")
    client.on_connect = on_connect
    client.on_publish = on_publish
    # 绑定断开连接回调  
    client.on_disconnect = on_disconnect  
    while True:
        try:
            client.connect("127.0.0.1", 1883, 60)
            return client
        except:
            # 如果连接mqtt失败，则在/data/ai/ai.log日志文件中加入报错信息
            logger.error("Unable to establish MQTT connection, reconnect after 3s...")
        time.sleep(3)

mqtt_client = connect_mqtt()

def send_mqtt_msg(data):
    # 发送mqtt消息，订阅命令：mosquitto_sub -t "/sys/ts/messagebus/20230506151601" -u ts -P 123
    global mqtt_client
    msg_topic = "/sys/ts/messagebus/20230506151601"
    msg_content = {
            "appType": "20230506151601",
            "cmdType": "1001",
            "data": data
    }
    print(msg_content)
    mqtt_client.publish(msg_topic, json.dumps(msg_content))


def speech_rec(wait_rec_audio_queue):
    speech_config = '/data/ai/speech_config.json'
    rtsp_url_env = os.environ.get('RTSP_URL')
    try: 
        with open(speech_config, 'r') as f:
            config = json.load(f)
            rtsp_url = config['RTSP_URL'] if not rtsp_url_env else rtsp_url_env
            model_type = config['MODEL_TYPE']
    except Exception as e:
        rtsp_url = '......'
        model_type = '1'
    
    if model_type == '1':  
        model = whisper.load_model("/usr/lib/wpm/base.pt")
    elif model_type == '2':
        model = whisper.load_model("/usr/lib/wpm/small.pt")
    else:
        model = whisper.load_model("/usr/lib/wpm/tiny.pt")

    while True:
        wav_path, ENERGY_THRESHOLD = wait_rec_audio_queue.get()
        start_time = time.time()
        # with wave.open(wav_path, 'rb') as wav_file:
        #     audio_data = wav_file.readframes(-1)
        #     audio_data = np.frombuffer(audio_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0
        result = model.transcribe(wav_path, language="Chinese")
        # 清理音频文件
        os.remove(wav_path)
        audio_rec_time = time.time() - start_time
        text_result = zhconv.convert(result['text'], 'zh-cn')
        if len(result['segments']) == 0:
            print("No speech content recgnation")
            continue

        duration = ceil(max([i['end'] for i in result['segments']])) + 1
        print("********** 识别时间: " + str(audio_rec_time) + " **********")
        # 组织返回的数据
        audio_start_time = int(wav_path.split('/')[-1].split('.')[0]) - 1
        data = {
            "rtsp_id": rtsp_url,
            "start_time": audio_start_time,
            "duration": duration,
            "text": text_result,
            "energy_threashold": ENERGY_THRESHOLD
        }
        # 发送消息
        send_mqtt_msg(data)

def main():
    # 注意 这个队列中存的是两个值，一个音频文件地址 一个energy_threashold
    wait_rec_audio_queue = queue.Queue()
    get_rec_audio = Thread(target=read_audio_stream, args=(wait_rec_audio_queue,))
    rec_audio = Thread(target=speech_rec, args=(wait_rec_audio_queue, ))
    get_rec_audio.start()
    rec_audio.start()
    wait_rec_audio_queue.join()
    get_rec_audio.join()
    rec_audio.join()
    

if __name__ == "__main__":
    main()