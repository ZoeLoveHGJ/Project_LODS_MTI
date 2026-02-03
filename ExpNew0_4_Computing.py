# -*- coding: utf-8 -*-
"""
Exp6_Computation_Overhead.py
实验 6: 计算开销验证 (无绘图版)
功能：执行原子延迟基准测试，并将结果保存为 CSV 数据文件。
"""

import time
import random
import os
import pandas as pd

# =========================================================
# ⚙️ 实验配置 (Configuration)
# =========================================================
OUTPUT_DIR = "Results_ExpNew0_4_Comuting"
DATA_FILENAME = "Computation_Overhead_Data.csv"

# X轴: 考察不同的分组大小 (Slice Size)
GROUP_SIZES = [4,8, 16, 32, 48, 64, 96, 128]

# 算法参数
CANDIDATE_COUNT = 16    # 算法实际搜索 16 个种子
STRESS_TEST_COUNT = 100 # 压力测试: 强制搜 100 个
COMPRESSION_RATIO = 1.0 # 最坏情况

# C++ 性能加速比估算
CPP_SPEEDUP_FACTOR = 20.0 

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================================
# 1. 核心算法微基准测试 (Micro-Benchmark)
# =========================================================

def benchmark_atomic_operation(k_size, candidate_count=16):
    """
    [Kernel] 模拟"单次指令前"的原子计算负载
    """
    # 1. 数据准备
    pending_ids = [random.getrandbits(96) for _ in range(k_size)]
    frame_len = k_size
    
    # --- 计时开始 ---
    start_t = time.perf_counter()
    
    # 模拟搜索循环 (算法热点)
    for seed in range(candidate_count):
        # A. 哈希映射
        slots = [(pid ^ seed) % frame_len for pid in pending_ids]
        # B. 冲突检测
        unique_slots = set(slots)
        
    end_t = time.perf_counter()
    # --- 计时结束 ---
    
    return (end_t - start_t) * 1000.0 # 返回 ms

def estimate_air_time(k_size):
    """
    估算物理层传输耗时 (Gen2 标准)
    """
    # 1. 下行链路 (Reader -> Tag)
    t_downlink = 0.3 
    
    # 2. 上行链路 (Tag -> Reader)
    # 估算总时隙数 (假设效率 ~36.8%)
    total_slots = k_size * 2.718
    avg_slot_duration = 0.5 # ms
    
    t_uplink = total_slots * avg_slot_duration
    
    return t_downlink + t_uplink

def run_benchmark_and_collect_data():
    """执行基准测试并收集数据"""
    print(f"{'='*80}")
    print(f"🚀 启动 Exp6: 原子延迟微基准测试 (Computation Overhead Benchmark)")
    print(f"   - Stress Test: {STRESS_TEST_COUNT} seeds / loop")
    print(f"   - Target Output: {os.path.join(OUTPUT_DIR, DATA_FILENAME)}")
    print(f"{'='*80}")
    
    results = {
        'K': [],
        'calc_py': [],
        'calc_cpp': [],
        'air_time': [],
        'overhead_pct': []
    }
    
    print(f"{'Group(K)':<10} | {'Py (ms)':<10} | {'C++ (ms)':<10} | {'Air (ms)':<10} | {'Overhead %':<10}")
    print("-" * 65)

    for k in GROUP_SIZES:
        # 1. 测量计算时间 (多次平均)
        timings = [benchmark_atomic_operation(k, STRESS_TEST_COUNT) for _ in range(20)]
        avg_calc_py = sum(timings) / len(timings)
        
        # 2. 归一化到实际算法 (16 seeds)
        real_algo_load_py = avg_calc_py * (CANDIDATE_COUNT / STRESS_TEST_COUNT)
        
        # 3. 推算 C++ 固件时间
        avg_calc_cpp = real_algo_load_py / CPP_SPEEDUP_FACTOR
        
        # 4. 估算物理传输时间
        est_air = estimate_air_time(k)
        
        # 5. 计算开销占比
        overhead = (avg_calc_cpp / est_air) * 100
        
        results['K'].append(k)
        results['calc_py'].append(real_algo_load_py)
        results['calc_cpp'].append(avg_calc_cpp)
        results['air_time'].append(est_air)
        results['overhead_pct'].append(overhead)
        
        print(f"{k:<10} | {real_algo_load_py:<10.3f} | {avg_calc_cpp:<10.4f} | {est_air:<10.2f} | {overhead:<10.4f}%")

    return results

# =========================================================
# 2. 主程序入口
# =========================================================

if __name__ == "__main__":
    # 运行实验
    data_dict = run_benchmark_and_collect_data()
    
    # 转换为 DataFrame 并保存
    df = pd.DataFrame(data_dict)
    save_path = os.path.join(OUTPUT_DIR, DATA_FILENAME)
    df.to_csv(save_path, index=False)
    
    print(f"\n✅ 数据已保存至: {save_path}")
    print(f"💡 提示: 请运行 'Exp6_Figure.py' 来读取此文件并生成图表。")