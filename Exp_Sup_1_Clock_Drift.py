# -*- coding: utf-8 -*-
"""
Exp_Sup_1.py
补充实验一：时钟漂移压力测试 (Clock Drift Tolerance Stress Test)
目标：
1. 验证相干约束理论：证明 Fixed-128 (红线) 在漂移 > 15% 时性能崩塌。
2. 验证安全裕量：证明 Adaptive (蓝线) 利用自适应机制能容忍更高的漂移。
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

# --- 导入算法 ---
from lods_mti_algo import LODS_MTI_Algorithm         # 蓝线 (Adaptive)
from lods_mti_sup_algo import LODS_MTI_Sup_Algo      # 红线 (Fixed-128 Stress Test)

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_1")

# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 1000
MISSING_RATE = 0.5  # 固定缺失率 0.5 (最难场景)

# Drift List: 0.00 -> 0.20 (0% -> 20%)
DRIFT_LIST = []
idx = 0.00
while idx <= 0.005001:
    DRIFT_LIST.append(idx)
    idx += 0.0005

REPEAT = 40
OUTPUT_DIR = "Results_Exp_Sup_1"
MAX_WORKERS = max(1, os.cpu_count() - 2) 

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    单个实验任务
    """
    # 解包参数
    drift_rate = task_params['drift_rate']
    run_id = task_params['run_id']
    algo_type = task_params['algo_type']
    
    # 1. 生成场景 (Seed 绑定 run_id)
    # 保持实验的可重复性，使得红蓝两线在面对同一组标签分布时进行 PK
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    # 模拟 50% 缺失 (制造高不确定性)
    missing_count = int(TAG_COUNT * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
    
    # 2. 实例化算法
    if algo_type == 'adaptive':
        # 蓝线: 开启自适应 (Adaptive Mode)
        # 预期行为: 遇到漂移导致误码上升时，自动降速保可靠性
        algo = LODS_MTI_Algorithm(is_adaptive=True, target_rho=4) 
        label = "LODS-MTI (Adaptive)"
    elif algo_type == 'fixed_128':
        # 红线: 压力测试专用 (Fixed-128)
        # 预期行为: 死板地坚持 K=128，直到漂移导致同步丢失
        algo = LODS_MTI_Sup_Algo() # 默认参数即为 fixed 128
        label = "LODS-Fixed-128 (Stress)"
    else:
        raise ValueError(f"Unknown algo_type: {algo_type}")

    algo.initialize(tags)
    
    # 3. 配置环境 (注入时钟漂移)
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,       # 开启物理层检查
        packet_error_rate=0.0,   # 关闭随机丢包，聚焦漂移
        BIT_ERROR_RATE=0.0,      # 关闭随机误码，聚焦漂移
        CLOCK_DRIFT_RATE=drift_rate # <--- 核心变量
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算指标
    # (1) Reliability / Recall
    present_gt = {t.epc for t in tags if t.is_present}
    found_present, _ = algo.get_results()
    tp = len(found_present.intersection(present_gt))
    recall = tp / len(present_gt) if present_gt else 0
    
    # (2) Goodput (Effective Throughput)
    # Tool.py 计算的是 throughput (Total / Time), 这里我们计算 Goodput (Correct / Time)
    # stats['total_time_us'] 由 framework 返回
    total_time_s = stats['total_time_us'] / 1e6
    goodput = tp / total_time_s if total_time_s > 0 else 0
    
    # 6. 数据封装
    # Tool.py 会自动提取 stats 中的数值列进行平均和拆分
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
    
    # 1. 创建目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 创建目录: {OUTPUT_DIR}")
        
    print(f"🚀 启动 Exp_Sup_1: 时钟漂移压力测试 (Drift Stress)")
    print(f"🎯 目标: 验证相干约束理论边界与系统安全裕量")
    print(f"⚙️  Workers={MAX_WORKERS}, Repeat={REPEAT}, Drift_Range=[0%, 20%]")
    
    analytics = SimulationAnalytics()
    
    # 2. 构建任务
    tasks = []
    for drift in DRIFT_LIST:
        for r in range(REPEAT):
            # 对照组 1: 蓝线 (Adaptive)
            tasks.append({'drift_rate': drift, 'run_id': r, 'algo_type': 'adaptive'})
            # 对照组 2: 红线 (Fixed-128 Stress)
            tasks.append({'drift_rate': drift, 'run_id': r, 'algo_type': 'fixed_128'})
            
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
                
                # 进度条
                if results_collected % 10 == 0 or results_collected == total_tasks:
                    progress = results_collected / total_tasks
                    print(f"\r🚀 进度: {progress:.1%} ({results_collected}/{total_tasks})", end="")
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")

    print("\n✅ 仿真结束。正在生成数据文件...")
    
    # 4. 保存数据
    # 将按照 'Drift_Rate' 为 X 轴拆分文件
    # 结果将生成: raw_Recall.csv, raw_Goodput.csv 等
    analytics.save_to_csv(x_axis_key='Drift_Rate', output_dir=OUTPUT_DIR)
    
    print(f"💾 数据保存完毕: {OUTPUT_DIR}/")
    print(f"   (请使用 output 中的 raw_Recall.csv 和 raw_Goodput.csv 绘制红蓝对比图)")