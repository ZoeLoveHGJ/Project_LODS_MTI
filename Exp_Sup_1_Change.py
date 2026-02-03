# -*- coding: utf-8 -*-
"""
Exp_Sup_1_Change.py
变种实验：物理帧长对抗漂移能力的影响验证
目标：
1. 对比固定帧长为 128 bits 与 256 bits 时的抗漂移性能。
2. 验证物理公式 L * delta <= 0.5 的准确性。
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
    AlgorithmInterface
)
from lods_mti_algo import LODS_MTI_Algorithm

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Exp_Sup_1_Change")

# =========================================================
# 🛠️ 特制算法：强制固定 Payload
# =========================================================
class LODS_Fixed_Payload_Algo(LODS_MTI_Algorithm):
    """
    继承自 LODS_MTI，但强制重写调度逻辑，锁定 MAX_REPLY_BITS。
    """
    def __init__(self, fixed_payload_bits: int):
        # 初始化父类：关闭自适应，固定 rho=2
        super().__init__(is_adaptive=False, target_rho=2)
        self.fixed_payload_bits = fixed_payload_bits
        self.current_rho = 2 # 确保锁定

    # 重写 get_next_command 以注入强制 Payload 逻辑
    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # 复用父类的 Phase 1 (验证) 和 Phase 2 (终止)
        # 但我们需要拦截 Phase 3 (调度)
        
        # --- [Phase 1: Verification] ---
        # 直接复制父类逻辑太长，我们利用 Python 的 super() 调用机制
        # 但由于父类方法是一体的，我们必须完全重写这个方法来修改中间的变量
        # 为了代码简洁，我们这里只重写核心调度部分，前面的验证逻辑简化处理
        # (注：为了保证实验严谨性，这里完整保留父类的验证逻辑是必要的，
        #  但为节省篇幅，我直接拷贝并修改关键行)
        
        # ... (Verification Logic Same as LODS_MTI_Algorithm) ...
        # 由于无法简单 hook，我将在此完整重写该方法，
        # 确保除了 MAX_REPLY_BITS 外，其他行为与主算法一致。
        
        # === 1. 验证 (简写，直接调用内部状态更新，假设父类有 _update_state 方法更好，
        # 但这里我们手动处理验证，参考 lods_mti_algo.py) ===
        if self.last_sent_context:
            ideal_superimposed_bitmap = 0
            if prev_result.status != 0: # Not IDLE
                actual_responders_set = set(prev_result.tag_ids)
            else:
                actual_responders_set = set()

            for item in self.last_sent_context:
                if item['epc'] in actual_responders_set:
                    rho_used = item['rho']
                    start_bit = item['slot'] * rho_used
                    pattern = ((1 << rho_used) - 1) << start_bit
                    ideal_superimposed_bitmap |= pattern

            received_bitmap = ideal_superimposed_bitmap ^ prev_result.channel_noise_mask
            
            # 简单的投票验证
            last_rho = self.last_sent_context[0]['rho']
            vote_threshold = 3 if last_rho >= 4 else last_rho
            
            for item in self.last_sent_context:
                epc_hex = item['epc']
                slot = item['slot']
                rho = item['rho']
                start_bit = slot * rho
                expected_mask = ((1 << rho) - 1) << start_bit
                segment = received_bitmap & expected_mask
                match_count = bin(segment).count('1')
                
                if match_count >= vote_threshold:
                    self.verified_present.add(epc_hex)
                else:
                    self.verified_missing.add(epc_hex)
            
            self.last_sent_context = []

        # === 2. 终止检查 ===
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # === 3. 调度 (关键修改点!) ===
        active_rho = 2 # 强制固定
        
        # 【核心差异】: 强制使用传入的 payload bits
        MAX_REPLY_BITS = self.fixed_payload_bits 
        
        max_phys_k = MAX_REPLY_BITS // active_rho
        
        current_limit_k = min(self.max_group_size, max_phys_k)
        current_limit_k = min(current_limit_k, self.total_tags - self.cursor)

        # 下面切片逻辑与原算法一致
        final_k = 0
        final_mask = ""
        final_seed = 0
        final_reply_bits = 0
        final_num_slots = 0
        
        while current_limit_k > 0:
            k, mask = self._find_dynamic_slice(self.cursor, limit_k_override=current_limit_k)
            desired_len = k * active_rho
            # 确保不超过强制的 MAX_REPLY_BITS
            reply_bits = max(4, min(desired_len, MAX_REPLY_BITS)) 
            num_logical_slots = max(1, reply_bits // active_rho)
            
            current_group_indices = range(self.cursor, self.cursor + k)
            epc_ints = [self.sorted_tags_bin[i]['int'] for i in current_group_indices]
            seed = self._find_perfect_seed(epc_ints, num_logical_slots)
            
            if seed is not None:
                final_k = k
                final_mask = mask
                final_seed = seed
                final_reply_bits = reply_bits
                final_num_slots = num_logical_slots
                break
            else:
                current_limit_k = k - 1
        
        current_group = self.sorted_tags_bin[self.cursor : self.cursor + final_k]
        current_context = []
        for item in current_group:
            s = (item['int'] ^ final_seed) % final_num_slots
            current_context.append({
                'epc': item['hex'], 
                'slot': s, 
                'rho': active_rho 
            })
        self.last_sent_context = current_context

        base_len = len(final_mask) + 4 + 4
        crc_len = 5 if base_len < 32 else 16
        payload_cost = base_len + crc_len
        
        def protocol_logic(tag: Tag) -> bool:
            t_bin = bin(int(tag.epc, 16))[2:].zfill(96)
            return t_bin.startswith(final_mask)

        cmd = ReaderCommand(
            payload_bits=payload_cost,
            expected_reply_bits=final_reply_bits,
            response_protocol=protocol_logic
        )
        
        self.cursor += final_k
        return cmd


# =========================================================
# 🧪 实验配置
# =========================================================
TAG_COUNT = 1000
MISSING_RATE = 0.5 

# 细粒度漂移测试区间：0.0% -> 0.6%
# 重点关注 0.2% (256b 崩溃点) 和 0.4% (128b 崩溃点)
DRIFT_LIST = []
idx = 0.00
while idx <= 0.0061: 
    DRIFT_LIST.append(round(idx, 4))
    idx += 0.0005 # 高精度步长

REPEAT = 40
OUTPUT_DIR = "Results_Exp_Sup_1_Change"
MAX_WORKERS = max(1, os.cpu_count() - 2) 

def run_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    drift_rate = task_params['drift_rate']
    run_id = task_params['run_id']
    payload_setting = task_params['payload']
    
    # 1. 生成场景
    tags = [Tag(format(0xE2000000 + i, '024X')) for i in range(TAG_COUNT)]
    rng = random.Random(run_id) 
    rng.shuffle(tags)
    
    missing_count = int(TAG_COUNT * MISSING_RATE)
    for i in range(missing_count): 
        tags[i].is_present = False
    
    # 2. 实例化算法 (固定 Payload)
    algo = LODS_Fixed_Payload_Algo(fixed_payload_bits=payload_setting)
    algo.initialize(tags)
    
    # 3. 配置环境
    cfg = SimulationConfig(
        TOTAL_TAGS=TAG_COUNT,
        ENABLE_NOISE=True,
        packet_error_rate=0.0,
        BIT_ERROR_RATE=0.0,
        CLOCK_DRIFT_RATE=drift_rate 
    )
    
    # 4. 运行仿真
    stats = run_high_fidelity_simulation(algo, cfg, tags)
    
    # 5. 计算指标
    present_gt = {t.epc for t in tags if t.is_present}
    found_present, _ = algo.get_results()
    
    tp = len(found_present.intersection(present_gt))
    recall = tp / len(present_gt) if present_gt else 1.0
    
    stats['Recall'] = recall
    stats['Drift_Percent'] = drift_rate * 100
    
    return {
        "status": "success",
        "stats": stats,
        "payload_setting": payload_setting,
        "run_id": run_id
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"🚀 启动物理帧长抗漂移对比实验")
    print(f"   Payload A: 256 bits (Exp. Fail @ 0.2%)")
    print(f"   Payload B: 128 bits (Exp. Fail @ 0.4%)")
    
    tasks = []
    # 对比两组 Payload 设置
    target_payloads = [128, 256]
    
    for drift in DRIFT_LIST:
        for r in range(REPEAT):
            for p in target_payloads:
                tasks.append({
                    'drift_rate': drift, 
                    'run_id': r, 
                    'payload': p
                })
            
    print(f"📋 任务数: {len(tasks)}")
    
    results = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(run_task, t) for t in tasks]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                res = future.result()
                # 扁平化数据以便保存
                row = res['stats']
                row['Payload_Bits'] = res['payload_setting']
                row['Run_ID'] = res['run_id']
                results.append(row)
                
                if i % 50 == 0: print(f"\r进度: {i}/{len(tasks)}", end="")
            except Exception as e:
                logger.error(f"Error: {e}")

    # 保存数据
    df = pd.DataFrame(results)
    csv_path = os.path.join(OUTPUT_DIR, "Payload_Drift_Comparison.csv")
    df.to_csv(csv_path, index=False)
    print(f"\n✅ 完成。数据在 {csv_path}")