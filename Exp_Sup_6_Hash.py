# -*- coding: utf-8 -*-
"""
Exp_Sup_6_Hardware.py
补充实验六：硬件可行性验证 (Hardware Feasibility & Complexity Analysis)

目标：
1. 验证 "Power-of-2 Constraint" 的影响：
   对比标准 LODS-MTI (允许任意 K) 与 LODS-MTI-Limit (强制 K=2^n) 的性能。
2. 证明：
   强制 K 为 2 的幂次方（从而将取模运算优化为位运算）不会导致吞吐量下降。
   这为在无源标签上移除除法器/取模器提供了强有力的实验支撑。
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

# --- 导入对比算法 ---
# 1. 基准版本 (Arbitrary K)
from lods_mti_algo import LODS_MTI_Algorithm
# 2. 硬件优化版本 (Power of 2 Only)
from lods_mti_limit_algo import LODS_MTI_LIMIT_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_6")

# =========================================================
# 🧪 实验配置
# =========================================================
# 核心变量: 标签总数 (100 -> 1000)
# 我们需要观察随着规模扩大，两者性能是否依然紧密贴合
TAG_COUNTS_LIST = list(range(100, 1001, 50))

MISSING_RATE = 0.5 

# 环境配置: 
# 使用微量噪声 (BER=0.1%) 模拟真实环境，
# 但又不至于让噪声主导结果，重点看调度效率。
ENV_BER = 0.000 

REPEAT = 20 # 重复次数，确保均值平滑
OUTPUT_DIR = "Results_Exp_Sup_6"
MAX_WORKERS = max(1, os.cpu_count() - 2)

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    单个实验任务
    """
    n_tags = task_params['n_tags']
    algo_type = task_params['algo_type'] # 'Standard' or 'Limit'
    run_id = task_params['run_id']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(n_tags)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    missing_count = int(n_tags * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
    
    # 2. 实例化算法
    if algo_type == 'LODS_Standard':
        # 基准版本：允许任意 K
        algo = LODS_MTI_Algorithm(
            max_group_size=128, 
            is_adaptive=True
        )
        label = "LODS-MTI (Arbitrary K)"
        
    elif algo_type == 'LODS_Limit':
        # 硬件优化版：强制 K=2^n
        algo = LODS_MTI_LIMIT_Algorithm(
            max_group_size=128, 
            is_adaptive=True
        )
        label = "LODS-MTI (Power-of-2)"
    else:
        raise ValueError(f"Unknown algo type: {algo_type}")
    
    algo.initialize(tags)
    
    # 3. 配置环境
    cfg = SimulationConfig(
        TOTAL_TAGS=n_tags,
        ENABLE_NOISE=True,       
        packet_error_rate=0.0,   
        BIT_ERROR_RATE=ENV_BER, 
        CLOCK_DRIFT_RATE=0.002 # 加上一点点漂移(0.2%)，验证鲁棒性
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算指标
    total_time_s = stats['total_time_us'] / 1e6
    throughput = n_tags / total_time_s if total_time_s > 0 else 0
    
    # 这里的 Goodput 定义为：处理完所有标签 / 时间
    # 因为在 MTI 场景下，确认 Missing 也是有效产出
    stats['System_Throughput'] = throughput
    stats['Total_Time_ms'] = stats['total_time_us'] / 1000.0
    
    # 记录额外的元数据
    stats['Algorithm_Type'] = algo_type
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"TOTAL_TAGS": n_tags, "BER": ENV_BER},
        "algorithm_name": label, # 用于绘图图例
        "run_id": run_id,
        "x_val": n_tags
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 创建目录: {OUTPUT_DIR}")
        
    print(f"🚀 启动 Exp_Sup_6: 硬件可行性验证 (Hardware Feasibility)")
    print(f"🎯 目标: 证明 Power-of-2 限制对性能无显著影响")
    print(f"⚙️  Env: N={TAG_COUNTS_LIST}, Repeat={REPEAT}")
    
    analytics = SimulationAnalytics()
    
    # 2. 构建任务
    tasks = []
    # 两个对比组
    algo_variants = ['LODS_Standard', 'LODS_Limit']
    
    for n in TAG_COUNTS_LIST:
        for var in algo_variants:
            for r in range(REPEAT):
                tasks.append({
                    'n_tags': n, 
                    'algo_type': var, 
                    'run_id': r
                })
            
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
                    algo_name=res['algorithm_name'],
                    run_id=res['run_id']
                )
                
                if results_collected % 50 == 0 or results_collected == total_tasks:
                    progress = results_collected / total_tasks
                    print(f"\r🚀 进度: {progress:.1%} ({results_collected}/{total_tasks})", end="")
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")

    print("\n✅ 仿真结束。正在生成数据文件...")
    
    # 4. 保存数据
    # 关键：以 'TOTAL_TAGS' 为 X 轴
    analytics.save_to_csv(x_axis_key='TOTAL_TAGS', output_dir=OUTPUT_DIR)
    
    print(f"💾 数据保存完毕: {OUTPUT_DIR}/")
    print(f"   请重点关注 raw_System_Throughput.csv 和 raw_Total_Time_ms.csv")
    print(f"   预期结果: 两条曲线 ('Arbitrary K' 和 'Power-of-2') 应该几乎重合。")