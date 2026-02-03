# -*- coding: utf-8 -*-
"""
Exp_Sup_7_Bit_Fly.py
补充实验七：微观物理层损伤鲁棒性验证 (Micro-Physical Resilience)

目标：
1. 验证 LODS-MTI 的多数投票机制 (Majority Voting) 对抗 "比特擦除 (Burst Erasure)" 的能力。
2. 验证对抗 "时序抖动 (Timing Jitter / Bit Slip)" 的能力。
3. 证明：相比于脆弱的 Fast Mode (rho=2), Robust Mode (rho=4) 提供了物理层级的自愈合能力。

实验设计：
- Sub-Experiment A: Burst Erasure Tolerance (X轴: Erasure Length [0-8 bits])
- Sub-Experiment B: Jitter Tolerance (X轴: Jitter Offset [0-4 bits])
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

# --- 导入支持物理损伤透传的算法 ---
from lods_mti_bit_fly_algo import LODS_MTI_BitFly_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_7")

# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 500       # 固定标签数量
MISSING_RATE = 0.5    # 50% 缺失率，制造充足的 False Positive 机会
REPEAT = 100           # 重复次数需足够多，因为损伤是概率性的

OUTPUT_DIR = "Results_Exp_Sup_7"
MAX_WORKERS = max(1, os.cpu_count() - 2)

# 定义两组实验的自变量范围
BURST_RANGE = list(range(0, 9))  # 0 to 8 bits
JITTER_RANGE = list(range(0, 5)) # 0 to 4 bits

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    单个实验任务
    """
    exp_type = task_params['exp_type'] # 'Burst' or 'Jitter'
    x_val = task_params['x_val']       # 具体强度值
    rho_mode = task_params['rho_mode'] # 2 or 4
    run_id = task_params['run_id']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    missing_count = int(TAG_COUNT * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
    
    # 2. 实例化算法 (使用支持 Bit-Fly 的版本)
    # 关闭自适应，强制指定 rho 以观察物理特性
    algo = LODS_MTI_BitFly_Algorithm(
        max_group_size=128, 
        is_adaptive=False, 
        target_rho=rho_mode
    )
    
    label = f"LODS (rho={rho_mode})"
    
    algo.initialize(tags)
    
    # 3. 配置环境 (根据实验类型注入不同损伤)
    burst_len = 0
    jitter_val = 0
    
    if exp_type == 'Burst':
        burst_len = x_val
    elif exp_type == 'Jitter':
        jitter_val = x_val
        
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,       
        packet_error_rate=0.0,   
        BIT_ERROR_RATE=0.0,      # 关闭随机噪声，隔离观察结构性损伤
        CLOCK_DRIFT_RATE=0.0,    # 关闭漂移，专注看突发擦除/滑移
        # --- 注入损伤 ---
        BURST_ERASURE_LEN=burst_len,
        JITTER_OFFSET=jitter_val
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算核心指标：Reliability (Recall)
    # 获取算法输出的两个集合
    verified_present, verified_missing = algo.get_results()
    
    # Ground Truth
    actual_present = {t.epc for t in tags if t.is_present}
    actual_missing = {t.epc for t in tags if not t.is_present}
    
    # 统计 TP, FN
    true_positives = len(verified_present.intersection(actual_present))
    false_negatives = len(actual_present - verified_present)
    
    recall = true_positives / len(actual_present) if actual_present else 1.0
    
    stats['Reliability'] = recall
    stats['Metric_Value'] = x_val # 记录 X 轴的值方便绘图
    
    # 为了区分两组实验，我们在 algorithm_name 里带上实验类型前缀是不行的，
    # 因为 Tool.py 是按列 pivot。
    # 策略：我们把两组实验分开跑，或者在文件名上做区分。
    # 这里我们生成两套 CSV，通过后面的 save_to_csv 区分目录或文件前缀。
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"Burst": burst_len, "Jitter": jitter_val},
        "algorithm_name": label,
        "run_id": run_id,
        "exp_type": exp_type,
        "x_val": x_val
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    # 创建子目录以区分两组实验结果
    dir_burst = os.path.join(OUTPUT_DIR, "Burst_Experiment")
    dir_jitter = os.path.join(OUTPUT_DIR, "Jitter_Experiment")
    
    for d in [OUTPUT_DIR, dir_burst, dir_jitter]:
        if not os.path.exists(d):
            os.makedirs(d)
            
    print(f"🚀 启动 Exp_Sup_7: 微观物理层损伤鲁棒性验证")
    print(f"🎯 目标: 验证 Majority Voting 对 Burst Erasure 和 Bit Slip 的抵抗力")
    
    # --- 实验 A: Burst Erasure ---
    print(f"\n[Phase A] Running Burst Erasure Experiment (Len: {BURST_RANGE})...")
    tasks_a = []
    for x in BURST_RANGE:
        for rho in [2, 4]:
            for r in range(REPEAT):
                tasks_a.append({
                    'exp_type': 'Burst', 'x_val': x, 'rho_mode': rho, 'run_id': r
                })
                
    analytics_a = SimulationAnalytics()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures_a = [executor.submit(run_task, t) for t in tasks_a]
        cnt = 0
        total = len(tasks_a)
        for f in concurrent.futures.as_completed(futures_a):
            res = f.result()
            analytics_a.add_run_result(res['stats'], res['sim_config'], res['algorithm_name'], res['run_id'])
            cnt += 1
            if cnt % 50 == 0: print(f"\r  Progress: {cnt/total:.1%}", end="")
            
    analytics_a.save_to_csv(x_axis_key='Metric_Value', output_dir=dir_burst)
    print(f"\n  ✅ Saved Burst results to {dir_burst}")

    # --- 实验 B: Jitter Tolerance ---
    print(f"\n[Phase B] Running Jitter Tolerance Experiment (Offset: {JITTER_RANGE})...")
    tasks_b = []
    for x in JITTER_RANGE:
        for rho in [2, 4]:
            for r in range(REPEAT):
                tasks_b.append({
                    'exp_type': 'Jitter', 'x_val': x, 'rho_mode': rho, 'run_id': r
                })

    analytics_b = SimulationAnalytics()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures_b = [executor.submit(run_task, t) for t in tasks_b]
        cnt = 0
        total = len(tasks_b)
        for f in concurrent.futures.as_completed(futures_b):
            res = f.result()
            analytics_b.add_run_result(res['stats'], res['sim_config'], res['algorithm_name'], res['run_id'])
            cnt += 1
            if cnt % 50 == 0: print(f"\r  Progress: {cnt/total:.1%}", end="")

    analytics_b.save_to_csv(x_axis_key='Metric_Value', output_dir=dir_jitter)
    print(f"\n  ✅ Saved Jitter results to {dir_jitter}")
    
    print("\n🎉 所有微观损伤实验完成。")
    print("请查看 Results_Exp_Sup_7 下的子目录。重点关注 raw_Reliability.csv")