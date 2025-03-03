"""Dataset utils for NN."""
import os
import random
from glob import glob
from pprint import pprint
import uuid
import tempfile
import cv2

import numpy as np
import ffmpeg
import skvideo.io
import pandas as pd
from skvideo.io import ffprobe
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image


class UCF101Dataset(Dataset):
    """UCF101 dataset for recognition. The class index start from 0.
    
    Args:
        root_dir (string): Directory with videos and splits.
        train (bool): train split or test split.
        clip_len (int): number of frames in clip, 16/32/64.
        transforms_ (object): composed transforms which takes in PIL image and output tensors.
        test_sample_num： number of clips sampled from a video. 1 for clip accuracy.
    """
    def __init__(self, root_dir, clip_len, split='1', train=True, transforms_=None, test_sample_num=10):
        self.root_dir = root_dir
        self.clip_len = clip_len
        self.split = split
        self.train = train
        self.transforms_ = transforms_
        self.test_sample_num = test_sample_num
        self.toPIL = transforms.ToPILImage()
        class_idx_path = os.path.join(root_dir, 'data', 'kinetics-600_train.csv')
        self.class_idx2label = pd.read_csv(class_idx_path, header=None, sep=' ').set_index(0)[1]
        self.class_label2idx = pd.read_csv(class_idx_path, header=None, sep=' ').set_index(1)[0]

        if self.train:
            train_split_path = os.path.join(root_dir, 'data', 'kinetics-600_train.csv')
            self.train_split = pd.read_csv(train_split_path, header=None, sep=' ')[0]
        else:
            test_split_path = os.path.join(root_dir, 'data', 'kinetics-600_test.csv')
            self.test_split = pd.read_csv(test_split_path, header=None)[0]
        print('Use split'+ self.split)

    def __len__(self):
        if self.train:
            return len(self.train_split)
        else:
            return len(self.test_split)

    def __getitem__(self, idx):
        """
        Returns:
            clip (tensor): [channel x time x height x width]
            class_idx (tensor): class index, [0-100]
        """
        if self.train:
            videoname = self.train_split[idx]
        else:
            videoname = self.test_split[idx]
        class_idx = self.class_label2idx[videoname[:videoname.find('/')]]
        filename = os.path.join(self.root_dir, 'video', videoname)
        videodata = skvideo.io.vread(filename)
        length, height, width, channel = videodata.shape
        
        # random select a clip for train
        if self.train:
            clip_start = random.randint(0, length - self.clip_len)
            clip = videodata[clip_start: clip_start + self.clip_len]

            if self.transforms_:
                trans_clip = []
                # fix seed, apply the sample `random transformation` for all frames in the clip 
                seed = random.random()
                for frame in clip:
                    random.seed(seed)
                    frame = self.toPIL(frame) # PIL image
                    frame = self.transforms_(frame) # tensor [C x H x W]
                    trans_clip.append(frame)
                # (T x C X H x W) to (C X T x H x W)
                clip = torch.stack(trans_clip).permute([1, 0, 2, 3])
            else:
                clip = torch.tensor(clip)

            return clip, torch.tensor(int(class_idx))
        # sample several clips for test
        else:
            all_clips = []
            all_idx = []
            for i in np.linspace(self.clip_len/2, length-self.clip_len/2, self.test_sample_num):
                clip_start = int(i - self.clip_len/2)
                clip = videodata[clip_start: clip_start + self.clip_len]
                if self.transforms_:
                    trans_clip = []
                    # fix seed, apply the sample `random transformation` for all frames in the clip 
                    seed = random.random()
                    for frame in clip:
                        random.seed(seed)
                        frame = self.toPIL(frame) # PIL image
                        frame = self.transforms_(frame) # tensor [C x H x W]
                        trans_clip.append(frame)
                    # (T x C X H x W) to (C X T x H x W)
                    clip = torch.stack(trans_clip).permute([1, 0, 2, 3])
                else:
                    clip = torch.tensor(clip)
                all_clips.append(clip)
                all_idx.append(torch.tensor(int(class_idx)))

            return torch.stack(all_clips), torch.tensor(int(class_idx))


