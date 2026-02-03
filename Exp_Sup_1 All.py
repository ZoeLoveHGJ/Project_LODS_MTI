# -*- coding: utf-8 -*-
"""
Exp_Sup_1.py
补充实验一 (Extended)：全算法时钟漂移压力测试
目标：
1. 对比 LODS-MTI (Adaptive/Fixed) 与 Slotted Baselines (CR-MTI, ECUMI等) 的抗漂移特性。
2. 揭示 "Long-Stream" (LODS) 与 "Short-Packet" (Slotted) 在物理层稳定性的根本差异。
"""

import logging
import random
import os
import concurrent.futures
import multiprocessing
import pandas as pd
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

# --- 导入所有对比算法 ---
from lods_mti_algo import LODS_MTI_Algorithm
from lods_mti_sup_algo import LODS_MTI_Sup_Algo
from cr_mti_algo import CR_MTI_Algorithm
from ctmti_algo import CTMTI_Algorithm
from ecumi_algo import ECUMI_Algorithm
from ISMTI_Algo import ISMTI_Algorithm
from cpt_algo import CPT_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_1")

# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 1000
MISSING_RATE = 0.5 

# Drift Range: 0.00 -> 0.05 (0% -> 5%)
DRIFT_LIST = []
idx = 0.00
while idx <= 0.021: # 聚焦在 0% - 2% 的高精度区间
    DRIFT_LIST.append(round(idx, 4))
    idx += 0.002

REPEAT = 3
OUTPUT_DIR = "Results_Exp_Sup_1_All"
MAX_WORKERS = max(1, os.cpu_count() - 2) 

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    通用实验任务执行器
    """
    drift_rate = task_params['drift_rate']
    run_id = task_params['run_id']
    algo_key = task_params['algo_key']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    missing_count = int(TAG_COUNT * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
    
    # 2. 实例化算法 (算法工厂)
    # 根据 Algorithm_Config.py 中的推荐参数配置
    algo = None
    label = ""
    
    if algo_key == 'LODS_Adaptive':
        algo = LODS_MTI_Algorithm(is_adaptive=True, target_rho=4)
        label = "LODS-MTI (Adaptive)"
        
    elif algo_key == 'LODS_Fixed_128':
        algo = LODS_MTI_Sup_Algo() # Fixed K=128
        label = "LODS-Fixed-128 (Stress)"
        
    elif algo_key == 'CR_MTI':
        # 论文推荐参数: lambda=1.5, w_len=34 (TMC '23)
        algo = CR_MTI_Algorithm(lambda_factor=1.5, w_len=34) 
        label = "CR-MTI"
        
    elif algo_key == 'CT_MTI':
        algo = CTMTI_Algorithm(B=4, alpha=0.5)
        label = "CTMTI"
        
    elif algo_key == 'ECUMI':
        algo = ECUMI_Algorithm(rho=1.0)
        label = "ECUMI"
        
    elif algo_key == 'ISMTI':
        algo = ISMTI_Algorithm(initial_q=0.5)
        label = "ISMTI"

    elif algo_key == 'CPT':
        algo = CPT_Algorithm(pseudo_id_len=12)
        label = "CPT"
        
    else:
        raise ValueError(f"Unknown algo_key: {algo_key}")

    algo.initialize(tags)
    
    # 3. 配置环境
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,
        packet_error_rate=0.0,
        BIT_ERROR_RATE=0.0,
        CLOCK_DRIFT_RATE=drift_rate # <--- 变量
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算指标 (Recall & Goodput)
    present_gt = {t.epc for t in tags if t.is_present}
    found_present, _ = algo.get_results()
    
    # Recall
    tp = len(found_present.intersection(present_gt))
    recall = tp / len(present_gt) if present_gt else 1.0
    
    # Goodput
    total_time_s = stats['total_time_us'] / 1e6
    goodput = tp / total_time_s if total_time_s > 0 else 0
    
    stats['Recall'] = recall
    stats['Goodput'] = goodput
    stats['Drift_Percent'] = drift_rate * 100
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"TOTAL_TAGS": TAG_COUNT, "Drift_Rate": drift_rate},
        "algorithm_name": label,
        "run_id": run_id
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"🚀 启动全算法漂移测试")
    analytics = SimulationAnalytics()
    
    # --- 定义要对比的算法列表 ---
    # 建议: 跑太慢的算法(如CPT)如果不需要可以注释掉
    TARGET_ALGOS = [
        'LODS_Adaptive', 
        'LODS_Fixed_128',
        'CR_MTI',
        'ECUMI',
        'CT_MTI',
        'ISMTI',
        'CPT'
    ]
    
    tasks = []
    for drift in DRIFT_LIST:
        for r in range(REPEAT):
            for algo_key in TARGET_ALGOS:
                tasks.append({
                    'drift_rate': drift, 
                    'run_id': r, 
                    'algo_key': algo_key
                })
            
    print(f"📋 任务数: {len(tasks)}")

    # 并行执行 (代码同前，省略部分打印逻辑以节省篇幅)
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(run_task, t) for t in tasks]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                res = future.result()
                analytics.add_run_result(
                    res['stats'], res['sim_config'], 
                    res['algorithm_name'], res['run_id']
                )
                if i % 50 == 0: print(f"\r进度: {i}/{len(tasks)}", end="")
            except Exception as e:
                logger.error(f"Error: {e}")

    analytics.save_to_csv(x_axis_key='Drift_Rate', output_dir=OUTPUT_DIR)
    print(f"\n✅ 完成。数据在 {OUTPUT_DIR}")