# -*- coding: utf-8 -*-
"""
ExpNew0_2.py
实验二：动态场景自适应测试 (The Extended Rollercoaster)
目标：验证算法在 [理想 -> 突发干扰 -> 理想恢复] 三段式场景下的表现。
"""

import logging
import random
import os
import math 
import concurrent.futures
import multiprocessing
import pandas as pd
from typing import Dict, Any

# --- 导入核心组件 ---
from framework import (
    run_high_fidelity_simulation, 
    SimulationConfig, 
    Tag
)
from Tool import SimulationAnalytics
from lods_mti_algo import LODS_MTI_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp0New_2")

# =========================================================
# 🧪 实验配置
# =========================================================
# 【修改1】总轮次拓展为 200
ROUNDS = 200
TAG_COUNT = 1000
OUTPUT_DIR = "Results_ExpNew0_2"
MAX_WORKERS = max(1, os.cpu_count() - 2)

def get_env_params(round_idx):
    """
    【修改2】三段式环境剧本
    Phase 1 (0-49): Ideal (Base Performance)
    Phase 2 (50-149): Cosine Wave Storm (Dynamic Adaptation)
    Phase 3 (150-199): Ideal (Recovery Check)
    """
    
    # 1. 定义阶段
    if round_idx < 50:
        # Phase 1: 绝对理想
        return 0.0, 0.0
        
    elif round_idx >= 150:
        # Phase 3: 绝对理想 (用于检查恢复是否滞后)
        return 0.0, 0.0
        
    else:
        # Phase 2: 波动区间 (50 <= round_idx < 150)
        # 将 [50, 150] 映射到 [0, 2π]
        wave_duration = 100
        relative_idx = round_idx - 50
        phase = 2 * math.pi * relative_idx / wave_duration
        
        # 波动因子 factor: 0 -> 1 -> 0
        factor = (1 - math.cos(phase)) / 2 
        
        # 参数配置
        MAX_BER = 0.10
        
        # Missing Rate: 保持基准为 0，只有波动时才增加
        MIN_MISSING = 0.0
        MAX_MISSING = 0.30
        
        current_ber = MAX_BER * factor
        current_missing = MIN_MISSING + (MAX_MISSING - MIN_MISSING) * factor
        
        return current_ber, current_missing

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """单个实验任务 (Process Safe)"""
    algo_type = task_params['algo_type']
    round_idx = task_params['round_idx']
    
    # 1. 获取环境参数
    ber, missing_rate = get_env_params(round_idx)
    
    # 2. 生成场景 (Seed 绑定 Round 确保所有算法面对同一场景)
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(2024 + round_idx)
    rng.shuffle(tags)
    
    num_missing = int(TAG_COUNT * missing_rate)
    for i in range(num_missing): tags[i].is_present = False
    
    # 3. 初始化算法
    if algo_type == 'Fixed-Fast':
        algo = LODS_MTI_Algorithm(is_adaptive=False, target_rho=2)
    elif algo_type == 'Fixed-Robust':
        algo = LODS_MTI_Algorithm(is_adaptive=False, target_rho=4)
    else: # Adaptive
        algo = LODS_MTI_Algorithm(is_adaptive=True)
        
    algo.initialize(tags)
    
    # 4. 配置环境
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,
        packet_error_rate=0.0,
        BIT_ERROR_RATE=ber
    )
    
    # 5. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 6. 计算指标
    present_gt = {t.epc for t in tags if t.is_present}
    found_present, _ = algo.get_results()
    
    tp = len(found_present.intersection(present_gt))
    recall = tp / len(present_gt) if present_gt else 1.0
    time_ms = stats['total_time_us'] / 1000.0
    
    stats['Time_ms'] = time_ms
    stats['Recall'] = recall
    stats['Env_Severity'] = 1 if ber > 0 else 0
    stats['Real_BER'] = ber
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"Round": round_idx + 1}, # X轴
        "algorithm_name": algo_type,
        "run_id": 0 
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 已自动创建输出目录: {OUTPUT_DIR}")
        
    print(f"🚀 启动 Exp0_2: 三段式动态测试 (Ideal -> Storm -> Ideal)")
    print(f"⚙️  配置: Workers={MAX_WORKERS}, Total Rounds={ROUNDS}")
    print(f"   - Phase 1 (0-50): Ideal")
    print(f"   - Phase 2 (50-150): Cosine Wave")
    print(f"   - Phase 3 (150-200): Ideal")
    
    analytics = SimulationAnalytics()
    
    # 1. 构建任务
    tasks = []
    algos = ['Fixed-Fast', 'Fixed-Robust', 'Adaptive']
    for r in range(ROUNDS):
        for algo in algos:
            tasks.append({'algo_type': algo, 'round_idx': r})
            
    total_tasks = len(tasks)
    print(f"📋 总任务数: {total_tasks} (正在分发...)")
    
    # 2. 并行执行
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
                
                if results_collected % 20 == 0:
                    print(f"\r进度: {results_collected}/{total_tasks} ({(results_collected/total_tasks):.1%})", end="")
                    
            except Exception as e:
                logger.error(f"❌ 任务失败: {e}")
                
    print("\n✅ 所有仿真任务完成。正在保存数据...")
    
    # 3. 保存数据
    analytics.save_to_csv(x_axis_key='Round', output_dir=OUTPUT_DIR)
    
    print(f"💾 数据已保存至: {OUTPUT_DIR}/")
    print("   建议更新 Plot 脚本的 X 轴范围设置。")