class UCF101ClipRetrievalDataset(Dataset):
    """UCF101 dataset for Retrieval. Sample clips for each video. The class index start from 0.
    
    Args:
        root_dir (string): Directory with videos and splits.
        train (bool): train split or test split.
        clip_len (int): number of frames in clip, 16/32/64.
        sample_num(int): number of clips per video.
        transforms_ (object): composed transforms which takes in PIL image and output tensors.
    """
    def __init__(self, root_dir, clip_len, sample_num, train=True, transforms_=None):
        self.root_dir = root_dir
        self.clip_len = clip_len
        self.sample_num = sample_num
        self.train = train
        self.transforms_ = transforms_
        self.toPIL = transforms.ToPILImage()
        class_idx_path = os.path.join(root_dir, 'data', 'kinetics-600_train.csv')
        self.class_idx2label = pd.read_csv(class_idx_path, header=None, sep=' ').set_index(0)[1]
        self.class_label2idx = pd.read_csv(class_idx_path, header=None, sep=' ').set_index(1)[0]

        if self.train:
            train_split_path = os.path.join(root_dir, 'data', 'kinetics-600_train.csv')
            self.train_split = pd.read_csv(train_split_path, header=None, sep=' ')[0]
        else:
            test_split_path = os.path.join(root_dir, 'data', 'kinetics-600_test.csv')
            self.test_split = pd.read_csv(test_split_path, header=None)[0]

    def __len__(self):
        if self.train:
            return len(self.train_split)
        else:
            return len(self.test_split)

    def __getitem__(self, idx):
        """
        Returns:
            clip (tensor): [channel x time x height x width]
            class_idx (tensor): class index [0-100]
        """
        if self.train:
            videoname = self.train_split[idx]
        else:
            videoname = self.test_split[idx]
        class_idx = self.class_label2idx[videoname[:videoname.find('/')]]
        filename = os.path.join(self.root_dir, 'video', videoname)
        videodata = skvideo.io.vread(filename)
        length, height, width, channel = videodata.shape
        
        all_clips = []
        all_idx = []
        for i in np.linspace(self.clip_len/2, length-self.clip_len/2, self.sample_num):
            clip_start = int(i - self.clip_len/2)
            clip = videodata[clip_start: clip_start + self.clip_len]
            if self.transforms_:
                trans_clip = []
                # fix seed, apply the sample `random transformation` for all frames in the clip 
                seed = random.random()
                for frame in clip:
                    random.seed(seed)
                    frame = self.toPIL(frame) # PIL image
                    frame = self.transforms_(frame) # tensor [C x H x W]
                    frames.append(frame)
                    trans_clip.append(frame)
                # (T x C X H x W) to (C X T x H x W)
                clip = torch.stack(trans_clip).permute([1, 0, 2, 3])
            else:
                clip = torch.tensor(clip)
            all_clips.append(clip)
            all_idx.append(torch.tensor(int(class_idx)))

        return torch.stack(all_clips), torch.stack(all_idx)


