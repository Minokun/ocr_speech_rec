import paho.mqtt.client as mqtt
import logging
import json
import time

error_logger = logging.getLogger(__name__)
# 日志文件
ai_log_path = '/data/ai/ai.log'
type_topic = ["/sys/ts/messagebus/20230506151601", "/sys/ts/messagebus/20230506151602"]

reconnect_count = 0
global message_cache

def connect_mqtt():
    global message_cache
    '''发送MQTT消息的函数'''
    def on_connect(client, userdata, flags, rc):
        '''连接成功回调函数'''
        print("Connected with result code "+str(rc))
    def on_publish(client, userdata, result):
        '''消息发布成功回调函数'''
        # print("Data published successfully")
        pass
        
    def on_disconnect(client, userdata, rc=0):
        global reconnect_count, message_cache
        reconnect_count = reconnect_count + 1
        print("Disconnected with result code "+str(rc))
        print("Reconnecting ", reconnect_count, client, userdata)
        # 等待3秒后重连
        time.sleep(3)
        client.connect("127.0.0.1", 1883)
        topic = type_topic[0] if message_cache[0] == 1 else type_topic[1]
        data = message_cache[1]
        print(message_cache, topic)
        client.publish(topic, data)

    global logger
    client = mqtt.Client(client_id="ai202305061516")
    client.username_pw_set(username="ts", password="123")
    client.on_connect = on_connect
    client.on_publish = on_publish
    # 绑定断开连接回调  
    client.on_disconnect = on_disconnect  
    while True:
        try:
            client.connect("127.0.0.1", 1883)
            return client
        except:
            # 如果连接mqtt失败，则在/data/ai/ai.log日志文件中加入报错信息
            error_logger.error("Unable to establish MQTT connection, reconnect after 3s...")
        time.sleep(3)

mqtt_client = connect_mqtt()

def send_mqtt_msg(data_type, data):
    # 发送mqtt消息，语音订阅命令：mosquitto_sub -t "/sys/ts/messagebus/20230506151601" -u ts -P 123
    # 发送mqtt消息，ocr订阅命令：mosquitto_sub -t "/sys/ts/messagebus/20230506151602" -u ts -P 123
    global mqtt_client, message_cache

    if data_type == 1:
        msg_topic = type_topic[0]
    else:
        msg_topic = type_topic[1]

    msg_content = {
            "appType": "20230506151601",
            "cmdType": "1001",
            "data": data
    }
    message_cache = (msg_topic, json.dumps(msg_content))
    mqtt_client.publish(msg_topic, json.dumps(msg_content))

def send(message_queue):
    while True:
        data_type, data = message_queue.get()
        send_mqtt_msg(data_type, data)