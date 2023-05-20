src_pic_path = "/data/ai/HDMI-camera2-1683786323954.jpg"
dist_pic_path = "/data/ai/ocr"

import shutil
import time

while True:
    shutil.copy(src_pic_path, dist_pic_path)
    time.sleep(2)
