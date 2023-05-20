#!/bin/bash

cp main.py build/
cp ocr.py build/
cp recorder.py build/
cp speech_rec.py build/
cp send_mqtt.py build/
cp build.sh build/
cp speech_command_dict.json build/

cd build/

echo "Starting Docker build process..."
docker build -t registry.cn-beijing.aliyuncs.com/minok/ocr_speech_rec:v2.1 .
echo "Docker build process completed."

# sudo docker login --username=2524231862@qq.com registry.cn-beijing.aliyuncs.com
# docker run -it --network=host -v /data/ai:/data/ai --rm registry.cn-beijing.aliyuncs.com/minok/ocr_speech_rec