class UCF101VCOPDataset(Dataset):
    """UCF101 dataset for video clip order prediction. Generate clips and permutes them on-the-fly.
    Need the corresponding configuration file exists. 
    
    Args:
        root_dir (string): Directory with videos and splits.
        train (bool): train split or test split.
        clip_len (int): number of frames in clip, 16/32/64.
        interval (int): number of frames between clips, 16/32.
        tuple_len (int): number of clips in each tuple, 3/4/5.
        transforms_ (object): composed transforms which takes in PIL image and output tensors.
    """
    def __init__(self, root_dir, clip_len, interval, tuple_len, train=True, transforms_=None):
        self.root_dir = root_dir
        self.clip_len = clip_len
        self.interval = interval
        self.tuple_len = tuple_len
        self.train = train
        self.transforms_ = transforms_
        self.toPIL = transforms.ToPILImage()
        self.tuple_total_frames = clip_len * tuple_len + interval * (tuple_len - 1)

        if self.train:
            vcop_train_split_name = 'vcop_train_{}_{}_{}.txt'.format(clip_len, interval, tuple_len)
            vcop_train_split_path = os.path.join(root_dir, 'data', 'kinetics-600_train_super_super_req.csv')
            self.train_split = pd.read_csv(vcop_train_split_path)
        else:
            vcop_test_split_name = 'vcop_test_{}_{}_{}.txt'.format(clip_len, interval, tuple_len)
            vcop_test_split_path = os.path.join(root_dir, 'data', 'kinetics-600_test.csv')
            self.test_split = pd.read_csv(vcop_test_split_path)

    def __len__(self):
        if self.train:
            return len(self.train_split)
        else:
            return len(self.test_split)

    def __getitem__(self, idx):
        """
        Returns:
            tuple_clip (tensor): [tuple_len x channel x time x height x width]
            tuple_order (tensor): [tuple_len]
        """
        if self.train:
            label = self.train_split["label"][idx]
            videoname = self.train_split["youtube_id"][idx]
            start_time = self.train_split["time_start"][idx]
            end_time = self.train_split["time_end"][idx]
        else:
            videoname = self.test_split["label"][idx]
            label = self.test_split["youtube_id"][idx]
            start_time = self.test_split["time_start"][idx]
            end_time = self.test_split["time_end"][idx]
        
        videofile = videoname+'_'+str(start_time).zfill(6)+'_'+str(end_time).zfill(6)+".mp4"
        filename = os.path.join(self.root_dir, 'dataset', label, videofile)
        try:
            videodata = skvideo.io.vread(filename)
        except:
            return [],[]
        length, height, width, channel = videodata.shape

        tuple_clip = []
        tuple_order = list(range(0, self.tuple_len))
        
        # random select tuple for train, deterministic random select for test
        if self.train:
            if(length < self.tuple_total_frames): return [],[]
            tuple_start = random.randint(0, length - self.tuple_total_frames)
        else:
            random.seed(idx)
            tuple_start = random.randint(0, length - self.tuple_total_frames)

        clip_start = tuple_start
        for _ in range(self.tuple_len):
            clip = videodata[clip_start: clip_start + self.clip_len]
            tuple_clip.append(clip)
            clip_start = clip_start + self.clip_len + self.interval

        clip_and_order = list(zip(tuple_clip, tuple_order))
        # random shuffle for train, the same shuffle for test
        if self.train:
            random.shuffle(clip_and_order)
        else:
            random.seed(idx)
            random.shuffle(clip_and_order)
        tuple_clip, tuple_order = zip(*clip_and_order)

        if self.transforms_:
            trans_tuple = []
            for clip in tuple_clip:
                trans_clip = []
                # fix seed, apply the sample `random transformation` for all frames in the clip 
                seed = random.random()
                for frame in clip:
                    random.seed(seed)
                    frame = self.toPIL(frame) # PIL image
                    frame = self.transforms_(frame) # tensor [C x H x W]
                    trans_clip.append(frame)
                # (T x C X H x W) to (C X T x H x W)
                trans_clip = torch.stack(trans_clip).permute([1, 0, 2, 3])
                trans_tuple.append(trans_clip)
            tuple_clip = trans_tuple
        else:
            tuple_clip = [torch.tensor(clip) for clip in tuple_clip]

        return torch.stack(tuple_clip), torch.tensor(tuple_order)


