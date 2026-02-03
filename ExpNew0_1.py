# -*- coding: utf-8 -*-
"""
ExpNew0_1.py
实验一：误码率压力测试 (Bit Error Stress Test) - Multiprocessing Optimized
目标：验证 3/4 投票机制在物理层存在误码时的抗干扰能力。
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
from lods_mti_algo import LODS_MTI_Algorithm
from lods_mti_strict_algo import LODS_MTI_Strict_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("ExpNew0_1")

# =========================================================
# 🧬 定义对照组：严格匹配算法 (No Voting)
# =========================================================
# class Strict_Improve_One(LODS_MTI_Algorithm):
#     """
#     [对照组] 严格匹配版 Improve_One
#     区别：必须所有比特完全匹配才判定在场 (Threshold = Rho)。
#     保留此类的定义，以防本地需要调试或覆盖逻辑。
#     """
# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 1000
# BER_LIST = [0, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 2e-2, 5e-2] # 0% -> 5% 误码
BER_LIST = []
INDEX = 0.00
while INDEX <= 0.1001:
    BER_LIST.append(INDEX)
    INDEX += 0.005
REPEAT = 20
OUTPUT_DIR = "Results_ExpNew0_1"
MAX_WORKERS = max(1, os.cpu_count() - 2) # 留 2 个核给系统，其余跑仿真

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    单个实验任务，设计为纯函数以便于多进程调用
    """
    # 解包参数
    ber = task_params['ber']
    run_id = task_params['run_id']
    use_voting = task_params['use_voting']
    
    # 1. 生成场景 (Seed 绑定 run_id 确保可复现性)
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) # 局部随机源
    rng.shuffle(tags)
    
    # 模拟 10% 缺失 (制造混淆)
    for i in range(100): tags[i].is_present = False
    
    # 2. 实例化算法
    if use_voting:
        # Ours: 允许 3/4 投票
        algo = LODS_MTI_Algorithm(is_adaptive=False, target_rho=4) 
        label = "Ours (Voting)"
    else:
        # Baseline: 严格匹配
        algo = LODS_MTI_Strict_Algorithm(is_adaptive=False, target_rho=4) 
        label = "Baseline (Without Voting)" 

    algo.initialize(tags)
    
    # 3. 配置环境
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,
        packet_error_rate=0.0, # 排除整包丢包干扰，只测误码
        BIT_ERROR_RATE=ber     # <--- 变量
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算 Recall (Tool.py 默认不计算 Recall，我们需要手动算好传进去)
    present_gt = {t.epc for t in tags if t.is_present}
    found_present, _ = algo.get_results()
    tp = len(found_present.intersection(present_gt))
    recall = tp / len(present_gt) if present_gt else 0
    
    # 6. 返回完整数据包
    # 我们将 Recall 和 BER 放进 stats 里，Tool.py 会自动识别并拆分为 raw_Recall.csv
    stats['Recall'] = recall 
    stats['BER_Percent'] = ber * 100 # 方便绘图 X 轴
    
    return {
        "status": "success",
        "stats": stats,
        "sim_config": {"TOTAL_TAGS": TAG_COUNT, "BER": ber},
        "algorithm_name": label,
        "run_id": run_id
    }

if __name__ == "__main__":
    # Windows 下多进程必须放在 if __name__ == "__main__": 下
    multiprocessing.freeze_support()
    
    # 1. 自动创建目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 已自动创建输出目录: {OUTPUT_DIR}")
        
    print(f"🚀 启动 Exp0_1: 误码压力测试 (BER Stress)")
    print(f"⚙️  配置: Workers={MAX_WORKERS}, Repeat={REPEAT}, BER_Levels={len(BER_LIST)}")
    
    # 初始化分析工具 (用于存储)
    analytics = SimulationAnalytics()
    
    # 2. 构建任务队列
    tasks = []
    for ber in BER_LIST:
        for r in range(REPEAT):
            # Ours
            tasks.append({'ber': ber, 'run_id': r, 'use_voting': True})
            # Baseline
            tasks.append({'ber': ber, 'run_id': r, 'use_voting': False})
            
    total_tasks = len(tasks)
    print(f"📋 总任务数: {total_tasks} (正在分发...)")

    # 3. 并行执行
    results_collected = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        futures = [executor.submit(run_task, t) for t in tasks]
        
        # 实时获取结果
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                results_collected += 1
                
                # 使用 Tool.py 的标准接口收集数据
                analytics.add_run_result(
                    result_stats=res['stats'],
                    sim_config=res['sim_config'],
                    algo_name=res['algorithm_name'],
                    run_id=res['run_id']
                )
                
                # 打印进度条
                progress = results_collected / total_tasks
                bar_len = 30
                filled = int(bar_len * progress)
                bar = '█' * filled + '-' * (bar_len - filled)
                print(f"\r[{bar}] {progress:.1%} | 已完成: {results_collected}/{total_tasks}", end="")
                
            except Exception as e:
                logger.error(f"❌ 任务失败: {e}")

    print("\n✅ 所有仿真任务完成。正在保存数据...")
    
    # 4. 自动拆分并保存为绘图友好格式
    # save_to_csv 会自动根据 Tool.py 的逻辑，将 Recall, Time 等指标
    # 拆分为 raw_Recall.csv, raw_total_time_us.csv 等
    # X 轴设为 'BER'，这样生成的 CSV 格式为：
    # BER, Ours (Voting), Baseline (Strict)
    # 0.0, 1.0, 1.0
    # ...
    analytics.save_to_csv(x_axis_key='BER', output_dir=OUTPUT_DIR)
    
    print(f"💾 数据已保存至: {OUTPUT_DIR}/")
    print(f"   (包含 raw_Recall.csv 等文件，可直接用于绘图)")