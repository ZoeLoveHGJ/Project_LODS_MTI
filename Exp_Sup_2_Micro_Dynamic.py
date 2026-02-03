# -*- coding: utf-8 -*-
"""
Exp_Sup_2.py (V2 - Multi-Scenario)
补充实验二：微观动力学分析 (Runtime Micro-Dynamics Analysis)

【更新说明】
支持多场景对比 (0% vs 10%)，并将数据清洗为 Tidy Format 统一存储。
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
    AlgorithmInterface
)
from lods_mti_algo import LODS_MTI_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_2")

# =========================================================
# 🕵️‍♂️ 核心组件：算法探针 (The Algorithm Spy)
# =========================================================
class AlgoSpy:
    """
    [代理模式] 包装原始算法，窃听每一轮的决策参数 (K, Rho)
    """
    def __init__(self, real_algo: LODS_MTI_Algorithm):
        self.algo = real_algo
        self.history_records = [] 

    def __getattr__(self, name):
        return getattr(self.algo, name)

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        cmd = self.algo.get_next_command(prev_result)
        
        # 窃听决策
        if cmd.payload_bits > 0 and cmd.expected_reply_bits > 0:
            current_rho = self.algo.current_rho
            if current_rho > 0:
                k_estimated = cmd.expected_reply_bits // current_rho
                self.history_records.append({
                    'K': k_estimated,
                    'Rho': current_rho
                })
        return cmd

# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 1000
MISSING_RATE = 0.5 

# 定义对比场景 (最佳实践：直接定义绘图用的标签)
SCENARIOS = [
    {'drift': 0.00, 'label': 'Ideal (Drift=0%)'},
    {'drift': 0.004, 'label': 'Stress (Drift=0.15%)'},
]

REPEAT = 50        # 每个场景跑 50 次
OUTPUT_DIR = "Results_Exp_Sup_2"
MAX_WORKERS = max(1, os.cpu_count() - 2)

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    单个实验任务
    """
    run_id = task_params['run_id']
    drift_val = task_params['drift']
    label = task_params['label']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    missing_count = int(TAG_COUNT * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
        
    if drift_val == 0.00:
        # 理想环境：模拟系统已处于高速状态 (Aggressive Start)
        print(f"drift:{drift_val}")
        init_rho = 2 
    else:
        # 恶劣环境：模拟系统处于防御状态或冷启动 (Conservative Start)
        init_rho = 4
    real_algo = LODS_MTI_Algorithm(is_adaptive=True, target_rho=init_rho)
    # 2. 实例化算法并安装探针
    # real_algo = LODS_MTI_Algorithm(is_adaptive=True, target_rho=4)
    spy_algo = AlgoSpy(real_algo)
    spy_algo.initialize(tags)
    
    # 3. 配置环境 (动态传入漂移率)
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,
        packet_error_rate=0.0,
        BIT_ERROR_RATE=0.0,
        CLOCK_DRIFT_RATE=drift_val 
    )
    
    # 4. 运行仿真
    run_high_fidelity_simulation(spy_algo, cfg, tags)
    
    # 5. 提取并清洗数据
    records = spy_algo.history_records
    for r in records:
        r['Run_ID'] = run_id
        r['Drift_Val'] = drift_val  # 数值方便计算
        r['Scenario'] = label       # 标签方便绘图
        
    return {
        "status": "success",
        "records": records
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"🚀 启动 Exp_Sup_2: 微观动力学分析 (Multi-Scenario)")
    print(f"🎯 对比场景: {[s['label'] for s in SCENARIOS]}")
    
    # 构建任务列表 (双重循环)
    tasks = []
    for sc in SCENARIOS:
        for r in range(REPEAT):
            tasks.append({
                'run_id': r,
                'drift': sc['drift'],
                'label': sc['label']
            })
            
    print(f"📋 总任务数: {len(tasks)} (正在并行计算...)")
    
    all_micro_records = []
    
    # 并行执行
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(run_task, t) for t in tasks]
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                res = future.result()
                all_micro_records.extend(res['records'])
                
                if i % 20 == 0: 
                    print(f"\r进度: {i}/{len(tasks)}", end="")
            except Exception as e:
                logger.error(f"Error: {e}")
                
    print(f"\n✅ 采集完成。总样本数: {len(all_micro_records)}")
    
    # 保存数据
    if all_micro_records:
        df = pd.DataFrame(all_micro_records)
        
        # 简单统计
        print("\n📊 数据概览:")
        print(df.groupby('Scenario')['K'].describe())
        
        csv_path = os.path.join(OUTPUT_DIR, "raw_Micro_Dynamics_Combined.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n💾 统一数据已保存: {csv_path}")
        print(f"   (包含列: Run_ID, K, Rho, Drift_Val, Scenario)")
        print(f"   (请使用此文件进行重叠直方图绘制)")
        
    else:
        print("❌ 警告: 未收集到数据。")