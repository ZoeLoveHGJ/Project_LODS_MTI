# -*- coding: utf-8 -*-
"""
Exp_Tg_Sensitivity.py (V2.0 - Real Baselines)
防御性实验：物理保护间隔灵敏度分析
对比对象：LODS-MTI (w/ Tg penalty) vs. ISMTI & CPT (Standard)

【目标】
证明即便引入物理间隙，LODS-MTI 的去时隙架构优势依然碾压传统时隙协议。
"""

import logging
import random
import os
import concurrent.futures
import multiprocessing
import pandas as pd
from typing import Dict, Any

from framework import run_high_fidelity_simulation, SimulationConfig, Tag
from Tool import SimulationAnalytics

# 1. 导入特殊变体算法 (LODS)
try:
    from lods_mti_guard_time_algo import LODS_MTI_Guard_Time_Algorithm
except ImportError:
    print("❌ 错误：未找到 lods_mti_guard_time_algo.py")
    exit(1)

# 2. 导入对比算法配置 (ISMTI, CPT)
try:
    from Algorithm_Config import ALGORITHM_LIBRARY
except ImportError:
    print("❌ 错误：未找到 Algorithm_Config.py")
    exit(1)

# =========================================================
# 🔬 实验配置
# =========================================================
TAG_COUNTS = [2000]       # 固定负载
REPEAT = 20               # 重复次数

# 自变量: Guard Interval (Bits)
TG_RANGE = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5,2.0]

# 参与对比的算法名单
# 注意：LODS 我们单独处理，这里列出要跑的基准算法 Key
BASELINE_ALGOS = ['ISMTI', 'CPT'] 

OUTPUT_DIR = "Results_Exp_Sup_8_Guard_Time"
MAX_WORKERS = max(1, os.cpu_count() - 2)

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    tg_val = task_params['tg_val']
    run_id = task_params['run_id']
    n_tags = task_params['n_tags']
    algo_type = task_params['algo_type'] # 'LODS_GTA' or 'ISMTI', 'CPT'
    
    # 1. 生成标签
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(n_tags)]
    rng = random.Random(run_id)
    rng.shuffle(tags)
    
    # 2. 初始化算法
    algo = None
    algo_name = ""
    
    if algo_type == 'LODS_GTA':
        # --- LODS (Guard Time Aware) ---
        algo = LODS_MTI_Guard_Time_Algorithm(
            max_group_size=128, 
            target_rho=2,      # 激进模式测试吞吐量上限
            is_adaptive=True 
        )
        algo_name = "LODS-MTI"
    else:
        # --- Baselines (From Config) ---
        # 动态加载类并实例化
        cfg = ALGORITHM_LIBRARY.get(algo_type)
        if not cfg:
            raise ValueError(f"Unknown algo: {algo_type}")
        
        AlgoClass = cfg['class']
        params = cfg['params']
        algo = AlgoClass(**params)
        algo_name = cfg.get('label', algo_type)
    
    algo.initialize(tags)
    
    # 3. 配置环境
    # 注意：对于 ISMTI/CPT，GUARD_INTERVAL_BITS 不会生效(penalty=0)，
    # 因为它们不触发 concatenation，这符合物理事实(它们只有标准T1/T2)
    sim_cfg = SimulationConfig(
        TOTAL_TAGS=n_tags,
        ENABLE_NOISE=False,         
        GUARD_INTERVAL_BITS=tg_val, 
        CLOCK_DRIFT_RATE=0.0        
    )
    
    # 4. 运行
    stats = run_high_fidelity_simulation(algo, sim_cfg, tags)
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {
            "Guard_Interval_Bits": tg_val,
            "TOTAL_TAGS": n_tags
        },
        "algorithm_name": algo_name, # 用于 Tool.py 分列
        "run_id": run_id,
        "tg_val": tg_val
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"🚀 启动 Exp_Tg_Sensitivity (V2): Real Baselines Comparison")
    print(f"🎯 Targets: LODS-MTI vs {BASELINE_ALGOS}")
    print(f"🎯 Tg Range: {TG_RANGE} bits")
    
    tasks = []
    
    # 1. 生成 LODS 任务 (受 Tg 影响)
    for tg in TG_RANGE:
        for r in range(REPEAT):
            for n in TAG_COUNTS:
                tasks.append({
                    'algo_type': 'LODS_GTA', 
                    'tg_val': tg, 'run_id': r, 'n_tags': n
                })

    # 2. 生成 Baseline 任务 (理论上不受 Tg 影响，作为水平参考线)
    # 我们也跑所有 Tg 点，以便在图中画出完整的线（含随机波动）
    for name in BASELINE_ALGOS:
        for tg in TG_RANGE:
            for r in range(REPEAT):
                for n in TAG_COUNTS:
                    tasks.append({
                        'algo_type': name,
                        'tg_val': tg, 'run_id': r, 'n_tags': n
                    })
                
    analytics = SimulationAnalytics()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(run_task, t) for t in tasks]
        cnt = 0
        total = len(tasks)
        print(f"Processing {total} tasks...")
        
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            analytics.add_run_result(
                res['stats'], 
                res['sim_config'], 
                res['algorithm_name'], 
                res['run_id']
            )
            cnt += 1
            if cnt % 20 == 0: print(f"\r Progress: {cnt/total:.1%}", end="")
            
    # 保存结果
    analytics.save_to_csv(x_axis_key='Guard_Interval_Bits', output_dir=OUTPUT_DIR)
    
    print(f"\n✅ 实验完成。数据已保存至 {OUTPUT_DIR}/raw_throughput.csv")