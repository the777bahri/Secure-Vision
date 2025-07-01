import csv
from pathlib import Path
import datetime

def login(username, password):
    users = {"admin": "1234", "user": "pass"}
    return users.get(username) == password

def save_detection(person_name, timestamp, camera_name):
    Path("logs").mkdir(exist_ok = True)
    with open("logs/detections.csv", "a", newline = "") as f:
        writer = csv.writer(f)
        writer.writerow([person_name, timestamp, camera_name])

def save_registration(name, num_poses):
    Path("logs").mkdir(exist_ok = True)
    with open("logs/registrations.csv", "a", newline = "") as f:
        writer = csv.writer(f)
        writer.writerow([name, num_poses, datetime.datetime.now().timestamp()])
