# -*- coding: utf-8 -*-
"""
Exp2_MissingRate_Parallel.py
实验 2: 宏观性能与缺失率的关系 (多进程并行版)
Macro-Performance vs. Missing Rate

【实验目标】
在固定标签总数 (N=1000) 下，测试不同算法在缺失率 (Pm) 从 0.1 到 0.96 变化时的表现。
这主要评估算法对“大规模缺失”场景的适应性（如：是否因缺失率高而导致时隙浪费，或反之）。

【适配说明】
1. 架构完全对齐 Exp1_Efficiency_Parallel.py。
2. 已适配 Framework V5.3 (移除 ALLOW_PARTIAL_RESPONSE)。
3. 增强了随机种子控制，确保对比公平性。
"""

import time
import logging
import random
import os
import concurrent.futures
from typing import List, Dict
import multiprocessing

# --- 导入核心组件 ---
from framework import (
    run_high_fidelity_simulation, 
    SimulationConfig, 
    Tag
)
from Algorithm_Config import ALGORITHM_LIBRARY, ALGORITHMS_TO_TEST
from Tool import SimulationAnalytics

# --- 实验配置 ---
FIXED_TOTAL_TAGS = 1000             # 控制变量: 固定标签总数
INDEX = 0.0
# MISSING_RATES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] # 自变量: 缺失率
MISSING_RATES = [] # 自变量: 缺失率
while INDEX <= 0.9001:
    MISSING_RATES.append(INDEX)
    INDEX += 0.05
REPEAT_TIMES = 40                  # 每个数据点重复次数
MAX_WORKERS = max(1, os.cpu_count() - 2) 
OUTPUT_DIR = "Results_Exp2_MissingRate"

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Exp2_Parallel")
logging.getLogger('framework').setLevel(logging.WARNING)

def generate_standard_scenario(total_tags: int, missing_rate: float, run_seed: int) -> List[Tag]:
    """
    生成标准测试场景 (确定性生成)
    """
    tags = []
    num_missing = int(total_tags * missing_rate)
    base_id_int = 0xE200001D4500000000000000
    
    # 1. 生成全量标签
    for i in range(total_tags):
        epc_int = base_id_int + i
        epc_hex = format(epc_int, '024X')
        tags.append(Tag(epc=epc_hex, is_present=True))
        
    # 2. 随机移除 (由 run_seed 决定)
    # 确保不同算法在同一轮次 (Run ID) 面对的是完全相同的缺失情况
    rng = random.Random(run_seed) 
    rng.shuffle(tags)
    for i in range(num_missing):
        tags[i].is_present = False
        
    return tags

def single_experiment_task(task_params: Dict) -> List[Dict]:
    """
    【子进程工作函数】
    负责：生成场景 -> 运行所有算法 -> 返回结果列表
    """
    n_tags = task_params['n_tags']
    missing_rate = task_params['missing_rate']
    run_idx = task_params['run_idx']
    algo_names = task_params['algo_names']
    
    # 1. 生成场景 (Local Generation)
    scenario_tags = generate_standard_scenario(n_tags, missing_rate, run_seed=run_idx)
    
    results_buffer = []

    for algo_name in algo_names:
        if algo_name not in ALGORITHM_LIBRARY:
            continue
            
        try:
            # A. 获取配置
            algo_conf = ALGORITHM_LIBRARY[algo_name]
            algo_class = algo_conf['class']
            algo_params = algo_conf.get('params', {})
            
            # B. 实例化 Config (Framework V5.3 标准)
            # [关键修改] 移除了 ALLOW_PARTIAL_RESPONSE
            sim_config = SimulationConfig(
                TOTAL_TAGS=n_tags,
                MISSING_RATE=missing_rate,
                ENABLE_ENERGY_TRACKING=True,
                ENABLE_NOISE=False # 宏观性能测试通常基于理想信道
            )
            
            # C. 初始化算法 (每次重新实例化)
            algo_instance = algo_class(**algo_params)
            algo_instance.initialize(scenario_tags)
            
            # D. 运行仿真
            start_cpu = time.time()
            stats = run_high_fidelity_simulation(algo_instance, sim_config, scenario_tags)
            cpu_time = time.time() - start_cpu
            
            # E. 打包结果
            record = {
                'algorithm_name': algo_name,
                'run_id': run_idx,
                # 注意：这里记录 MISSING_RATE 以便后续绘图作为 X 轴
                'sim_config': {'TOTAL_TAGS': n_tags, 'MISSING_RATE': missing_rate},
                'stats': stats,
                '_meta': {'cpu_time': cpu_time}
            }
            results_buffer.append(record)
            
        except Exception as e:
            # 捕获异常，防止进程池崩溃
            # 仅打印简略错误，避免日志刷屏
            print(f"⚠️ Worker Error [{algo_name} Pm={missing_rate}]: {e}")
            continue
            
    return results_buffer

