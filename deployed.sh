#!/bin/bash

cp main.py build/
cp ocr.py build/
cp recorder.py build/
cp speech_rec.py build/

cd build/

echo "Starting Docker build process..."
docker build -t minokun/ocr_speech_rec:v2.0 .
echo "Docker build process completed."

# docker run -it --network=host -v /data/ai:/data/ai --rm minokun/ocr_speech_rec:v2.0 /bin/bash