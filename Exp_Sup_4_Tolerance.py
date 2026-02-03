# -*- coding: utf-8 -*-
"""
Exp_Sup_4_Tolerance.py
补充实验四：自适应容忍度阈值敏感性分析 (Tolerance Threshold Sensitivity)

目标：
1. 验证统计边界：证明 epsilon=0.30 是区分"可恢复噪声"与"不可恢复错误"的最优统计分界线。
2. 展示权衡 (Trade-off)：
   - epsilon 过低 (<0.25): 系统过于保守，死守低速模式，吞吐量低。
   - epsilon 过高 (>0.35): 系统在噪声下盲目切回高速，导致可靠性崩塌。
   - epsilon = 0.30: 处于"甜点区" (Sweet Spot)，兼顾 Recall 和 Goodput。
"""

import logging
import random
import os
import concurrent.futures
import multiprocessing
import pandas as pd
import numpy as np
from typing import List, Dict, Any

# --- 导入核心组件 ---
from framework import (
    run_high_fidelity_simulation, 
    SimulationConfig, 
    Tag,
    SlotResult,
    ReaderCommand,
    PacketType
)
from Tool import SimulationAnalytics

# --- 导入专用算法 ---
# 注意：这里导入的是刚才新建的 sensitivity 类
from lods_mti_sensitivity import LODS_MTI_Sensitivity

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_4")

# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 1000
MISSING_RATE = 0.5 

# 核心变量: 容忍度阈值 (0.00 -> 0.60, 步长 0.05)
# 理论预测: 0.30 应该是性能峰值
TOLERANCE_LIST = [round(x, 2) for x in np.arange(0.0, 0.61, 0.05)]

# 固定环境: 8% 的比特误码率
# 理由: 1 - (1-0.08)^4 ≈ 0.28。
# 在 8% 误码下，Imperfect Rate 约为 28%，刚好在 0.30 的容忍范围内。
# 如果阈值设为 0.25，系统会误判；如果设为 0.35，系统会通过。
FIXED_BER = 0.06 

REPEAT = 10 # 次数多一点以消除随机性
OUTPUT_DIR = "Results_Exp_Sup_4"
MAX_WORKERS = max(1, os.cpu_count() - 2) 

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    单个实验任务
    """
    epsilon = task_params['tolerance']
    run_id = task_params['run_id']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    missing_count = int(TAG_COUNT * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
    
    # 2. 实例化算法 (传入当前遍历的 tolerance)
    algo = LODS_MTI_Sensitivity(
        is_adaptive=True, 
        target_rho=4,
        tolerance_threshold=epsilon # <--- 关键变量
    )
    
    algo.initialize(tags)
    
    # 3. 配置环境 (固定 BER=8%)
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,       
        packet_error_rate=0.0,   
        BIT_ERROR_RATE=FIXED_BER, # <--- 固定的高压环境
        CLOCK_DRIFT_RATE=0.0      # 暂时关闭漂移，专注测试误码容忍度
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算指标
    present_gt = {t.epc for t in tags if t.is_present}
    found_present, _ = algo.get_results()
    tp = len(found_present.intersection(present_gt))
    
    # Metric 1: Reliability (Recall)
    recall = tp / len(present_gt) if present_gt else 0
    
    # Metric 2: Goodput (Effective Throughput)
    # Goodput = Correctly Identified Tags / Time
    total_time_s = stats['total_time_us'] / 1e6
    goodput = tp / total_time_s if total_time_s > 0 else 0

    # Metric 3: System Throughput (Raw Throughput)
    throughput = TAG_COUNT / total_time_s if total_time_s > 0 else 0
    
    stats['Recall'] = recall
    stats['Goodput'] = goodput
    stats['System_Throughput'] = throughput
    stats['Tolerance_Threshold'] = epsilon
    
    # 这里的 Algorithm Name 用参数值命名，方便绘图时区分 (虽然我们主要画 X 轴曲线)
    label = f"LODS (eps={epsilon:.2f})" 
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"TOTAL_TAGS": TAG_COUNT, "BER": FIXED_BER, "Tolerance": epsilon},
        "algorithm_name": label,
        "run_id": run_id
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 创建目录: {OUTPUT_DIR}")
        
    print(f"🚀 启动 Exp_Sup_4: 容忍度参数敏感性分析")
    print(f"🎯 目标: 寻找 epsilon 的 Sweet Spot (预期 0.30)")
    print(f"⚙️  Env: BER={FIXED_BER*100}%, Repeat={REPEAT}")
    print(f"📉 Range: epsilon = {TOLERANCE_LIST}")
    
    analytics = SimulationAnalytics()
    
    # 2. 构建任务
    tasks = []
    for eps in TOLERANCE_LIST:
        for r in range(REPEAT):
            tasks.append({'tolerance': eps, 'run_id': r})
            
    total_tasks = len(tasks)
    print(f"📋 任务装载完毕: {total_tasks} 个子任务")

    # 3. 并行执行
    results_collected = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(run_task, t) for t in tasks]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                results_collected += 1
                
                analytics.add_run_result(
                    result_stats=res['stats'],
                    sim_config=res['sim_config'],
                    algo_name=res['algorithm_name'], # 这里其实主要用 X 轴区分
                    run_id=res['run_id']
                )
                
                if results_collected % 50 == 0 or results_collected == total_tasks:
                    progress = results_collected / total_tasks
                    print(f"\r🚀 进度: {progress:.1%} ({results_collected}/{total_tasks})", end="")
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")

    print("\n✅ 仿真结束。正在生成数据文件...")
    
    # 4. 保存数据
    # 关键：以 'Tolerance_Threshold' 为 X 轴
    analytics.save_to_csv(x_axis_key='Tolerance_Threshold', output_dir=OUTPUT_DIR)
    
    print(f"💾 数据保存完毕: {OUTPUT_DIR}/")
    print(f"   请重点关注 raw_Goodput.csv 和 raw_Recall.csv")
    print(f"   预期图表形态: Goodput 呈倒U型，顶点在 0.30 附近；Recall 在 0.30 后断崖式下跌。")