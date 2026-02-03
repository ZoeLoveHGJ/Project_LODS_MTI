# -*- coding: utf-8 -*-
"""
Exp_Sup_5_Repair.py
【全独立修复版】补充实验五：容忍度恢复机理验证
内嵌了算法类，消除了文件依赖导致的 Crash 问题。
"""

import logging
import random
import os
import math 
import concurrent.futures
import multiprocessing
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
import traceback

# --- 导入基础框架 (确保 framework.py 在同级目录) ---
try:
    from framework import (
        run_high_fidelity_simulation, 
        SimulationConfig, 
        Tag, AlgorithmInterface, ReaderCommand, SlotResult, PacketType
    )
    from Tool import SimulationAnalytics
except ImportError:
    print("❌ 严重错误: 缺少 framework.py 或 Tool.py，请检查文件完整性。")
    exit(1)

# =========================================================
# 🛠️ 内嵌核心算法类 (LODS_MTI_Sensitivity)
# 避免因文件版本不一致导致的 AttributeError/TypeError
# =========================================================
class LODS_MTI_Sensitivity_Embedded(AlgorithmInterface):
    def __init__(self, 
                 max_group_size: int = 128, 
                 target_rho: int = 4,       
                 is_adaptive: bool = True,
                 max_payload_bit: int = 256,
                 tolerance_threshold: float = 0.30): # <--- 关键参数
        
        self.max_group_size = max_group_size
        self.is_adaptive = is_adaptive
        self.target_rho = target_rho
        self.max_payload_bit = max_payload_bit
        self.tolerance_threshold = tolerance_threshold 

        if self.is_adaptive:
            self.current_rho = 4 
        else:
            self.current_rho = target_rho
            
        self.sorted_tags_bin = []   
        self.total_tags = 0
        self.cursor = 0
        self.is_running = True
        self.last_sent_context = [] 
        self.verified_present = set()
        self.verified_missing = set()

    def initialize(self, expected_tags: List[Tag]):
        temp_list = []
        for t in expected_tags:
            b_str = bin(int(t.epc, 16))[2:].zfill(96)
            temp_list.append({'hex': t.epc, 'bin': b_str, 'int': t.epc_int})
        
        self.sorted_tags_bin = sorted(temp_list, key=lambda x: x['bin'])
        self.total_tags = len(self.sorted_tags_bin)
        self.cursor = 0
        self.is_running = True
        self.verified_present = set()
        self.verified_missing = set()
        self.last_sent_context = []
        
        if self.is_adaptive:
            self.current_rho = 4
        else:
            self.current_rho = self.target_rho

    def _get_lcp(self, str1: str, str2: str) -> str:
        l = min(len(str1), len(str2))
        for i in range(l):
            if str1[i] != str2[i]: return str1[:i]
        return str1[:l]

    def _find_dynamic_slice(self, start_idx: int, limit_k_override: int = None) -> Tuple[int, str]:
        remaining = self.total_tags - start_idx
        if remaining == 0: return 0, ""
        limit_k = min(self.max_group_size, remaining)
        if limit_k_override is not None: limit_k = min(limit_k, limit_k_override)
        
        if start_idx + limit_k >= self.total_tags:
            group_first = self.sorted_tags_bin[start_idx]['bin']
            group_last = self.sorted_tags_bin[start_idx + limit_k - 1]['bin']
            return limit_k, self._get_lcp(group_first, group_last)

        for k in range(limit_k, 0, -1):
            idx_last = start_idx + k - 1
            tag_first = self.sorted_tags_bin[start_idx]['bin']
            tag_last = self.sorted_tags_bin[idx_last]['bin']
            current_lcp = self._get_lcp(tag_first, tag_last)
            idx_outside = start_idx + k
            tag_outside = self.sorted_tags_bin[idx_outside]['bin']
            if tag_outside.startswith(current_lcp): continue 
            else: return k, current_lcp     
        return 1, self.sorted_tags_bin[start_idx]['bin']

    def _find_perfect_seed(self, epc_ints: List[int], mod_size: int) -> Optional[int]:
        for seed in range(16):
            slots = set()
            collision = False
            for val in epc_ints:
                s = (val ^ seed) % mod_size
                if s in slots:
                    collision = True
                    break
                slots.add(s)
            if not collision: return seed
        return None

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        error_flag = False
        
        # --- Phase 1: Verification ---
        if self.last_sent_context:
            ideal_bitmap = 0
            # 安全获取实际响应者 (防止 None)
            actual_responders = set(prev_result.tag_ids) if prev_result.tag_ids else set()

            for item in self.last_sent_context:
                if item['epc'] in actual_responders:
                    rho_used = item['rho']
                    start_bit = item['slot'] * rho_used
                    ideal_bitmap |= (((1 << rho_used) - 1) << start_bit)

            # 安全获取噪声掩码 (防止旧版 framework 报错)
            noise_mask = getattr(prev_result, 'channel_noise_mask', 0)
            received_bitmap = ideal_bitmap ^ noise_mask
            
            last_rho = self.last_sent_context[0]['rho']
            vote_threshold = 3 if last_rho >= 4 else last_rho
            total_checks = 0
            error_cnt = 0
            
            for item in self.last_sent_context:
                total_checks += 1
                rho = item['rho']
                start_bit = item['slot'] * rho
                expected_mask = ((1 << rho) - 1) << start_bit
                segment = received_bitmap & expected_mask
                match_count = bin(segment).count('1')
                
                if match_count >= vote_threshold:
                    self.verified_present.add(item['epc'])
                    if match_count < rho: 
                        error_flag = True
                        error_cnt += 1
                else:
                    self.verified_missing.add(item['epc'])
                    error_cnt += 1 # Missing 也算 Error
            
            # --- Adaptation Logic ---
            if self.is_adaptive and total_checks > 0:
                error_rate = error_cnt / total_checks
                if error_rate <= self.tolerance_threshold:
                    self.current_rho = 2 
                else:
                    self.current_rho = 4 
            
            self.last_sent_context = []

        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # --- Phase 2: Scheduling ---
        active_rho = self.current_rho
        MAX_REPLY_BITS = self.max_payload_bit
        if active_rho >= 4 and error_flag:
            MAX_REPLY_BITS = min(128, self.max_payload_bit)
        
        max_phys_k = max(1, MAX_REPLY_BITS // active_rho) # 防止除零
        current_limit_k = min(self.max_group_size, max_phys_k)
        current_limit_k = min(current_limit_k, self.total_tags - self.cursor)

        final_k = 0; final_mask = ""; final_seed = 0; final_reply_bits = 0; final_num_slots = 0
        
        # 种子搜索重试逻辑
        search_k = current_limit_k
        while search_k > 0:
            k, mask = self._find_dynamic_slice(self.cursor, limit_k_override=search_k)
            desired_len = k * active_rho
            reply_bits = max(4, min(desired_len, MAX_REPLY_BITS))
            num_logical_slots = max(1, reply_bits // active_rho)
            
            current_group_indices = range(self.cursor, self.cursor + k)
            epc_ints = [self.sorted_tags_bin[i]['int'] for i in current_group_indices]
            seed = self._find_perfect_seed(epc_ints, num_logical_slots)
            
            if seed is not None:
                final_k = k; final_mask = mask; final_seed = seed
                final_reply_bits = reply_bits; final_num_slots = num_logical_slots
                break
            else:
                search_k = k - 1 # 缩小范围重试
        
        # 兜底：如果搜索彻底失败 (极罕见)，强制只处理 1 个标签
        if final_k == 0:
            final_k = 1
            _, final_mask = self._find_dynamic_slice(self.cursor, limit_k_override=1)
            final_reply_bits = active_rho
            final_num_slots = 1
            final_seed = 0

        current_group = self.sorted_tags_bin[self.cursor : self.cursor + final_k]
        current_context = []
        for item in current_group:
            s = (item['int'] ^ final_seed) % final_num_slots
            current_context.append({'epc': item['hex'], 'slot': s, 'rho': active_rho})
        self.last_sent_context = current_context

        base_len = len(final_mask) + 8
        payload_cost = base_len + 5
        
        def protocol_logic(tag: Tag) -> bool:
            t_bin = bin(int(tag.epc, 16))[2:].zfill(96)
            return t_bin.startswith(final_mask)
            
        cmd = ReaderCommand(payload_bits=payload_cost, expected_reply_bits=final_reply_bits, response_protocol=protocol_logic)
        self.cursor += final_k
        return cmd

    def is_finished(self) -> bool: return not self.is_running
    def get_results(self): return self.verified_present, self.verified_missing

# =========================================================
# 🧪 实验主逻辑
# =========================================================
ROUNDS = 200
TAG_COUNT = 1000
OUTPUT_DIR = "Results_Exp_Sup_5_Tolerance_Recover"
MAX_WORKERS = max(1, os.cpu_count() - 2)

ALGO_CONFIGS = [
    {'name': 'LODS (eps=0.25)', 'eps': 0.25, 'adaptive': True},
    {'name': 'LODS (eps=0.30)', 'eps': 0.30, 'adaptive': True},
    {'name': 'LODS (eps=0.40)', 'eps': 0.40, 'adaptive': True},
    {'name': 'LODS (eps=0.60)', 'eps': 0.60, 'adaptive': True},
    {'name': 'Fixed-Robust',    'eps': 0.00, 'adaptive': False}
]

def get_env_params(round_idx):
    """环境剧本"""
    if round_idx < 40: return 0.0, 0.0
    elif round_idx >= 160: return 0.0, 0.0
    else:
        wave_duration = 120
        relative_idx = round_idx - 40
        phase = 2 * math.pi * relative_idx / wave_duration
        factor = (1 - math.cos(phase)) / 2 
        
        # 稍微降低峰值难度，确保数据连续性，便于观察趋势
        MAX_BER = 0.10        
        MAX_MISSING = 0.40    
        
        current_ber = MAX_BER * factor
        current_missing = MAX_MISSING * factor
        return current_ber, current_missing

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        algo_conf = task_params['algo_conf']
        round_idx = task_params['round_idx']
        
        ber, missing_rate = get_env_params(round_idx)
        
        tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
        rng = random.Random(2026 + round_idx)
        rng.shuffle(tags)
        
        num_missing = int(TAG_COUNT * missing_rate)
        for i in range(num_missing): tags[i].is_present = False
        
        # 使用内嵌类初始化
        algo = LODS_MTI_Sensitivity_Embedded(
            is_adaptive=algo_conf['adaptive'], 
            target_rho=4,
            tolerance_threshold=algo_conf['eps']
        )
            
        algo.initialize(tags)
        
        cfg = SimulationConfig(
            TOTAL_TAGS=TAG_COUNT, ENABLE_NOISE=True,
            packet_error_rate=0.0, BIT_ERROR_RATE=ber
        )
        
        stats = run_high_fidelity_simulation(algo, cfg, tags)
        
        present_gt = {t.epc for t in tags if t.is_present}
        found_present, _ = algo.get_results()
        tp = len(found_present.intersection(present_gt))
        recall = tp / len(present_gt) if present_gt else 1.0
        
        total_time_s = stats['total_time_us'] / 1e6
        goodput = tp / total_time_s if total_time_s > 0 else 0
        
        stats['Recall'] = recall
        stats['Goodput'] = goodput
        
        return {
            "status": "success", "stats": stats,
            "sim_config": {"Round": round_idx},
            "algorithm_name": algo_conf['name'], "run_id": round_idx 
        }
    except Exception as e:
        print(f"⚠️ [Task Error] Round {task_params['round_idx']} Failed: {e}")
        traceback.print_exc()
        return {"status": "error"}

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        
    print(f"🚀 启动 Exp_Sup_5_Repair (内嵌算法版)...")
    
    analytics = SimulationAnalytics()
    tasks = []
    for r in range(ROUNDS):
        for conf in ALGO_CONFIGS:
            tasks.append({'algo_conf': conf, 'round_idx': r, 'run_id': r})
            
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(run_task, t) for t in tasks]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            res = future.result()
            if res['status'] == 'success':
                analytics.add_run_result(res['stats'], res['sim_config'], res['algorithm_name'], res['run_id'])
            if i % 50 == 0: print(f"\r进度: {i}/{len(tasks)}", end="")

    print("\n✅ 仿真结束。保存数据...")
    analytics.save_to_csv(x_axis_key='Round', output_dir=OUTPUT_DIR)