#!/bin/bash
# SyncNet 批量处理脚本
# 用法: ./batch_syncnet.sh [--skip-failed] [--skip-video-failed]

# ==================== 配置 ====================
PYTHON_SCRIPT="./batch_syncnet.py"  # 您的Python批量脚本
DATA_ROOT="./data/work"             # 输出数据根目录
LOG_DIR="./batch_logs"              # 批量日志目录

# ==================== 参数解析 ====================
SKIP_FAILED=""
SKIP_VIDEO_FAILED=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --skip-failed) SKIP_FAILED="--skip-failed" ;;
        --skip-video-failed) SKIP_VIDEO_FAILED="--skip-video-failed" ;;
        *) echo "未知参数: $1" && exit 1 ;;
    esac
    shift
done

# ==================== 批量任务定义 ====================
# 定义要处理的目录列表
# 格式: "输入目录路径|输出子目录名"
# 输出目录会创建在 $DATA_ROOT/输出子目录名 下
tasks=(
    "/path/to/videos/dir1|output_dir1"
    "/path/to/videos/dir2|output_dir2"
    "/path/to/videos/dir3|output_dir3"
    "/path/to/videos/dir4|output_dir4"
    "/path/to/videos/dir5|output_dir5"
    "/path/to/videos/dir6|output_dir6"
    "/path/to/videos/dir7|output_dir7"
    "/path/to/videos/dir8|output_dir8"
    "/path/to/videos/dir9|output_dir9"
    "/path/to/videos/dir10|output_dir10"
    "/path/to/videos/dir11|output_dir11"
    "/path/to/videos/dir12|output_dir12"
)

# ==================== 初始化 ====================
echo "========================================"
echo "SyncNet 批量处理脚本"
echo "开始时间: $(date)"
echo "Python脚本: $PYTHON_SCRIPT"
echo "数据根目录: $DATA_ROOT"
echo "总任务数: ${#tasks[@]}"
echo "参数: $SKIP_FAILED $SKIP_VIDEO_FAILED"
echo "========================================"

# 创建日志目录
mkdir -p "$LOG_DIR"
timestamp=$(date +%Y%m%d_%H%M%S)
batch_log_file="$LOG_DIR/batch_$timestamp.log"

# 写入日志头
{
echo "===== SyncNet 批量处理执行日志 ====="
echo "执行时间: $(date)"
echo "Python脚本: $PYTHON_SCRIPT"
echo "数据根目录: $DATA_ROOT"
echo "总任务数: ${#tasks[@]}"
echo "参数: $SKIP_FAILED $SKIP_VIDEO_FAILED"
echo "==================================="
echo ""
} | tee -a "$batch_log_file"

# ==================== 处理每个任务 ====================
total_success=0
total_failed=0
failed_tasks=()

for i in "${!tasks[@]}"; do
    task="${tasks[$i]}"
    
    # 解析任务参数
    IFS='|' read -r input_dir output_subdir <<< "$task"
    
    # 构造输出目录
    output_dir="$DATA_ROOT/$output_subdir"
    
    echo ""
    echo "处理任务 $((i+1))/${#tasks[@]}:"
    echo "  输入目录: $input_dir"
    echo "  输出目录: $output_dir"
    echo "----------------------------------------"
    
    # 检查输入目录是否存在
    if [[ ! -d "$input_dir" ]]; then
        echo "  ❌ 输入目录不存在，跳过此任务"
        echo "  ❌ 输入目录不存在，跳过此任务" >> "$batch_log_file"
        total_failed=$((total_failed + 1))
        failed_tasks+=("$input_dir (目录不存在)")
        continue
    fi
    
    # 创建输出目录
    mkdir -p "$output_dir"
    
    # 构建Python命令
    PYTHON_CMD="python3 \"$PYTHON_SCRIPT\" \
        --input_dir \"$input_dir\" \
        --data_dir \"$output_dir\" \
        $SKIP_FAILED \
        $SKIP_VIDEO_FAILED"
    
    # 添加可选参数（如果需要）
    # PYTHON_CMD="$PYTHON_CMD --facedet_scale 0.25 --batch_size 20"
    
    # 记录开始时间
    task_start_time=$(date +%s)
    
    echo "  开始执行..."
    echo "  命令: $PYTHON_CMD"
    echo "  任务开始时间: $(date)"
    echo ""
    
    # 执行命令并记录到日志文件
    {
    echo "========================================"
    echo "任务 $((i+1))/${#tasks[@]} 开始"
    echo "输入目录: $input_dir"
    echo "输出目录: $output_dir"
    echo "开始时间: $(date)"
    echo "========================================"
    } >> "$batch_log_file"
    
    # 执行Python脚本
    eval $PYTHON_CMD 2>&1 | tee -a "$batch_log_file"
    exit_code=${PIPESTATUS[0]}
    
    # 记录结束时间
    task_end_time=$(date +%s)
    task_duration=$((task_end_time - task_start_time))
    
    # 统计结果
    if [[ $exit_code -eq 0 ]]; then
        echo "  ✅ 任务完成 (耗时: ${task_duration}秒)"
        {
        echo "========================================"
        echo "任务 $((i+1))/${#tasks[@]} 完成"
        echo "状态: 成功"
        echo "耗时: ${task_duration}秒"
        echo "结束时间: $(date)"
        echo "========================================"
        } >> "$batch_log_file"
        total_success=$((total_success + 1))
    else
        echo "  ❌ 任务失败 (耗时: ${task_duration}秒)"
        {
        echo "========================================"
        echo "任务 $((i+1))/${#tasks[@]} 失败"
        echo "状态: 失败"
        echo "耗时: ${task_duration}秒"
        echo "结束时间: $(date)"
        echo "========================================"
        } >> "$batch_log_file"
        total_failed=$((total_failed + 1))
        failed_tasks+=("$input_dir (退出码: $exit_code)")
        
        # 如果开启了skip-video-failed，则终止整个批处理
        if [[ -n "$SKIP_VIDEO_FAILED" ]]; then
            echo "  ⚠️ 已开启--skip-video-failed，终止批量处理"
            echo "  ⚠️ 已开启--skip-video-failed，终止批量处理" >> "$batch_log_file"
            break
        fi
    fi
    
    echo "----------------------------------------"
done

# ==================== 生成汇总报告 ====================
echo ""
echo "========================================"
echo "批量处理完成！"
echo "总任务数: ${#tasks[@]}"
echo "成功任务: $total_success"
echo "失败任务: $total_failed"
echo "批量日志: $batch_log_file"
echo "完成时间: $(date)"
echo "========================================"

if [[ ${#failed_tasks[@]} -gt 0 ]]; then
    echo ""
    echo "失败任务详情:"
    for failed_task in "${failed_tasks[@]}"; do
        echo "  - $failed_task"
    done
fi

# 写入汇总到日志文件
{
echo ""
echo "===== 批量处理汇总 ====="
echo "总任务数: ${#tasks[@]}"
echo "成功任务: $total_success"
echo "失败任务: $total_failed"
echo "完成时间: $(date)"
echo "批量日志: $batch_log_file"
if [[ ${#failed_tasks[@]} -gt 0 ]]; then
    echo ""
    echo "失败任务列表:"
    for failed_task in "${failed_tasks[@]}"; do
        echo "  - $failed_task"
    done
fi
echo "========================"
} >> "$batch_log_file"

# 输出日志文件路径（方便后续查看）
echo ""
echo "详细日志已保存到: $batch_log_file"
