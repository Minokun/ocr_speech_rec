# -*- coding: utf-8 -*-
import time
import os
import fastdeploy as fd
import cv2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import logging
import numpy as np
 
 # 根目录
ai_root = "/data/ai"
# ocr的根目录
ocr_root = ai_root + '/ocr'
# 语音的根目录
audio_root = ai_root + '/audio'
# Check if ocr_root directory exists, if not create it
if not os.path.exists(ocr_root):
    os.makedirs(ocr_root)
# Check if audio_root directory exists, if not create it
if not os.path.exists(audio_root):
    os.makedirs(audio_root)
# ocr的相关配置文件
ocr_config_path = ai_root + '/ocr_config.json'
# 日志文件
ai_log_path = ai_root + '/ai.log'
# ocr监控的文件夹
watch_path = ocr_root

# 日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler = logging.FileHandler(ai_log_path)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 用于从 /data/ai 目录下的 ocr_config.json 文件中读取 OCR 字段的函数
def read_ocr_field():
    '''
    读取json配置文件
    '''
    global ocr_config_path, logger
    try:
        with open(ocr_config_path, 'r') as f:
            data = json.load(f)
        ocr_field = data["ocr"]
    except Exception as e:
        logger.error("Unable to load ocr_config.json file! " + str(e))
        return None
    return ocr_field

class Watcher:
    def __init__(self, message_queue):
        global watch_path
        # 发送消息的队列
        self.message_queue = message_queue
        # 需要监控的文件夹路径
        self.directory = watch_path
        self.observer = Observer()  #创建Observer对象
        # 模型路径
        self.model_dirname = '/usr/lib/pdm'
        self.model_rec = fd.vision.ocr.Recognizer(model_file=self.model_dirname + '/rec/inference.pdmodel',
                                            params_file=self.model_dirname + '/rec/inference.pdiparams',
                                            label_path=self.model_dirname + '/keys.txt')
        self.model_det = fd.vision.ocr.DBDetector(model_file=self.model_dirname + '/det/inference.pdmodel',
                                            params_file=self.model_dirname + '/det/inference.pdiparams')
        self.model = fd.vision.ocr.PPOCRv3(det_model=self.model_det, rec_model=self.model_rec)
 
    def run(self):
        event_handler = Handler(model=self.model, message_queue=self.message_queue)
        #将Observer与目录、事件处理器关联起来并启动观察
        self.observer.schedule(event_handler, self.directory, recursive=True)
        self.observer.start()  #启动Observer
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()  #停止Observer
            print("出现错误")
 
        self.observer.join()  #回收Observer
 
 
class Handler(FileSystemEventHandler):
    '''初始化OCR结果监听器（监控文件夹，并识别新生成的OCR图片）'''
    def __init__(self, model, message_queue):
        super().__init__()
        # 发送消息的队列
        self.message_queue = message_queue
        self.ocr_object_list = read_ocr_field()
        self.model = model
        
    def on_any_event(self, event):
        if event.is_directory:
            return None
 
        elif event.event_type == 'created':
            # 当文件首次创建时，在此处执行任何操作。
            if event.src_path.endswith('.jpg'):  # 如果您想检查特定的文件扩展名
                self.ocr_object_list = read_ocr_field()
                # 首先获取图片名称中的unix时间戳部分，图片名称例如：test001-1683513283000.jpg，将中间符号'-'到'.'的部分截取出来
                try:
                    img_name = event.src_path.split('/')[-1]
                    device_id = img_name.split('-')[1]
                    ts_str = img_name.split('-')[2].split('.')[0]
                    unix_ts = int(ts_str) / 1000.0 # convert milliseconds to seconds
                except Exception as e:
                    logger.error("OCR config json device_id error! Check out /data/ai/ocr pic and device_id!")
                    os.remove(event.src_path)
                    return None
                # print(f"{event.src_path} 已创建")
                time.sleep(0.3)
                img = cv2.imread(event.src_path)
                if img is None:
                    print(img.shape)
                    logger.error("OCR read pic failed!Please check out the jpg file in /data/ai/ocr!") 
                    return   

                if self.ocr_object_list is None:
                    print("全文扫描")
                    result = self.model.predict(img)
                    result_list = []
                    n = 0
                    for i in result.text:
                        result_list.append(
                            {"label": "全文", "text":i, "score": round(result.rec_scores[n], 3)}
                        ) 
                else:
                    # 根据json配置文件中的字段获取坐标值
                    result_list = []
                    for obj in self.ocr_object_list:
                        if obj['device_id'] == device_id:
                            label = obj['label']
                            x1 = int(obj['x_left'])
                            y1 = int(obj['y_left'])
                            x2 = int(obj['x_right'])
                            y2 = int(obj['y_right'])
                            # 此处ocr有bug，无法直接识别roi区域，只能先保存文件后再识别

                            img_roi = img[y1:y2, x1:x2]
                            cv2.imwrite('_bak.jpg', img_roi)
                            img_roi = cv2.imread('_bak.jpg')
                            result_o = self.model.predict(img_roi)
                            result_text = ' '.join([i for i in result_o.text])
                            score = np.mean(np.array(result_o.rec_scores))
                            result_list.append(
                                {"label":label, "text":result_text, "score": round(score, 3)}
                            )
                        # vis_im = fd.vision.vis_ppocr(img, result)
                        # cv2.imwrite("visualized_result.jpg", vis_im)
                data = {
                            "device_id": device_id,
                            "start_time": int(unix_ts),
                            "text": result_list
                        }
                        
                if len(result_list) > 0:
                    # 1 是语音消息 2是ocr消息
                    self.message_queue.put((2, data))
                
                os.remove(event.src_path)

def delete_files_in_directory(directory):
    """删除目录中的所有文件

    Args:
        directory: 要删除文件的目录路径
    """
    filelist = [f for f in os.listdir(directory)]
    for f in filelist:
        os.remove(os.path.join(directory, f))

def ocr_rec(message_queue):
    delete_files_in_directory(watch_path)
    watcher = Watcher(message_queue) # create a Watcher object to monitor the directory "/data/ocr/"
    watcher.run() # start monitoring the directory

if __name__ == "__main__":
    ocr_rec()
