#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import subprocess
import os
import time
import sys
from pathlib import Path
import glob

# ==================== 基础配置 ====================
# 日志目录
LOG_DIR = Path("./logs")
# 要执行的脚本列表
SCRIPTS = [
    "run_pipeline.py",
    "run_syncnet.py",
    "run_visualise.py"
]
# 支持的视频格式（可自行扩展）
SUPPORTED_VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']

# ==================== 工具函数 ====================
def get_timestamp():
    """生成时间戳（YYYYMMDD_HHMMSS）"""
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())

def init_log_dir():
    """初始化日志目录"""
    LOG_DIR.mkdir(exist_ok=True, parents=True)

def get_video_files(input_dir, recursive=True):
    """递归/非递归获取目录下所有支持的视频文件"""
    video_files = []
    input_path = Path(input_dir).resolve()
    
    if not input_path.exists():
        print(f"❌ 输入目录不存在: {input_dir}")
        return video_files
    
    # 遍历所有支持的视频格式
    for ext in SUPPORTED_VIDEO_EXT:
        glob_pattern = f"**/*{ext}" if recursive else f"*{ext}"
        files = glob.glob(str(input_path / glob_pattern), recursive=recursive)
        video_files.extend(files)
    
    # 去重并排序
    video_files = sorted(list(set(video_files)))
    return video_files

def run_command(cmd, log_file):
    """执行命令并记录日志"""
    # 记录命令执行信息
    log_content = f"\n{'='*50}\n执行命令: {' '.join(cmd)}\n开始时间: {time.ctime()}\n{'='*50}\n"
    log_file.write(log_content)
    log_file.flush()

    # 执行命令并捕获输出
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8"
    )

    # 实时输出日志
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            log_file.write(line)
            log_file.flush()
            # 同时输出到控制台
            sys.stdout.write(line)
            sys.stdout.flush()

    # 记录执行结果
    return_code = process.returncode
    result = "成功" if return_code == 0 else "失败"
    end_log = f"\n{'='*50}\n命令执行{result}，返回码: {return_code}\n结束时间: {time.ctime()}\n{'='*50}\n"
    log_file.write(end_log)
    log_file.flush()

    return return_code

