# OCR和语音识别程序
### 该程序融合了paddle ocr和openai-whisper语音识别，构建的容器是在rk3588下。文件说明如下：
1. main.py：入口文件，在环境中执行python mian.py就可以运行ocr和语音识别程序
2. ocr.py:ocr识别程序，采用paddle ocr，用fastdeploy部署，所以注意要在环境中安装fastdeploy
3. speech_rec.py:语音识别，采用openai-whisper作为识别引擎
4. recorder.py:该代码从rtsp音频流中读取实时音频流，根据音频能量大小截取大于能量门限的语音音频部分，并保存到相应文件夹中，能量门限是动态实时计算的。
5. send_mqtt.py：该代码将识别结果以mqtt形式发送出去
6. speech_command_dict.json:是语音识别后将某些字或词替换成另外的字或词的字典。
7. start_test.wav:因为语音识别第一次需要一定时间来加载模型，所以程序一开始就识别该音频来加载模型。
8. osr_otg.sh：是程序远程离线升级脚本，该脚本会将osr_otg.tar.gz包解压到/data/ai/下并重启ai容器
9. deployed.sh：是自动构建容器脚本，该脚本会自动将最新代码构建成容器，注意，一定要在rk3588环境下
10. otg:文件夹是将需要远程离线升级的放入的地方
11. build:文件夹是自动构建容器文件夹

## 安装
### 拉取ubuntu镜像 安装python3.10

```bash
sudo apt udpate -y
sudo apt install python3.10 python3-dev python3-pip -y
sudo ln -s /usr/bin/python3.10 /usr/bin/python

```

### 安装pyaudio

```bash
# 在arm板上直接安装pyaudio报错，就先安装这个
sudo apt install portaudio19-dev -y
# 安装zhconv 繁体转简体
pip install -i https://pypi.douban.com/simple/ pyaudio zhconv paho-mqtt openai-whisper numpy watchdog opencv-python Cython
# 安装fastdeploy GPU版
pip install numpy opencv-python fastdeploy-gpu-python -f https://www.paddlepaddle.org.cn/whl/fastdeploy.html
# CPU版
pip install numpy opencv-python fastdeploy-python -f https://www.paddlepaddle.org.cn/whl/fastdeploy.html

apt install ffmpeg
# 测试rtmp语音是否可以播放
ffplay -i rtmp://192.168.1.8:1935/live/1 -nodisp -loglevel quiet -vn -autoexit
```
### 注意登陆docker:
```commandline
sudo docker login --username=2524231862@qq.com registry.cn-beijing.aliyuncs.com
```

### 修改程序后，自动构建容器
```commandline
sh ./deployed.sh
```

### 运行
```shell
# 直接运行：
python main.py
# 容器运行
docker run -it -d --restart=unless-stopped --cpus=4 --network=host -v /data/ai:/data/ai --name ocr_speech_rec registry.cn-beijing.aliyuncs.com/minok/ocr_speech_rec /bin/bash
```

### 升级
1. 升级最新容器镜像，直接重新构建就行，执行命令：sh ./deployed.sh
2. 离线远程升级，升级的时候在远程机器上运行osr_otg.sh，该脚本会将osr_otg.tar.gz包解压至/data/ai/下并重启容器，容器运行时自动扫描/data/ai/otg文件夹，如有将替换相应文件运行
```shell
# 将升级文件放入otg中
# 将otg文件打包成osr_otg.tar.gz文件
tar -zxvf osr_otg.tar.gz otg
```
