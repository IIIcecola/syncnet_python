#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import argparse
import numpy as np
from pathlib import Path
from collections import Counter

def parse_offsets_txt(txt_path):
    """
    读取单个offsets.txt文件，返回：
    - 有效数据行数量（不含表头）
    - 按confidence降序排序后的列数据 (sorted_offset_frames, sorted_offset_seconds, sorted_confidence)
    """
    offset_frames = []
    offset_seconds = []
    confidence = []
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            # 跳过表头
            header = f.readline().strip()
            if not header.startswith("track_id"):
                print(f"⚠️  {txt_path} 表头格式异常，跳过")
                return (0, None)
            
            # 读取数据行
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 按制表符/空格分割（兼容不同分隔符）
                parts = line.split()
                if len(parts) < 4:
                    print(f"⚠️  {txt_path} 行数据异常：{line}，跳过")
                    continue
                # 提取数值（忽略track_id）
                try:
                    of = int(parts[1])
                    os_val = float(parts[2])
                    conf = float(parts[3])
                    offset_frames.append(of)
                    offset_seconds.append(os_val)
                    confidence.append(conf)
                except ValueError:
                    print(f"⚠️  {txt_path} 数值转换失败：{line}，跳过")
                    continue
        
        # 统计有效数据行数量
        data_line_count = len(confidence)
        if data_line_count == 0:
            print(f"⚠️  {txt_path} 无有效数据行，跳过")
            return (0, None)
        
        # 按confidence降序排序（所有列同步排序）
        sorted_indices = np.argsort(confidence)[::-1]
        sorted_of = [offset_frames[i] for i in sorted_indices]
        sorted_os = [offset_seconds[i] for i in sorted_indices]
        sorted_conf = [confidence[i] for i in sorted_indices]
        
        return (data_line_count, (sorted_of, sorted_os, sorted_conf))
    
    except Exception as e:
        print(f"❌ 读取 {txt_path} 失败：{str(e)}")
        return (0, None)

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="汇总SyncNet批量处理结果的均值（按数据行数量分组计算）")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="SyncNet的输出根目录（如/path/to/output/）")
    args = parser.parse_args()
    
    # 校验输出目录
    output_root = Path(args.output_dir).resolve()
    pywork_dir = output_root / "pywork"
    if not pywork_dir.exists():
        print(f"❌ 未找到pywork目录：{pywork_dir}")
        return
    
    # 第一步：遍历所有视频子目录，收集数据行数量和排序后的数据
    all_data = {}  # key: 视频名称, value: (data_line_count, sorted_data)
    video_names = []  # 记录所有找到的视频名称
    
    for video_subdir in pywork_dir.iterdir():
        if not video_subdir.is_dir():
            continue
        offsets_txt = video_subdir / "offsets.txt"
        if not offsets_txt.exists():
            print(f"⚠️  {video_subdir.name} 目录下无offsets.txt，跳过")
            continue
        
        # 读取该视频的offsets.txt
        data_line_count, sorted_data = parse_offsets_txt(str(offsets_txt))
        if data_line_count == 0 or sorted_data is None:
            continue
        
        all_data[video_subdir.name] = (data_line_count, sorted_data)
        video_names.append(video_subdir.name)
    
    if not all_data:
        print(f"❌ 未找到任何有效offsets.txt文件")
        return
    
    # 第二步：按数据行数量分组
    grouped_data = {}  # key: 数据行数量, value: {"videos": [视频名列表], "data": [排序后数据列表]}
    for video_name, (line_count, sorted_data) in all_data.items():
        if line_count not in grouped_data:
            grouped_data[line_count] = {"videos": [], "data": []}
        grouped_data[line_count]["videos"].append(video_name)
        grouped_data[line_count]["data"].append(sorted_data)
    
    # 打印分组统计
    print(f"\n===== 数据行数量分组统计 =====")
    for line_count in sorted(grouped_data.keys()):
        video_list = grouped_data[line_count]["videos"]
        print(f"数据行数量 {line_count}：共 {len(video_list)} 个文件 → {', '.join(video_list)}")
    
    # 第三步：逐组计算均值
    output_txt = output_root / "syncnet_summary_mean_by_linecount.txt"
    with open(output_txt, 'w', encoding='utf-8') as f:
        # 写入总统计信息
        f.write("===== SyncNet批量结果均值汇总（按数据行数量分组）=====\n")
        f.write(f"汇总时间：{os.popen('date').read().strip()}\n")
        f.write(f"输出根目录：{output_root}\n\n")
        
        # 逐组写入结果
        for line_count in sorted(grouped_data.keys()):
            group_info = grouped_data[line_count]
            video_list = group_info["videos"]
            data_list = group_info["data"]
            group_size = len(video_list)
            
            # 写入分组表头
            f.write(f"{'='*60}\n")
            f.write(f"分组：数据行数量 = {line_count} 行\n")
            f.write(f"参与计算的视频数：{group_size}\n")
            f.write(f"参与计算的视频名称：{', '.join(video_list)}\n")
            f.write(f"{'='*60}\n")
            
            # 写入该组均值表头
            f.write("排序索引\t均值_offset_frames\t均值_offset_seconds\t均值_confidence\t参与计算的视频数\n")
            
            # 计算该组均值（数据行数量一致，直接按索引遍历）
            for idx in range(line_count):
                # 收集该索引下所有文件的数值
                of_vals = [d[0][idx] for d in data_list]
                os_vals = [d[1][idx] for d in data_list]
                conf_vals = [d[2][idx] for d in data_list]
                
                # 计算均值
                mean_of = np.mean(of_vals)
                mean_os = np.mean(os_vals)
                mean_conf = np.mean(conf_vals)
                
                # 写入该行均值
                f.write(f"{idx+1}\t{mean_of:.4f}\t{mean_os:.4f}\t{mean_conf:.4f}\t{group_size}\n")
            
            f.write("\n")  # 组间空行分隔
    
    # 控制台输出完成信息
    print(f"\n✅ 汇总完成！结果已保存到：{output_txt}")
    print(f"\n===== 最终汇总结果预览 =====")
    with open(output_txt, 'r', encoding='utf-8') as f:
        preview = f.read().splitlines()[:20]  # 预览前20行
        print("\n".join(preview))
        if len(f.read().splitlines()) > 20:
            print("...（更多内容请查看完整文件）")

if __name__ == "__main__":
    main()