def run_parallel_experiment():
    analytics = SimulationAnalytics()
    
    print(f"{'='*60}")
    print(f"🚀 启动实验 2: 宏观性能 vs. 缺失率 (Parallel)")
    print(f"⚙️  CPU 核心利用: {MAX_WORKERS} / {os.cpu_count()}")
    print(f"🎯 测试算法: {ALGORITHMS_TO_TEST}")
    print(f"📊 缺失率 (X轴): {MISSING_RATES}")
    print(f"🔒 固定标签数: {FIXED_TOTAL_TAGS} | 重复次数: {REPEAT_TIMES}")
    print(f"{'='*60}\n")

    # 1. 准备任务队列
    tasks = []
    for pm in MISSING_RATES:
        for run_idx in range(REPEAT_TIMES):
            tasks.append({
                'n_tags': FIXED_TOTAL_TAGS,
                'missing_rate': pm,
                'run_idx': run_idx,
                'algo_names': ALGORITHMS_TO_TEST
            })

    total_tasks = len(tasks)
    completed_tasks = 0
    start_time = time.time()

    # 2. 启动进程池
    print(f"⏳ 正在分发 {total_tasks} 个组合任务...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {executor.submit(single_experiment_task, t): t for t in tasks}
        
        for future in concurrent.futures.as_completed(future_to_task):
            task_info = future_to_task[future]
            completed_tasks += 1
            
            try:
                batch_results = future.result()
                
                # 汇总数据
                for res in batch_results:
                    analytics.add_run_result(
                        result_stats=res['stats'],
                        sim_config=res['sim_config'],
                        algo_name=res['algorithm_name'],
                        run_id=res['run_id']
                    )
                    
                # 进度显示
                elapsed = time.time() - start_time
                avg_time = elapsed / completed_tasks
                remaining = avg_time * (total_tasks - completed_tasks)
                
                # 动态进度条
                current_pm = task_info['missing_rate']
                print(f"\r[{completed_tasks}/{total_tasks}] "
                      f"Pm={current_pm:<4} Done. "
                      f"耗时: {elapsed:.0f}s (剩余: {remaining:.0f}s)", end="", flush=True)

            except Exception as exc:
                print(f"\n❌ 任务异常 {task_info}: {exc}")

    print("\n\n✅ 实验完成。正在导出数据...")

    # 3. 导出与绘图
    # 注意：X轴 Key 必须与 sim_config 中的键名一致
    analytics.save_to_csv(x_axis_key='MISSING_RATE', output_dir=OUTPUT_DIR)
    
    try:
        analytics.plot_results(
            x_axis_key='MISSING_RATE',
            algorithm_library=ALGORITHM_LIBRARY,
            save_path=f"{OUTPUT_DIR}/Exp2_MissingRate_Summary.png"
        )
        print(f"📈 图表已保存至 {OUTPUT_DIR}")
    except Exception as e:
        print(f"⚠️ 绘图失败: {e}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_parallel_experiment()