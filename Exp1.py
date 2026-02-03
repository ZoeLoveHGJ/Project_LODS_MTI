# -*- coding: utf-8 -*-
"""
Exp1_Efficiency_Parallel.py
实验1：系统效率与可扩展性测试 (多进程并行加速版 - Fixed)

【修复日志】
1. [Fix] 增加 Task Shuffling，解决尾部任务过重导致的进度条“卡死”假象。
2. [Fix] 移除子进程内部 print，避免多进程管道阻塞 (Pipe Blocking)。
3. [Opt] 优化进度估算算法，提供更准确的剩余时间预测。
"""

import time
import logging
import random
import os
import concurrent.futures
import multiprocessing
from typing import List, Dict, Any

# --- 导入核心组件 ---
from framework import (
    run_high_fidelity_simulation, 
    SimulationConfig, 
    Tag
)
from Algorithm_Config import ALGORITHM_LIBRARY, ALGORITHMS_TO_TEST
from Tool import SimulationAnalytics

# --- 实验配置 ---
TAG_COUNTS = range(1000, 10001, 1000)  # [100, 150, ... 1000]
FIXED_MISSING_RATE = 0.5             # 10% 缺失率
REPEAT_TIMES = 5                   # 每个点重复 20 次
# 自动计算 worker 数量，保留 2 个核心给系统响应
MAX_WORKERS = max(1, os.cpu_count() - 2) 
OUTPUT_DIR = "Results_Exp1_Parallel_Test"

# 日志配置 (仅主进程打印)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("Exp1_Main")
# 屏蔽底层详细日志，防止刷屏
logging.getLogger('framework').setLevel(logging.WARNING)

def generate_standard_scenario(total_tags: int, missing_rate: float, run_seed: int) -> List[Tag]:
    """
    生成标准测试场景 (确定性生成)
    保证每个算法在相同的 run_seed 下面对的是完全一样的标签集合
    """
    tags = []
    num_missing = int(total_tags * missing_rate)
    # 固定 Base ID
    base_id_int = 0xE200001D4500000000000000
    
    for i in range(total_tags):
        epc_int = base_id_int + i
        epc_hex = format(epc_int, '024X')
        tags.append(Tag(epc=epc_hex, is_present=True))
        
    # 使用独立随机源，确保线程安全且可复现
    rng = random.Random(run_seed) 
    rng.shuffle(tags)
    for i in range(num_missing):
        tags[i].is_present = False
        
    return tags

def single_experiment_task(task_params: Dict) -> Dict:
    """
    【Worker 进程函数】
    注意：此处严禁使用 print()，所有结果/错误必须通过 return 返回。
    """
    n_tags = task_params['n_tags']
    run_idx = task_params['run_idx']
    algo_names = task_params['algo_names']
    
    # 结果容器
    output = {
        'results': [],
        'errors': []
    }
    
    try:
        # 1. 生成场景 (本地计算，减少跨进程通信开销)
        scenario_tags = generate_standard_scenario(n_tags, FIXED_MISSING_RATE, run_seed=run_idx)
        
        for algo_name in algo_names:
            if algo_name not in ALGORITHM_LIBRARY:
                continue
                
            try:
                # A. 实例化配置
                algo_conf = ALGORITHM_LIBRARY[algo_name]
                algo_class = algo_conf['class']
                algo_params = algo_conf.get('params', {})
                
                # B. 配置仿真环境 (Exp1 通常为理想环境，无噪声)
                sim_config = SimulationConfig(
                    TOTAL_TAGS=n_tags,
                    MISSING_RATE=FIXED_MISSING_RATE,
                    ENABLE_ENERGY_TRACKING=True,
                    ENABLE_NOISE=False  # Exp1 侧重效率，通常关闭噪声
                )
                
                # C. 初始化算法
                # 必须每次重新实例化，清除内部状态
                algo_instance = algo_class(**algo_params)
                algo_instance.initialize(scenario_tags)
                
                # D. 运行仿真
                start_cpu = time.time()
                stats = run_high_fidelity_simulation(algo_instance, sim_config, scenario_tags)
                cpu_duration = time.time() - start_cpu
                
                # E. 记录成功结果
                output['results'].append({
                    'algorithm_name': algo_name,
                    'run_id': run_idx,
                    'sim_config': {'TOTAL_TAGS': n_tags, 'MISSING_RATE': FIXED_MISSING_RATE},
                    'stats': stats,
                    '_meta': {'cpu_time': cpu_duration}
                })
                
            except Exception as e:
                # 捕获单个算法的崩溃，不影响该 Batch 中其他算法
                output['errors'].append(f"Algo '{algo_name}' failed at N={n_tags}: {str(e)}")

    except Exception as e:
        # 捕获场景生成等严重错误
        output['errors'].append(f"Critical Batch Error at N={n_tags}: {str(e)}")
        
    return output

