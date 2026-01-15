#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import subprocess
import os
import time
import sys
from pathlib import Path

# ==================== 基础配置 ====================
# 日志目录
LOG_DIR = Path("./logs")
# 要执行的脚本列表
SCRIPTS = [
    "run_pipeline.py",
    "run_syncnet.py",
    "run_visualise.py"
]

# ==================== 工具函数 ====================
def get_timestamp():
    """生成时间戳（YYYYMMDD_HHMMSS）"""
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())

def init_log_dir():
    """初始化日志目录"""
    LOG_DIR.mkdir(exist_ok=True, parents=True)

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
    parser = argparse.ArgumentParser(description="SyncNet 全管线自动化脚本",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # ---------------- 共用核心参数 ----------------
    parser.add_argument("--videofile", type=str, required=True,
                        help="输入视频文件路径（必填）")
    parser.add_argument("--reference", type=str, required=True,
                        help="视频标识名称（必填）")
    parser.add_argument("--data_dir", type=str, default="data/work",
                        help="输出数据目录")
    
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
                        help="某个脚本执行失败时，是否跳过后续脚本")
    parser.add_argument("--log-level", type=str, default="all",
                        choices=["all", "error"],
                        help="日志级别：all(全部输出) / error(仅错误)")

    return parser.parse_args()

# ==================== 主执行逻辑 ====================
def main():
    # 1. 解析参数
    args = parse_args()
    
    # 2. 初始化日志目录
    init_log_dir()
    
    # 3. 生成日志文件名（带时间戳）
    timestamp = get_timestamp()
    log_file_path = LOG_DIR / f"syncnet_automation_{timestamp}.log"
    
    # 4. 打开日志文件
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        # 写入脚本执行头部信息
        log_file.write(f"===== SyncNet 自动化管线执行日志 =====\n")
        log_file.write(f"执行时间: {time.ctime()}\n")
        log_file.write(f"视频文件: {args.videofile}\n")
        log_file.write(f"参考名称: {args.reference}\n")
        log_file.write(f"数据目录: {args.data_dir}\n")
        log_file.write(f"日志文件: {log_file_path}\n")
        log_file.write(f"=======================================\n\n")
        log_file.flush()

        # 5. 构造每个脚本的执行命令
        # 5.1 run_pipeline.py 命令
        pipeline_cmd = [
            sys.executable, "run_pipeline.py",
            "--videofile", args.videofile,
            "--reference", args.reference,
            "--data_dir", args.data_dir,
            "--facedet_scale", str(args.facedet_scale),
            "--crop_scale", str(args.crop_scale),
            "--min_track", str(args.min_track),
            "--frame_rate", str(args.frame_rate),
            "--num_failed_det", str(args.num_failed_det),
            "--min_face_size", str(args.min_face_size)
        ]

        # 5.2 run_syncnet.py 命令
        syncnet_cmd = [
            sys.executable, "run_syncnet.py",
            "--videofile", args.videofile,
            "--reference", args.reference,
            "--data_dir", args.data_dir,
            "--initial_model", args.initial_model,
            "--batch_size", str(args.batch_size),
            "--vshift", str(args.vshift)
        ]

        # 5.3 run_visualise.py 命令
        visualise_cmd = [
            sys.executable, "run_visualise.py",
            "--videofile", args.videofile,
            "--reference", args.reference,
            "--data_dir", args.data_dir,
            "--frame_rate", str(args.frame_rate)
        ]

        # 6. 按顺序执行脚本
        scripts_cmds = [
            ("run_pipeline.py", pipeline_cmd),
            ("run_syncnet.py", syncnet_cmd),
            ("run_visualise.py", visualise_cmd)
        ]

        for script_name, cmd in scripts_cmds:
            log_file.write(f"\n\n========== 开始执行 {script_name} ==========\n")
            log_file.flush()
            
            # 执行命令
            return_code = run_command(cmd, log_file)
            
            # 检查执行结果，若失败且开启skip-failed则退出
            if return_code != 0 and args.skip_failed:
                log_file.write(f"\n{script_name} 执行失败，已开启--skip-failed，终止后续执行\n")
                print(f"\n❌ {script_name} 执行失败，日志文件: {log_file_path}")
                sys.exit(return_code)

        # 7. 执行完成
        log_file.write(f"\n\n===== 所有脚本执行完成 =====\n")
        log_file.write(f"完成时间: {time.ctime()}\n")
        log_file.write(f"日志文件: {log_file_path}\n")
        print(f"\n✅ 全管线执行完成！日志文件: {log_file_path}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 脚本执行出错: {str(e)}")
        # 错误信息写入日志
        timestamp = get_timestamp()
        init_log_dir()
        error_log_path = LOG_DIR / f"syncnet_automation_error_{timestamp}.log"
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(f"执行出错时间: {time.ctime()}\n")
            f.write(f"错误信息: {str(e)}\n")
        sys.exit(1)
