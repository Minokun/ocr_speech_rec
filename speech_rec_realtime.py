# -*- coding: utf-8 -*-
import subprocess
import pyaudio
import numpy as np
import wave
import whisper
import zhconv
import time
from collections import deque
import paho.mqtt.client as mqtt
import logging
from logging.handlers import RotatingFileHandler
import os, json
from math import ceil

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

def connect_mqtt():
    reconnect_count = 0
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
        # 等待5秒后重连
        time.sleep(5)
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
    
speech_config = '/data/ai/speech_config.json'    

if not os.path.exists(speech_config):
    with open(speech_config, 'w') as fp:
        json.dump({"MODEL_TYPE":0,"RTSP_URL":"rtsp://10.0.75.22:554/stream0/asound_rockchipes83881?secret=035c73f7-bb6b-4889-a715-d9eb2d1925cc"}, fp)

rtsp_url_env = os.environ.get('RTSP_URL')
with open(speech_config, 'r') as f:
    config = json.load(f)
    rtsp_url = config['RTSP_URL'] if not rtsp_url_env else rtsp_url_env
    model_type = config['MODEL_TYPE']
if model_type == '1':  
    model = whisper.load_model("/usr/lib/wpm/base.pt")
elif model_type == '2':
    model = whisper.load_model("/usr/lib/wpm/small.pt")
else:
    model = whisper.load_model("/usr/lib/wpm/tiny.pt")

# 设置录音参数
RATE = 44100
CHUNKSIZE = 1024 * 2
ENERGY_THRESHOLD = 250  # 门限
energy_queue = deque(maxlen=100) # 门限能量值计算队列
audio_cache = deque(maxlen=15)  # 保留最近20帧音频数据

def speech_rec():
    global ENERGY_THRESHOLD
    process = subprocess.Popen(
        ['ffmpeg', '-i', rtsp_url, '-vn', '-f', 's16le', '-ar', '44100', '-ac', '1', '-acodec', 'pcm_s16le', '-'],
        stdout=subprocess.PIPE)
    # 初始化PyAudio
    p = pyaudio.PyAudio()

    # 初始化变量
    frames = []  # 存储录音数据的列表
    recording = False  # 是否正在录音
    n = 0
    record_frame_count = 0
    last_energy_calculation_time = time.time()

    while True:
        # 从FFmpeg进程中读取音频数据
        data = process.stdout.read(CHUNKSIZE)
        if data == b'':
            error_logger.error("RTSP ERROR!Reconnect RTSP <" + rtsp_url + "> ......" )
            time.sleep(3)
            process = subprocess.Popen(
                ['ffmpeg', '-i', rtsp_url, '-vn', '-f', 's16le', '-ar', '44100', '-ac', '1', '-acodec', 'pcm_s16le', '-'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            print("重新链接......")
            continue

        # 将音频数据转换为numpy数组
        data = np.frombuffer(data, dtype=np.int16)
        cur_energy = np.sum(np.abs(data)) / len(data)
        energy_queue.append(cur_energy)
        audio_cache.append(data)

        # 判断是否开始录音
        if cur_energy > ENERGY_THRESHOLD and not recording:
            recording = True
            n += 1
            print("Start recording", cur_energy, ENERGY_THRESHOLD)
            start_time = time.time()
            # 将此时开始前20帧数据加入frame
            for i in range(len(audio_cache)):
                frames.append(audio_cache[i].tobytes())

        # 判断是否结束录音
        if cur_energy <= ENERGY_THRESHOLD and recording:
            record_frame_count += 1
            if record_frame_count > 20:
                recording = False
                record_frame_count = 0
                print("Stop recording")
                # 保存录音数据
                wav_path =  os.path.join(ai_audio_path, str(int(start_time)) + ".wav")
                wf = wave.open(wav_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                frames = []
                result = model.transcribe(wav_path, language="Chinese")
                # 清理音频文件
                os.remove(wav_path)
                audio_rec_time = time.time() - start_time
                text_result = zhconv.convert(result['text'], 'zh-cn')
                if len(result['segments']) == 0:
                    error_logger.error("No speech content recgnation")
                    print(result)
                    continue
                duration = ceil(max([i['end'] for i in result['segments']]))
                print("********** 识别时间: " + str(audio_rec_time) + " **********")
                # 组织返回的数据
                data = {
                    "rtsp_id": rtsp_url,
                    "start_time": int(start_time) - 1,
                    "duration": duration,
                    "text": text_result,
                    "energy_threashold": ENERGY_THRESHOLD
                }
                # 发送消息
                send_mqtt_msg(data)

        # 每隔30s计算能量门限
        if time.time() - last_energy_calculation_time >= 10:
            print("计算能量门限，当前值：" + str(ENERGY_THRESHOLD), cur_energy)
            last_energy_calculation_time = time.time()
            ENERGY_THRESHOLD = np.percentile(np.array(energy_queue), (15))  * 1.1
            # 此处注意，最低100
            ENERGY_THRESHOLD = ENERGY_THRESHOLD if ENERGY_THRESHOLD > 100 else 100


        # 存储录音数据
        if recording:
            frames.append(data.tobytes())
            

    # 关闭PyAudio
    p.terminate()

if __name__ == "__main__":
    speech_rec()