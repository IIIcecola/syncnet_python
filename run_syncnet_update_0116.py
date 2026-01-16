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
offsets_list = []  # 存储每个裁剪视频的偏移值
confidences_list = []  # 存储每个裁剪视频的置信度
avg_min_dist_list = []  # 新增：存储每个裁剪视频的「最优偏移平均同步差」

for idx, fname in enumerate(flist):
    print(f"\nProcessing crop video {idx}: {fname}")
    offset, conf, dist = s.evaluate(opt,videofile=fname)
    dists.append(dist)
    offsets_list.append(offset)
    confidences_list.append(conf)
    
    # 新增：计算当前track的「最优偏移平均同步差（最小距离）」
    # dist.shape = [帧数, 2*vshift+1] → 按帧取最小距离 → 求均值
    min_vals_per_frame = np.min(dist, axis=1)  # 每帧的最小距离（最优偏移对应的距离）
    avg_min_dist = np.mean(min_vals_per_frame) # 所有帧的最小距离均值（平均同步差）
    avg_min_dist_list.append(avg_min_dist)
    print(f"Track {idx} - 最优偏移平均同步差（最小距离）: {avg_min_dist:.4f}")

# ==================== SAVE ACTIVESD.PCKL ====================

with open(os.path.join(opt.work_dir,opt.reference,'activesd.pckl'), 'wb') as fil:
    pickle.dump(dists, fil)
print(f"\nSaved raw distance matrix to: {os.path.join(opt.work_dir,opt.reference,'activesd.pckl')}")

# ==================== 生成 offsets.txt（含平均同步差） ====================
def generate_offsets_txt(opt, offsets, confidences, avg_min_dists):
    """生成包含偏移、置信度、平均同步差的offsets.txt"""
    txt_path = os.path.join(opt.work_dir, opt.reference, 'offsets.txt')
    frame_rate = 25  # 固定帧率（与run_pipeline.py一致）
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        # 新增表头：avg_min_dist（最优偏移平均同步差）
        f.write("track_id\toffset_frames\toffset_seconds\tconfidence\tavg_min_dist\n")
        # 写入每个track的结果
        for track_id, (offset, conf, avg_min) in enumerate(zip(offsets, confidences, avg_min_dists)):
            offset_sec = offset / frame_rate  # 偏移转换为秒
            f.write(f"{track_id}\t{offset}\t{offset_sec:.4f}\t{conf:.4f}\t{avg_min:.4f}\n")
    
    print(f"Saved offset results to: {txt_path}")
    print("\n=== Final Offset Summary ===")
    for track_id, (offset, conf, avg_min) in enumerate(zip(offsets, confidences, avg_min_dists)):
        print(f"Track {track_id}: "
              f"Offset = {offset} frames ({offset/25:.4f} sec), "
              f"Confidence = {conf:.4f}, "
              f"Avg Min Dist (平均同步差) = {avg_min:.4f}")

# 调用生成函数（传入新增的avg_min_dist_list）
generate_offsets_txt(opt, offsets_list, confidences_list, avg_min_dist_list)
