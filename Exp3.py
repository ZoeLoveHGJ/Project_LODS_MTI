# -*- coding: utf-8 -*-
"""
Exp3_Robustness_BER_Parallel.py
实验3：抗干扰鲁棒性测试 (BER Sensitivity Test) - 多进程并行版

【修改说明】
1. 新增 Goodput (有效吞吐率) 指标计算。
   公式: Goodput = (Total_Tags - FP - FN) / Time_in_Seconds
2. 保持原有 FP/FN/Reliability 计算逻辑不变。
"""

import time
import logging
import random
import os
import concurrent.futures
import multiprocessing
from typing import List, Dict, Any, Set, Tuple

# --- 导入核心组件 ---
from framework import (
    run_high_fidelity_simulation, 
    SimulationConfig, 
    Tag
)
from Algorithm_Config import ALGORITHM_LIBRARY, ALGORITHMS_TO_TEST
from Tool import SimulationAnalytics

# --- 实验配置 ---
# 1. 误码率测试范围
BER_RANGE = []
INDEX = 0.00
while INDEX <= 0.1:
    BER_RANGE.append(INDEX)
    INDEX += 0.005

# 2. 固定参数
FIXED_TOTAL_TAGS = 500      # 固定标签数量
FIXED_MISSING_RATE = 0.5    # 固定缺失率
REPEAT_TIMES = 40           # 重复次数

# 3. 系统配置
MAX_WORKERS = max(1, os.cpu_count() - 2) 
OUTPUT_DIR = "Results_Exp3_BER"

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("Exp3_Main")
logging.getLogger('framework').setLevel(logging.WARNING)

def generate_standard_scenario(total_tags: int, missing_rate: float, run_seed: int) -> List[Tag]:
    """生成标准测试场景 (确定性生成)"""
    tags = []
    num_missing = int(total_tags * missing_rate)
    base_id_int = 0xE200001D4500000000000000
    
    for i in range(total_tags):
        epc_int = base_id_int + i
        epc_hex = format(epc_int, '024X')
        tags.append(Tag(epc=epc_hex, is_present=True))
        
    rng = random.Random(run_seed) 
    rng.shuffle(tags)
    # 标记前 num_missing 个为缺失
    for i in range(num_missing):
        tags[i].is_present = False
        
    return tags

def calculate_accuracy_metrics(
    algo_instance: Any, 
    scenario_tags: List[Tag]
) -> Dict[str, float]:
    """
    【阅卷系统】计算 FP, FN, Reliability
    """
    # 1. 获取算法判定结果 (Predicted)
    pred_present, pred_missing = algo_instance.get_results()
    pred_present = set(pred_present)
    pred_missing = set(pred_missing)
    
    # 2. 获取真值 (Ground Truth)
    actual_present = {t.epc for t in scenario_tags if t.is_present}
    actual_missing = {t.epc for t in scenario_tags if not t.is_present}
    
    # 3. 计算指标
    # FP (False Positive): 算法误报缺失 (实际上在场)
    fp_set = pred_missing.intersection(actual_present)
    
    # FN (False Negative): 算法漏报缺失 (误判为在场)
    fn_set = pred_present.intersection(actual_missing)
    
    fp_count = len(fp_set)
    fn_count = len(fn_set)
    total_tags = len(scenario_tags)
    
    # 可靠性 (Reliability)
    reliability = 1.0 - ((fp_count + fn_count) / total_tags) if total_tags > 0 else 0.0
    
    return {
        'FP': float(fp_count),
        'FN': float(fn_count),
        'Reliability': reliability
    }