# ==================== 参数解析 ====================
def parse_args():
    parser = argparse.ArgumentParser(description="SyncNet 批量全管线自动化脚本",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # ---------------- 批量处理核心参数 ----------------
    parser.add_argument("--input_dir", type=str, required=True,
                        help="视频文件目录（批量处理必填，会递归查找所有视频）")
    parser.add_argument("--no-recursive", action="store_true",
                        help="是否禁用递归查找（仅处理input_dir下一级目录）")
    
    # ---------------- 共用核心参数 ----------------
    parser.add_argument("--data_dir", type=str, default="data/work",
                        help="输出数据根目录（每个视频会在该目录下按文件名创建子目录）")
    
    # ---------------- run_pipeline.py 特有参数 ----------------
    parser.add_argument("--facedet_scale", type=float, default=0.25,
                        help="[pipeline] 人脸检测缩放因子")
    parser.add_argument("--crop_scale", type=float, default=0.40,
                        help="[pipeline] 裁剪框缩放因子")
    parser.add_argument("--min_track", type=int, default=100,
                        help="[pipeline] 最小人脸跟踪时长")
    parser.add_argument("--num_failed_det", type=int, default=25,
                        help="[pipeline] 允许的最大检测失败次数")
    parser.add_argument("--min_face_size", type=int, default=100,
                        help="[pipeline] 最小人脸尺寸（像素）")
    
    # ---------------- run_syncnet.py 特有参数 ----------------
    parser.add_argument("--initial_model", type=str, default="data/syncnet_v2.model",
                        help="[syncnet] 初始模型路径")
    parser.add_argument("--batch_size", type=int, default=20,
                        help="[syncnet] 批处理大小")
    parser.add_argument("--vshift", type=int, default=15,
                        help="[syncnet] 视频偏移量")
    
    # ---------------- run_visualise.py 特有参数 ----------------
    parser.add_argument("--frame_rate", type=int, default=25,
                        help="[visualise/pipeline] 帧率")
    
    # ---------------- 脚本控制参数 ----------------
    parser.add_argument("--skip-failed", action="store_true",
                        help="某个脚本执行失败时，是否跳过该视频的后续脚本")
    parser.add_argument("--skip-video-failed", action="store_true",
                        help="某个视频处理失败时，是否跳过下一个视频")

    return parser.parse_args()

# ==================== 主执行逻辑 ====================
def main():
    # 1. 解析参数
    args = parse_args()
    
    # 2. 初始化日志目录
    init_log_dir()
    
    # 3. 生成批量日志文件名（带时间戳）
    timestamp = get_timestamp()
    batch_log_file_path = LOG_DIR / f"syncnet_batch_automation_{timestamp}.log"
    
    # 4. 获取所有视频文件
    video_files = get_video_files(args.input_dir, not args.no_recursive)
    if not video_files:
        print(f"❌ 在目录 {args.input_dir} 下未找到支持的视频文件（支持格式：{SUPPORTED_VIDEO_EXT}）")
        sys.exit(1)
    print(f"✅ 共找到 {len(video_files)} 个视频文件，开始批量处理...")
    
    # 5. 打开批量日志文件
    with open(batch_log_file_path, "a", encoding="utf-8") as batch_log_file:
        # 写入批量执行头部信息
        batch_log_file.write(f"===== SyncNet 批量自动化管线执行日志 =====\n")
        batch_log_file.write(f"执行时间: {time.ctime()}\n")
        batch_log_file.write(f"输入目录: {args.input_dir}\n")
        batch_log_file.write(f"递归查找: {not args.no_recursive}\n")
        batch_log_file.write(f"输出根目录: {args.data_dir}\n")
        batch_log_file.write(f"视频文件数量: {len(video_files)}\n")
        batch_log_file.write(f"日志文件: {batch_log_file_path}\n")
        batch_log_file.write(f"==========================================\n\n")
        batch_log_file.flush()

        # 6. 遍历处理每个视频
        total_success = 0
        total_failed = 0
        failed_videos = []
        
        for idx, videofile in enumerate(video_files, 1):
            # 生成reference（视频文件名，不含路径和后缀）
            video_path = Path(videofile)
            reference = video_path.stem  # 核心：用文件名作为reference
            # 替换特殊字符（避免目录创建失败）
            reference = reference.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            
            batch_log_file.write(f"\n\n{'='*60}\n开始处理第 {idx}/{len(video_files)} 个视频:\n文件路径: {videofile}\nReference: {reference}\n{'='*60}\n")
            batch_log_file.flush()
            print(f"\n\n📌 开始处理第 {idx}/{len(video_files)} 个视频: {videofile} (reference: {reference})")

            # 标记当前视频是否处理成功
            video_success = True

            # 构造每个脚本的执行命令
            # 6.1 run_pipeline.py 命令
            pipeline_cmd = [
                sys.executable, "run_pipeline.py",
                "--videofile", videofile,
                "--reference", reference,
                "--data_dir", args.data_dir,
                "--facedet_scale", str(args.facedet_scale),
                "--crop_scale", str(args.crop_scale),
                "--min_track", str(args.min_track),
                "--frame_rate", str(args.frame_rate),
                "--num_failed_det", str(args.num_failed_det),
                "--min_face_size", str(args.min_face_size)
            ]

            # 6.2 run_syncnet.py 命令
            syncnet_cmd = [
                sys.executable, "run_syncnet.py",
                "--videofile", videofile,
                "--reference", reference,
                "--data_dir", args.data_dir,
                "--initial_model", args.initial_model,
                "--batch_size", str(args.batch_size),
                "--vshift", str(args.vshift)
            ]

            # 6.3 run_visualise.py 命令
            visualise_cmd = [
                sys.executable, "run_visualise.py",
                "--videofile", videofile,
                "--reference", reference,
                "--data_dir", args.data_dir,
                "--frame_rate", str(args.frame_rate)
            ]

            # 按顺序执行脚本
            scripts_cmds = [
                ("run_pipeline.py", pipeline_cmd),
                ("run_syncnet.py", syncnet_cmd),
                ("run_visualise.py", visualise_cmd)
            ]

            for script_name, cmd in scripts_cmds:
                batch_log_file.write(f"\n\n========== 开始执行 {script_name} ==========\n")
                batch_log_file.flush()
                
                # 执行命令
                return_code = run_command(cmd, batch_log_file)
                
                # 检查执行结果
                if return_code != 0:
                    video_success = False
                    batch_log_file.write(f"\n❌ {script_name} 执行失败 (视频: {videofile})\n")
                    batch_log_file.flush()
                    print(f"\n❌ {script_name} 执行失败 (视频: {videofile})")
                    
                    # 若开启skip-failed，跳过该视频后续脚本
                    if args.skip_failed:
                        batch_log_file.write(f"\n⚠️  已开启--skip-failed，跳过该视频后续脚本\n")
                        batch_log_file.flush()
                        print(f"\n⚠️  已开启--skip-failed，跳过该视频后续脚本")
                        break

            # 统计结果
            if video_success:
                total_success += 1
                batch_log_file.write(f"\n✅ 视频 {videofile} 处理完成\n")
                print(f"\n✅ 视频 {videofile} 处理完成")
            else:
                total_failed += 1
                failed_videos.append(videofile)
                batch_log_file.write(f"\n❌ 视频 {videofile} 处理失败\n")
                print(f"\n❌ 视频 {videofile} 处理失败")
                
                # 若开启skip-video-failed，跳过下一个视频
                if args.skip_video_failed:
                    batch_log_file.write(f"\n⚠️  已开启--skip-video-failed，终止批量处理\n")
                    batch_log_file.flush()
                    print(f"\n⚠️  已开启--skip-video-failed，终止批量处理")
                    break

        # 7. 批量处理完成，写入汇总信息
        batch_log_file.write(f"\n\n===== 批量处理汇总 =====\n")
        batch_log_file.write(f"总视频数: {len(video_files)}\n")
        batch_log_file.write(f"成功数: {total_success}\n")
        batch_log_file.write(f"失败数: {total_failed}\n")
        if failed_videos:
            batch_log_file.write(f"失败视频列表: {failed_videos}\n")
        batch_log_file.write(f"完成时间: {time.ctime()}\n")
        batch_log_file.write(f"批量日志文件: {batch_log_file_path}\n")
        batch_log_file.write(f"========================\n")
        batch_log_file.flush()

        # 控制台输出汇总
        print(f"\n\n===== 批量处理汇总 =====")
        print(f"总视频数: {len(video_files)}")
        print(f"成功数: {total_success}")
        print(f"失败数: {total_failed}")
        if failed_videos:
            print(f"失败视频列表: {failed_videos}")
        print(f"批量日志文件: {batch_log_file_path}")
        print(f"========================")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 批量脚本执行出错: {str(e)}")
        # 错误信息写入日志
        timestamp = get_timestamp()
        init_log_dir()
        error_log_path = LOG_DIR / f"syncnet_batch_automation_error_{timestamp}.log"
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(f"执行出错时间: {time.ctime()}\n")
            f.write(f"错误信息: {str(e)}\n")
        sys.exit(1)
