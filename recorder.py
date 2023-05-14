import subprocess
import numpy as np
import wave
from collections import deque
import os, json
import time
import pyaudio

def read_audio_stream(wait_rec_audio_queue):
    # 设置录音参数
    RATE = 44100
    CHUNKSIZE = 1024 * 2
    ENERGY_THRESHOLD = 250  # 门限
    energy_queue = deque(maxlen=100) # 门限能量值计算队列
    audio_cache = deque(maxlen=15)  # 保留最近20帧音频数据
    speech_config = '/data/ai/speech_config.json'    

    if not os.path.exists(speech_config):
        with open(speech_config, 'w') as fp:
            json.dump({"MODEL_TYPE":0,"RTSP_URL":"rtsp://10.0.75.22:554/stream0/asound_rockchipes83881?secret=035c73f7-bb6b-4889-a715-d9eb2d1925cc"}, fp)

    rtsp_url_env = os.environ.get('RTSP_URL')
    with open(speech_config, 'r') as f:
        config = json.load(f)
        rtsp_url = config['RTSP_URL'] if not rtsp_url_env else rtsp_url_env
        model_type = config['MODEL_TYPE']
    print("当前音频流：" + rtsp_url)

    process = subprocess.Popen(
        ['ffmpeg', '-i', rtsp_url, '-vn', '-f', 's16le', '-ar', '44100', '-ac', '1', '-acodec', 'pcm_s16le', '-'],
        stdout=subprocess.PIPE)

    frames = []  # 存储录音数据的列表
    recording = False  # 是否正在录音
    n = 0
    record_frame_count = 0
    last_energy_calculation_time = time.time()
    p = pyaudio.PyAudio()

    while True:
        # 从FFmpeg进程中读取音频数据
        data = process.stdout.read(CHUNKSIZE)
        if data == b'':
            print("RTSP ERROR!Reconnect RTSP <" + rtsp_url + "> ......")
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
                wav_path = os.path.join('/data/ai/audio', str(int(start_time)) + ".wav")
                wf = wave.open(wav_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                frames = []
                # 识别队列里加入该文件
                wait_rec_audio_queue.put((wav_path, ENERGY_THRESHOLD))

        # 每隔30s计算能量门限
        if time.time() - last_energy_calculation_time >= 10:
            print("计算能量门限，当前值：" + str(ENERGY_THRESHOLD), cur_energy)
            last_energy_calculation_time = time.time()
            ENERGY_THRESHOLD = np.percentile(np.array(energy_queue), (15))  * 1.1
            # 此处注意，最低100
            ENERGY_THRESHOLD = ENERGY_THRESHOLD if ENERGY_THRESHOLD > 250 else 100

        # 存储录音数据
        if recording:
            frames.append(data.tobytes())