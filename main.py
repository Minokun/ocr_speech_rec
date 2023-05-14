# -*- coding: utf-8 -*-
import time
import threading
import ocr
import speech_rec

def start_threads():
    # 启动线程
    record_thread = threading.Thread(target=speech_rec.main)
    ocr_thread = threading.Thread(target=ocr.ocr_rec)
    record_thread.start()
    ocr_thread.start()

    while True:
        # 监控线程状态
        if not record_thread.is_alive():
            print("Speech processing terminated. Restarting...")
            print("Restarting worker 1...")
            record_thread = threading.Thread(target=speech_rec.main)
            record_thread.start()
        if not ocr_thread.is_alive():
            print("Ocr processing terminated. Restarting...")
            ocr_thread = threading.Thread(target=ocr.ocr_rec)
            ocr_thread.start()
        # 等待一段时间
        time.sleep(3)

if __name__ == "__main__":
    start_threads()