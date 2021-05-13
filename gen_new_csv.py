import pandas as pd
import os.path
from os import path

root = "/home/hdd2/ananya/Autism/ActivityNet/Crawler/Kinetics/"
data = pd.read_csv(root + "data/kinetics-600_train_super_req.csv")
req_labels = pd.read_excel("super_super_req_classes.ods")["Labels"].values
num = {}
for index, row in data.iterrows():
    label = row["label"]
    videoname = row["youtube_id"]
    start_time = row["time_start"]
    end_time = row["time_end"]
    videofile = videoname+'_'+str(start_time).zfill(6)+'_'+str(end_time).zfill(6)+".mp4"
    filename = os.path.join(root, 'dataset', label, videofile)
    videodata = skvideo.io.vread(filename)
    length, height, width, channel = videodata.shape
    if (not path.exists(filename)) or (label not in req_labels) or (length < 80):
        print("dropped" + str(index))
        data.drop(index, inplace=True)
    else : 
        if label in num:
            if(num[label] < 130):
                num[label] = num[label] + 1
            else:
                print("dropped" + str(index))
                data.drop(index, inplace=True)
        else :
            num[label] = 1
data.to_csv("./kinetics-600_train_super_super_req.csv")

# data = pd.read_excel("req_classes.ods")
# print('argui' in data["req_labels"].values)