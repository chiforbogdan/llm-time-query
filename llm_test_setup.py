import random
import json
import shutil
import os
from faker import Faker

ANDROID_DIR='data/android'
ANDROID_LOG_TYPES=['D', 'E', 'I', 'W']
ANDROID_NUM_FAKE_EVENTS=0

def generate_android_fake_event(date):
    val = date
    val += " " + str(random.randint(1, 1000000)) + " " + str(random.randint(1, 1000000))
    val += " " + ANDROID_LOG_TYPES[random.randint(0, len(ANDROID_LOG_TYPES)-1)]
    val += " " + Faker().sentence()
    val += "\n"
    return val

def generate_android_fake_events(date, num_events):
    val=""
    for i in range(num_events):
        val += generate_android_fake_event(date)
    return val

def get_android_event_as_string(event):
    val = event['date']
    val += " " + str(random.randint(1, 1000000)) + " " + str(random.randint(1, 1000000))
    val += " " + event['log_level']
    val += " " + event['text']
    val += "\n"

    return val

def generate_android_setup(users):
    shutil.rmtree(ANDROID_DIR)
    os.makedirs(ANDROID_DIR, exist_ok=True)

    android_users = []
    for user in users:
        user_id=random.randint(1, 1000000)
        android_users.append({'name': user['name'], 'email': user['email'], 'user_id': user_id})

        logcat_file_index=0
        for event in user['events']:
            logcat_file_index=logcat_file_index+1
            logcat_filename=str(user_id) + "_" + str(logcat_file_index) + ".logcat"
            with open("data/android/" + logcat_filename, 'w') as file:
                file.write(generate_android_fake_events(event['date'], ANDROID_NUM_FAKE_EVENTS))
                file.write(get_android_event_as_string(event))
                file.write(generate_android_fake_events(event['date'], ANDROID_NUM_FAKE_EVENTS))

    with open('data/android/android_users.json', 'w') as file:
        json.dump(android_users, file)