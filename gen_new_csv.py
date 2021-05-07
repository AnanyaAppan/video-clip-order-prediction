import pandas as pd
import os.path
from os import path

root = "/home/hdd2/ananya/Autism/ActivityNet/Crawler/Kinetics/"
data = pd.read_csv(root + "data/kinetics-600_train.csv")
# req_labels = pd.read_excel("req_classes.ods")["req_labels"].values
num = 0
for index, row in data.iterrows():
    label = row["label"]
    videoname = row["youtube_id"]
    start_time = row["time_start"]
    end_time = row["time_end"]
    videofile = videoname+'_'+str(start_time).zfill(6)+'_'+str(end_time).zfill(6)+".mp4"
    filename = os.path.join(root, 'dataset', label, videofile)
    if (not path.exists(filename)) or (label != 'climbing ladder'):
        print("dropped" + str(index))
        data.drop(index, inplace=True)
    else : num += 1
    if(num == 150): break
data = data[:150]
data.to_csv("./kinetics-600_train_150.csv")

# data = pd.read_excel("req_classes.ods")
# print('argui' in data["req_labels"].values)