def single_experiment_task(task_params: Dict) -> Dict:
    """Worker 进程函数"""
    ber_value = task_params['ber']
    run_idx = task_params['run_idx']
    algo_names = task_params['algo_names']
    n_tags = task_params['n_tags'] 
    
    output = {
        'results': [],
        'errors': []
    }
    
    try:
        # 1. 生成场景
        scenario_tags = generate_standard_scenario(n_tags, FIXED_MISSING_RATE, run_seed=run_idx)
        
        for algo_name in algo_names:
            if algo_name not in ALGORITHM_LIBRARY:
                continue
                
            try:
                algo_conf = ALGORITHM_LIBRARY[algo_name]
                algo_class = algo_conf['class']
                algo_params = algo_conf.get('params', {})
                
                # B. 配置仿真环境 (开启噪声)
                sim_config = SimulationConfig(
                    TOTAL_TAGS=n_tags,
                    MISSING_RATE=FIXED_MISSING_RATE,
                    ENABLE_ENERGY_TRACKING=True,
                    ENABLE_NOISE=True,           
                    BIT_ERROR_RATE=ber_value     
                )
                
                # C. 初始化
                algo_instance = algo_class(**algo_params)
                algo_instance.initialize(scenario_tags)
                
                # D. 运行物理仿真 (获得开销指标)
                start_cpu = time.time()
                stats = run_high_fidelity_simulation(algo_instance, sim_config, scenario_tags)
                cpu_duration = time.time() - start_cpu
                
                # E. 【核心修复】阅卷环节 (获得准确率指标)
                accuracy_metrics = calculate_accuracy_metrics(algo_instance, scenario_tags)
                
                # --- [新增] 计算 Goodput ---
                time_s = stats['total_time_us'] / 1e6
                # 有效识别数 = 总数 - 错误数(FP+FN)
                n_errors = accuracy_metrics['FP'] + accuracy_metrics['FN']
                n_correct = n_tags - n_errors
                
                # Goodput (tags/s)
                goodput = n_correct / time_s if time_s > 0 else 0.0
                accuracy_metrics['Goodput'] = goodput
                # -------------------------
                
                # F. 合并指标
                full_stats = {**stats, **accuracy_metrics}
                
                # G. 记录
                output['results'].append({
                    'algorithm_name': algo_name,
                    'run_id': run_idx,
                    'sim_config': {
                        'TOTAL_TAGS': n_tags, 
                        'BIT_ERROR_RATE': ber_value, # X轴
                        'MISSING_RATE': FIXED_MISSING_RATE
                    },
                    'stats': full_stats, # 包含 Time, Slots, FP, FN, Goodput
                    '_meta': {'cpu_time': cpu_duration}
                })
                
            except Exception as e:
                output['errors'].append(f"Algo '{algo_name}' failed at BER={ber_value}: {str(e)}")

    except Exception as e:
        output['errors'].append(f"Critical Batch Error at BER={ber_value}: {str(e)}")
        
    return output

def run_parallel_experiment():
    analytics = SimulationAnalytics()
    
    print(f"\n{'='*60}")
    print(f"🚀 启动 Exp3: 鲁棒性测试 (Goodput/FP/FN vs BER)")
    print(f"{'='*60}")
    print(f"⚙️  CPU资源: {os.cpu_count()} 核心 | 激活 Worker: {MAX_WORKERS}")
    print(f"🎯 算法列表: {ALGORITHMS_TO_TEST}")
    print(f"📡 BER 梯度: {['{:.1e}'.format(b) for b in BER_RANGE]}")
    print(f"📌 固定参数: N={FIXED_TOTAL_TAGS}, Missing={FIXED_MISSING_RATE}")
    print(f"{'='*60}\n")

    # 1. 构建任务
    tasks = []
    for ber in BER_RANGE:
        for run_idx in range(REPEAT_TIMES):
            tasks.append({
                'ber': ber,
                'n_tags': FIXED_TOTAL_TAGS,
                'run_idx': run_idx,
                'algo_names': ALGORITHMS_TO_TEST
            })

    # 打散任务
    random.shuffle(tasks)
    
    total_tasks = len(tasks)
    completed_count = 0
    start_time = time.time()
    
    print(f"⏳ 已生成 {total_tasks} 个 BER 测试任务，正在并行执行...")

    # 2. 并行执行
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {executor.submit(single_experiment_task, t): t for t in tasks}
        
        for future in concurrent.futures.as_completed(future_to_task):
            task_info = future_to_task[future]
            completed_count += 1
            
            try:
                data = future.result()
                
                if data['errors']:
                    for err in data['errors']:
                        logger.error(f"❌ {err}")
                
                for record in data['results']:
                    analytics.add_run_result(
                        result_stats=record['stats'],
                        sim_config=record['sim_config'],
                        algo_name=record['algorithm_name'],
                        run_id=record['run_id']
                    )
                
                elapsed = time.time() - start_time
                progress = (completed_count / total_tasks) * 100
                bar_len = 30
                filled = int(bar_len * completed_count // total_tasks)
                bar = '█' * filled + '-' * (bar_len - filled)
                
                print(f"\r[{bar}] {progress:5.1f}% | "
                      f"BER={task_info['ber']:.1e} | "
                      f"ETA: {(elapsed/completed_count)*(total_tasks-completed_count):.0f}s ", 
                      end="", flush=True)

            except Exception as exc:
                logger.error(f"\n❌ System Error: {exc}")

    print(f"\n\n✅ 实验结束! 总耗时: {time.time() - start_time:.1f}s")

    # 3. 导出与绘图
    print(f"💾 数据处理中...")
    analytics.save_to_csv(x_axis_key='BIT_ERROR_RATE', output_dir=OUTPUT_DIR)
    
    try:
        print("📈 正在绘制图表...")
        analytics.plot_results(
            x_axis_key='BIT_ERROR_RATE', 
            algorithm_library=ALGORITHM_LIBRARY,
            save_path=f"{OUTPUT_DIR}/Exp3_Robustness_Summary.png"
        )
        print(f"🎉 结果已保存至 {OUTPUT_DIR}/")
    except Exception as e:
        logger.error(f"⚠️ 绘图失败: {e}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_parallel_experiment()