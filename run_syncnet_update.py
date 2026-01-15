#!/usr/bin/python
#-*- coding: utf-8 -*-

import time, pdb, argparse, subprocess, pickle, os, gzip, glob
import numpy as np  # 新增：导入numpy

from SyncNetInstance import *

# ==================== PARSE ARGUMENT ====================

parser = argparse.ArgumentParser(description = "SyncNet");
parser.add_argument('--initial_model', type=str, default="data/syncnet_v2.model", help='');
parser.add_argument('--batch_size', type=int, default='20', help='');
parser.add_argument('--vshift', type=int, default='15', help='');
parser.add_argument('--data_dir', type=str, default='data/work', help='');
parser.add_argument('--videofile', type=str, default='', help='');
parser.add_argument('--reference', type=str, default='', help='');
opt = parser.parse_args();

setattr(opt,'avi_dir',os.path.join(opt.data_dir,'pyavi'))
setattr(opt,'tmp_dir',os.path.join(opt.data_dir,'pytmp'))
setattr(opt,'work_dir',os.path.join(opt.data_dir,'pywork'))
setattr(opt,'crop_dir',os.path.join(opt.data_dir,'pycrop'))


# ==================== LOAD MODEL AND FILE LIST ====================

s = SyncNetInstance();

s.loadParameters(opt.initial_model);
print("Model %s loaded."%opt.initial_model);

flist = glob.glob(os.path.join(opt.crop_dir,opt.reference,'0*.avi'))
flist.sort()

# ==================== GET OFFSETS ====================

dists = []
offsets_list = []  # 新增：存储每个裁剪视频的偏移值
confidences_list = []  # 新增：存储每个裁剪视频的置信度

for idx, fname in enumerate(flist):
    print(f"\nProcessing crop video {idx}: {fname}")
    offset, conf, dist = s.evaluate(opt,videofile=fname)
    dists.append(dist)
    offsets_list.append(offset)  # 保存偏移值
    confidences_list.append(conf)  # 保存置信度

# ==================== SAVE ACTIVESD.PCKL ====================

with open(os.path.join(opt.work_dir,opt.reference,'activesd.pckl'), 'wb') as fil:
    pickle.dump(dists, fil)
print(f"\nSaved raw distance matrix to: {os.path.join(opt.work_dir,opt.reference,'activesd.pckl')}")

# ==================== 新增：解析并生成 offsets.txt ====================
def generate_offsets_txt(opt, offsets, confidences):
    """从activesd.pckl的原始数据/直接结果生成offsets.txt"""
    txt_path = os.path.join(opt.work_dir, opt.reference, 'offsets.txt')
    frame_rate = 25  # 固定帧率（与run_pipeline.py一致）
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write("track_id\toffset_frames\toffset_seconds\tconfidence\n")
        # 写入每个裁剪视频的结果
        for track_id, (offset, conf) in enumerate(zip(offsets, confidences)):
            offset_sec = offset / frame_rate  # 转换为秒
            f.write(f"{track_id}\t{offset}\t{offset_sec:.4f}\t{conf:.4f}\n")
    
    print(f"Saved offset results to: {txt_path}")
    print("\n=== Final Offset Summary ===")
    for track_id, (offset, conf) in enumerate(zip(offsets, confidences)):
        print(f"Track {track_id}: Offset = {offset} frames ({offset/25:.4f} sec), Confidence = {conf:.4f}")

# 调用生成函数
generate_offsets_txt(opt, offsets_list, confidences_list)
