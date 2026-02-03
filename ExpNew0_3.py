# -*- coding: utf-8 -*-
"""
ExpNew0_3.py
实验三：分组大小优化测试 (Group Size Optimization) - Optimized
目标：在大规模标签场景下，寻找吞吐量最高的 Group Size (K 值)。
"""

import logging
import random
import os
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
logger = logging.getLogger("ExpNew0_3")

# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 500  # 海量标签，放大协议开销
GROUP_SIZES = [4, 8, 12, 16, 24, 32, 48, 64,128,256]
REPEAT = 20       # 重复次数，取平均值消除抖动
OUTPUT_DIR = "Results_ExpNew0_3"
MAX_WORKERS = max(1, os.cpu_count() - 2)

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """单个实验任务"""
    k = task_params['k']
    run_id = task_params['run_id']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id)
    rng.shuffle(tags) # 随机化
    
    # 2. 初始化算法
    # 变量: max_group_size = k
    # 固定: is_adaptive=False (排除干扰), target_rho=4 (保持稳健)
    algo = LODS_MTI_Algorithm(max_group_size=k, is_adaptive=True, target_rho=4)
    algo.initialize(tags)
    
    # 3. 配置环境 (理想环境，专注考察调度效率)
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=False,
        packet_error_rate=0.0,
        BIT_ERROR_RATE=0.0
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算吞吐量
    total_time_s = stats['total_time_us'] / 1e6
    throughput = TAG_COUNT / total_time_s if total_time_s > 0 else 0
    
    # 注入自定义指标
    stats['Throughput'] = throughput
    stats['Time_s'] = total_time_s
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"GroupSize": k}, # X轴
        "algorithm_name": "Improve_One", # 单一算法对比不同参数
        "run_id": run_id
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 已自动创建输出目录: {OUTPUT_DIR}")
        
    print(f"🚀 启动 Exp0_3: 分组大小优化 (Tags={TAG_COUNT})")
    print(f"⚙️  配置: Workers={MAX_WORKERS}, GroupSizes={GROUP_SIZES}")
    
    analytics = SimulationAnalytics()
    
    # 1. 构建任务
    tasks = []
    for k in GROUP_SIZES:
        for r in range(REPEAT):
            tasks.append({'k': k, 'run_id': r})
            
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
                
                if results_collected % 10 == 0:
                    print(f"\r进度: {results_collected}/{total_tasks} ({(results_collected/total_tasks):.1%})", end="")
                    
            except Exception as e:
                logger.error(f"❌ 任务失败: {e}")
                
    print("\n✅ 所有仿真任务完成。正在保存数据...")
    
    # 3. 保存数据
    # X轴为 GroupSize，生成 raw_Throughput.csv, raw_Time_s.csv
    analytics.save_to_csv(x_axis_key='GroupSize', output_dir=OUTPUT_DIR)
    
    print(f"💾 数据已保存至: {OUTPUT_DIR}/")
    print("   请运行 Plot_Exp0_3.py 生成可视化图表。")