class UCF101FrameRetrievalDataset(Dataset):
    """UCF101 dataset for Retrieval. Sample frames for each video. The class index start from 0.
    
    Args:
        root_dir (string): Directory with videos and splits.
        train (bool): train split or test split.
        clip_len (int): number of frames in clip, 16/32/64.
        sample_num(int): number of clips per video.
        transforms_ (object): composed transforms which takes in PIL image and output tensors.
    """
    def __init__(self, root_dir, sample_num, train=True, transforms_=None):
        self.root_dir = root_dir
        self.sample_num = sample_num
        self.train = train
        self.transforms_ = transforms_
        self.toPIL = transforms.ToPILImage()
        class_idx_path = os.path.join(root_dir, 'split', 'classInd.txt')
        self.class_idx2label = pd.read_csv(class_idx_path, header=None, sep=' ').set_index(0)[1]
        self.class_label2idx = pd.read_csv(class_idx_path, header=None, sep=' ').set_index(1)[0]

        if self.train:
            train_split_path = os.path.join(root_dir, 'split', 'trainlist01.txt')
            self.train_split = pd.read_csv(train_split_path, header=None, sep=' ')[0]
        else:
            test_split_path = os.path.join(root_dir, 'split', 'testlist01.txt')
            self.test_split = pd.read_csv(test_split_path, header=None)[0]

    def __len__(self):
        if self.train:
            return len(self.train_split)
        else:
            return len(self.test_split)

    def __getitem__(self, idx):
        """
        Returns:
            clip (tensor): [channel x time x height x width]
            class_idx (tensor): class index [0-100]
        """
        if self.train:
            videoname = self.train_split[idx]
        else:
            videoname = self.test_split[idx]
        class_idx = self.class_label2idx[videoname[:videoname.find('/')]]
        filename = os.path.join(self.root_dir, 'video', videoname)
        videodata = skvideo.io.vread(filename)
        length, height, width, channel = videodata.shape
        
        all_frames = []
        all_idx = []
        for i in np.linspace(0, length-1, self.sample_num):
            frame = videodata[int(i)]
            if self.transforms_:
                frame = self.toPIL(frame) # PIL image
                frame = self.transforms_(frame) # tensor [C x H x W]
            else:
                frame = torch.tensor(frame) 
            all_frames.append(frame)
            all_idx.append(torch.tensor(int(class_idx)))

        return torch.stack(all_frames), torch.stack(all_idx)


class UCF101FOPDataset(Dataset):
    """UCF101 dataset for frame order prediction. Generate frames and permutes them on-the-fly. 
    May corrupt if there exists video which is not long enough.
    
    Args:
        root_dir (string): Directory with videos and splits.
        train (bool): train split or test split.
        interval (int): number of frames between selected frames.
        tuple_len (int): number of selected frames in each tuple, 3/4/5.
        transforms_ (object): composed transforms which takes in PIL image and output tensors.
    """
    def __init__(self, root_dir, interval, tuple_len, train=True, transforms_=None):
        self.root_dir = root_dir
        self.interval = interval
        self.tuple_len = tuple_len
        self.train = train
        self.transforms_ = transforms_
        self.toPIL = transforms.ToPILImage()
        self.tuple_total_frames = tuple_len + interval * (tuple_len - 1)

        if self.train:
            train_split_path = os.path.join(root_dir, 'split', 'trainlist01.txt')
            self.train_split = pd.read_csv(train_split_path, header=None, sep=' ')[0]
        else:
            test_split_path = os.path.join(root_dir, 'split', 'testlist01.txt')
            self.test_split = pd.read_csv(test_split_path, header=None)[0]

    def __len__(self):
        if self.train:
            return len(self.train_split)
        else:
            return len(self.test_split)

    def __getitem__(self, idx):
        """
        Returns:
            tuple_frame (tensor): [tuple_len x channel x height x width]
            tuple_order (tensor): [tuple_len]
        """
        if self.train:
            videoname = self.train_split[idx]
        else:
            videoname = self.test_split[idx]        
        filename = os.path.join(self.root_dir, 'video', videoname)
        videodata = skvideo.io.vread(filename)
        length, height, width, channel = videodata.shape

        tuple_frame = []
        tuple_order = list(range(0, self.tuple_len))
        
        # random select frame for train, deterministic random select for test
        if self.train:
            tuple_start = random.randint(0, length - self.tuple_total_frames)
        else:
            random.seed(idx)
            tuple_start = random.randint(0, length - self.tuple_total_frames)

        frame_idx = tuple_start
        for _ in range(self.tuple_len):
            tuple_frame.append(videodata[frame_idx])
            frame_idx = frame_idx + self.interval

        frame_and_order = list(zip(tuple_frame, tuple_order))
        # random shuffle for train, the same shuffle for test
        if self.train:
            random.shuffle(frame_and_order)
        else:
            random.seed(idx)
            random.shuffle(frame_and_order)
        tuple_frame, tuple_order = zip(*frame_and_order)

        if self.transforms_:
            trans_tuple = []
            for frame in tuple_frame:
                frame = self.toPIL(frame) # PIL image
                frame = self.transforms_(frame) # tensor [C x H x W]
                trans_tuple.append(frame)
            tuple_frame = trans_tuple
        else:
            tuple_frame = [torch.tensor(frame) for frame in tuple_frame]

        return torch.stack(tuple_frame), torch.tensor(tuple_order)


