#!/bin/bash

cythonize ocr.py
cythonize recorder.py
cythonize speech_rec.py
cythonize send_mqtt.py
gcc -finput-charset=utf-8 -fPIC -shared ocr.c -o ocr.so -I/usr/include/python3.10 -L/usr/lib/python3.10/config-3.10-aarch64-linux-gnu
gcc -finput-charset=utf-8 -fPIC -shared recorder.c -o recorder.so -I/usr/include/python3.10 -L/usr/lib/python3.10/config-3.10-aarch64-linux-gnu
gcc -finput-charset=utf-8 -fPIC -shared speech_rec.c -o speech_rec.so -I/usr/include/python3.10 -L/usr/lib/python3.10/config-3.10-aarch64-linux-gnu
gcc -finput-charset=utf-8 -fPIC -shared send_mqtt.c -o send_mqtt.so -I/usr/include/python3.10 -L/usr/lib/python3.10/config-3.10-aarch64-linux-gnu
rm -rf *.c
find . -type f ! -name 'main.py' -name '*.py' -exec rm -f {} +