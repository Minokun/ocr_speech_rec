# -*- coding: utf-8 -*-
import time
import threading
import ocr
import speech_rec
import send_mqtt
import queue

def start_threads():
    message_queue = queue.Queue()
    wait_rec_audio_queue = queue.Queue()
    # 启动线程
    # 语音识别
    record_thread = threading.Thread(target=speech_rec.main, args=(message_queue,))
    # ocr识别
    ocr_thread = threading.Thread(target=ocr.ocr_rec, args=(message_queue,))
    # mqtt消费
    mqtt_thread = threading.Thread(target=send_mqtt.send, args=(message_queue,))

    record_thread.start()
    ocr_thread.start()
    mqtt_thread.start()

    while True:
        # 监控线程状态
        if not record_thread.is_alive():
            print("Speech processing terminated. Restarting...")
            print("Restarting worker 1...")
            record_thread = threading.Thread(target=speech_rec.main, args=(message_queue,))
            record_thread.start()
        if not ocr_thread.is_alive():
            print("Ocr processing terminated. Restarting...")
            print("Restarting worker 2...")
            ocr_thread = threading.Thread(target=ocr.ocr_rec, args=(message_queue,))
            ocr_thread.start()
        if not mqtt_thread.is_alive():
            print("Ocr processing terminated. Restarting...")
            print("Restarting worker 3...")
            mqtt_thread = threading.Thread(target=send_mqtt.send, args=(message_queue,))
            mqtt_thread.start()
        # 等待一段时间
        time.sleep(3)

if __name__ == "__main__":
    start_threads()