def export_tuple(tuple_clip, tuple_order, dir):
    """export tuple_clip and set its name with correct order.
    
    Args:
        tuple_clip (tensor): [tuple_len x channel x time x height x width]
        tuple_order (tensor): [tuple_len]
    """
    tuple_len, channel, time, height, width = tuple_clip.shape
    for i in range(tuple_len):
        filename = os.path.join(dir, 'c{}.mp4'.format(tuple_order[i]))
        skvideo.io.vwrite(filename, tuple_clip[i])


def gen_ucf101_vcop_splits(root_dir, clip_len, interval, tuple_len):
    """Generate split files for different configs."""
    vcop_train_split_name = 'vcop_train_{}_{}_{}.txt'.format(clip_len, interval, tuple_len)
    vcop_train_split_path = os.path.join(root_dir, 'split', vcop_train_split_name)
    vcop_test_split_name = 'vcop_test_{}_{}_{}.txt'.format(clip_len, interval, tuple_len)
    vcop_test_split_path = os.path.join(root_dir, 'split', vcop_test_split_name)
    # minimum length of video to extract one tuple
    min_video_len = clip_len * tuple_len + interval * (tuple_len - 1)

    def _video_longer_enough(filename):
        """Return true if video `filename` is longer than `min_video_len`"""
        path = os.path.join(root_dir, 'video', filename)
        metadata = ffprobe(path)['video']
        return eval(metadata['@nb_frames']) >= min_video_len

    train_split = pd.read_csv(os.path.join(root_dir, 'split', 'trainlist01.txt'), header=None, sep=' ')[0]
    train_split = train_split[train_split.apply(_video_longer_enough)]
    train_split.to_csv(vcop_train_split_path, index=None)

    test_split = pd.read_csv(os.path.join(root_dir, 'split', 'testlist01.txt'), header=None, sep=' ')[0]
    test_split = test_split[test_split.apply(_video_longer_enough)]
    test_split.to_csv(vcop_test_split_path, index=None)


def ucf101_stats():
    """UCF101 statistics"""
    collects = {'nb_frames': [], 'heights': [], 'widths': [], 
                'aspect_ratios': [], 'frame_rates': []}

    for filename in glob('../data/ucf101/video/*/*.avi'):
        metadata = ffprobe(filename)['video']
        collects['nb_frames'].append(eval(metadata['@nb_frames']))
        collects['heights'].append(eval(metadata['@height']))
        collects['widths'].append(eval(metadata['@width']))
        collects['aspect_ratios'].append(metadata['@display_aspect_ratio'])
        collects['frame_rates'].append(eval(metadata['@avg_frame_rate']))

    stats = {key: sorted(list(set(collects[key]))) for key in collects.keys()}
    stats['nb_frames'] = [stats['nb_frames'][0], stats['nb_frames'][-1]]

    pprint(stats)


if __name__ == '__main__':
    seed = 632
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # ucf101_stats()
    # gen_ucf101_vcop_splits('../data/ucf101', 16, 16, 2)
    # gen_ucf101_vcop_splits('../data/ucf101', 16, 32, 3)
    gen_ucf101_vcop_splits('../data/ucf101', 16, 8, 3)

    # train_transforms = transforms.Compose([
    #     transforms.Resize((128, 171)),
    #     transforms.RandomCrop(112),
    #     transforms.ToTensor()])
    # # train_dataset = UCF101FOPDataset('../data/ucf101', 8, 3, True, train_transforms)
    # # train_dataset = UCF101VCOPDataset('../data/ucf101', 16, 8, 3, True, train_transforms)
    # train_dataset = UCF101Dataset('../data/ucf101', 16, False, train_transforms)
    # # train_dataset = UCF101RetrievalDataset('../data/ucf101', 16, 10, True, train_transforms)    
    # train_dataloader = DataLoader(train_dataset, batch_size=8)

    # for i, data in enumerate(train_dataloader):
    #     clips, idxs = data
    #     # for i in range(10):
    #     #     filename = os.path.join('{}.mp4'.format(i))
    #     #     skvideo.io.vwrite(filename, clips[0][i])
    #     print(clips.shape)
    #     print(idxs)
    #     exit()
    # pass
