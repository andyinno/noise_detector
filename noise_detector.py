#!/usr/bin/env python3

import yaml
import numpy as np
import sounddevice as sd
import paho.mqtt.client as mqtt 
import threading
import collections
import json

with open("config.yaml", "r") as ymlfile:
    cfg = yaml.load(ymlfile)

for section in cfg:
    print(section)
print(cfg["mqtt"])
print(cfg["audio"])

data_topic = cfg['mqtt']['name']+'/'+cfg['mqtt']['data_topic']
availability_topic = cfg['mqtt']['name']+'/available'

sd.default.device = cfg["audio"]["input_device"]
duration = 60 #in seconds

# homeassistant/sensor/0x00158d00054d4675/battery/config
#  {"availability":[{"topic":"zigbee2mqtt/bridge/state"}],
#   "device":{
#       "identifiers":["zigbee2mqtt_0x00158d00054d4675"],
#       "manufacturer":"Xiaomi",
#       "model":"Aqara human body movement and illuminance sensor (RTCGQ11LM)",
#       "name":"studio_door_motion",
#       "sw_version":"Zigbee2MQTT 1.16.2"
#       },
#       "device_class":"battery",
#       "json_attributes_topic":"zigbee2mqtt/studio_door_motion",
#       "name":"studio_door_motion_battery",
#       "state_topic":"zigbee2mqtt/studio_door_motion",
#       "unique_id":"0x00158d00054d4675_battery_zigbee2mqtt",
#       "unit_of_measurement":"%",
#       "value_template":"{{ value_json.battery }}"
# }
# homeassistant/sensor/0x00158d00054d4675/illuminance/config
#  {"availability":[{"topic":"zigbee2mqtt/bridge/state"}],
#   "device":{
#       "identifiers":["zigbee2mqtt_0x00158d00054d4675"],
#       "manufacturer":"Xiaomi",
#       "model":"Aqara human body movement and illuminance sensor (RTCGQ11LM)",
#       "name":"studio_door_motion",
#       "sw_version":"Zigbee2MQTT 1.16.2"
#       },
#   "device_class":"illuminance",
#   "json_attributes_topic":"zigbee2mqtt/studio_door_motion",
#   "name":"studio_door_motion_illuminance",
#   "state_topic":"zigbee2mqtt/studio_door_motion",
#   "unique_id":"0x00158d00054d4675_illuminance_zigbee2mqtt",
#   "unit_of_measurement":"lx",
#   "value_template":"{{ value_json.illuminance }}"}
# homeassistant/sensor/0x00158d00054d4675/linkquality/config
#  {"availability":[{"topic":"zigbee2mqtt/bridge/state"}],
#   "device":{
#       "identifiers":["zigbee2mqtt_0x00158d00054d4675"],
#       "manufacturer":"Xiaomi",
#       "model":"Aqara human body movement and illuminance sensor (RTCGQ11LM)",
#       "name":"studio_door_motion",
#       "sw_version":"Zigbee2MQTT 1.16.2"
#   },
#   "icon":"mdi:signal",
#   "json_attributes_topic":"zigbee2mqtt/studio_door_motion",
#   "name":"studio_door_motion_linkquality",
#   "state_topic":"zigbee2mqtt/studio_door_motion",
#   "unique_id":"0x00158d00054d4675_linkquality_zigbee2mqtt",
#   "unit_of_measurement":"lqi",
#   "value_template":"{{ value_json.linkquality }}"}

device_data = {
    "identifiers":["raspmic"],
    "manufacturer":"Andrea",
    "model":"RaspMic - Andrea",
    "name":"raspmic_studio",
    "sw_version":"0.1"
    
}

connected = False
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("test")
    global connected
    connected = True
    if (cfg['mqtt']['autodiscovery']):
        pload = {"availability":[{"topic":availability_topic}],
            "device": device_data,
            "icon":"mdi:signal",
            "json_attributes_topic":data_topic,
            "name":"raspmic_studio_audio_signal",
            "state_topic": data_topic,
            "unique_id":"raspmic_studio_signal",
            "unit_of_measurement":"db",
            "value_template":"{{ value_json.signal}}"
        }

        client.publish(cfg['mqtt']['discovery_topic']+'/sensor/'+cfg['mqtt']['name']+'/audio_signal/config', payload=json.dumps(pload))
        pload_counter = {"availability":[{"topic":availability_topic}],
            "device":device_data,
            "json_attributes_topic":data_topic,
            "name":"raspmic_studio_counter",
            "state_topic": data_topic,
            "unique_id":"raspmic_studio_counter",
            "unit_of_measurement":"unit",
            "value_template":"{{ value_json.counter}}"
        }

        client.publish(cfg['mqtt']['discovery_topic']+'/sensor/'+cfg['mqtt']['name']+'/counter/config', payload=json.dumps(pload_counter))
        
        client.publish(availability_topic, payload="online", retain=True)
        print("Publish autodiscovery")

def on_disconnect(client, userdata, flags, rc):
    global connected 
    connected= False

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


client = mqtt.Client(client_id="",clean_session=True,userdata=None,protocol=mqtt.MQTTv311,transport="tcp")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.will_set(availability_topic, payload="offline")

client.username_pw_set(username=cfg['mqtt']['username'],password=cfg['mqtt']['password'])
print("Connecting...")
client.connect(cfg['mqtt']['host'], 1883, 10)
client.loop_start()

data_collection = collections.deque(1000 * [0], 1000)



counter = 0
def publish_data():
    threading.Timer(5.0, publish_data).start()
    median = int(sum(data_collection)/len(data_collection))
    global counter
    pload = {
        'signal': median,
        'counter': counter,
    }
    if (connected):
        client.publish(data_topic, payload=json.dumps(pload))
        client.publish(availability_topic, payload="online", retain=True)
        counter += 1
        print("Publish data")

def audio_callback(indata, frames, time, status):
   volume_norm = np.linalg.norm(indata) * 10
   data_collection.appendleft(volume_norm)
   #print("|" * int(volume_norm))
   

publish_data()
while True:
   stream = sd.InputStream(callback=audio_callback)
   with stream:
      sd.sleep(duration * 1000)

client.loop_stop()