def run_parallel_experiment():
    # 0. 准备统计工具
    analytics = SimulationAnalytics()
    
    print(f"\n{'='*60}")
    print(f"🚀 启动 Exp1: 效率与可扩展性测试 (Parallel Optimized)")
    print(f"{'='*60}")
    print(f"⚙️  CPU资源: {os.cpu_count()} 核心 | 激活 Worker: {MAX_WORKERS}")
    print(f"🎯 算法列表: {ALGORITHMS_TO_TEST}")
    print(f"📊 标签梯度: {len(TAG_COUNTS)} 组 (Max N={max(TAG_COUNTS)})")
    print(f"🔄 重复次数: {REPEAT_TIMES}")
    print(f"{'='*60}\n")

    # 1. 构建任务池
    tasks = []
    for n_tags in TAG_COUNTS:
        for run_idx in range(REPEAT_TIMES):
            tasks.append({
                'n_tags': n_tags,
                'run_idx': run_idx,
                'algo_names': ALGORITHMS_TO_TEST
            })

    # [核心修复 1] 打散任务顺序！
    # 解决“长尾效应”：避免最后剩下的全是大规模(N=1000)的重型任务导致看起来像死机。
    random.shuffle(tasks)
    
    total_tasks = len(tasks)
    completed_count = 0
    start_time = time.time()
    
    print(f"⏳ 已生成 {total_tasks} 个子任务，正在分发至进程池 (Random Order)...")

    # 2. 并行执行
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交任务
        future_to_task = {executor.submit(single_experiment_task, t): t for t in tasks}
        
        # 异步获取结果
        for future in concurrent.futures.as_completed(future_to_task):
            task_info = future_to_task[future]
            completed_count += 1
            
            try:
                # 获取 Worker 返回的字典
                data = future.result()
                
                # 处理错误日志 (在主进程打印)
                if data['errors']:
                    for err in data['errors']:
                        logger.error(f"❌ {err}")
                
                # 处理正常数据
                for record in data['results']:
                    analytics.add_run_result(
                        result_stats=record['stats'],
                        sim_config=record['sim_config'],
                        algo_name=record['algorithm_name'],
                        run_id=record['run_id']
                    )
                
                # 进度条显示
                elapsed = time.time() - start_time
                avg_time_per_task = elapsed / completed_count
                remaining_time = avg_time_per_task * (total_tasks - completed_count)
                
                # 动态进度条格式
                progress_percent = (completed_count / total_tasks) * 100
                bar_len = 30
                filled_len = int(bar_len * completed_count // total_tasks)
                bar = '█' * filled_len + '-' * (bar_len - filled_len)
                
                print(f"\r[{bar}] {progress_percent:5.1f}% | "
                      f"N={task_info['n_tags']} Done | "
                      f"ETA: {remaining_time:.0f}s ", end="", flush=True)

            except Exception as exc:
                logger.error(f"\n❌ System Error processing task {task_info}: {exc}")

    print(f"\n\n✅ 实验结束! 总耗时: {time.time() - start_time:.1f}s")

    # 3. 导出数据与绘图
    print(f"💾 正在保存数据至 {OUTPUT_DIR}...")
    analytics.save_to_csv(x_axis_key='TOTAL_TAGS', output_dir=OUTPUT_DIR)
    
    try:
        print("📈 正在绘制图表...")
        analytics.plot_results(
            x_axis_key='TOTAL_TAGS',
            algorithm_library=ALGORITHM_LIBRARY,
            save_path=f"{OUTPUT_DIR}/Exp1_Parallel_Summary.png"
        )
        print(f"🎉 任务全部完成。")
    except Exception as e:
        logger.error(f"⚠️ 绘图模块报错 (检查 Matplotli1b 环境): {e}")

if __name__ == "__main__":
    # Windows 必须保留此保护块
    multiprocessing.freeze_support()
    run_parallel_experiment()