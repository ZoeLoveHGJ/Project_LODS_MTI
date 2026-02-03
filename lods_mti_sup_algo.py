# -*- coding: utf-8 -*-
"""
lods_mti_sup_algo.py
(Supplementary Algorithm for Stress Test - Fixed 128b Robust)

【用途说明】
这是一个 "LODS-MTI" 的特殊变体，专用于 "Clock Drift Tolerance" 压力测试。
它被剥夺了所有的 "自适应能力" (Non-Adaptive)，强制工作在：
1. Max Payload = 128 bits (短帧，物理层抗相位漂移能力最强)
2. Rho = 4 (高冗余，容忍比特翻转能力最强)

【实验预期】
这代表了算法的 "Lower Bound" (鲁棒性底线)。
- 吞吐量：较低 (因为 Rho=4 且帧短)。
- 稳定性：极高 (直到漂移率非常大时才会失效)。
"""

import math
from typing import List, Tuple, Any, Set, Optional
from framework import AlgorithmInterface, ReaderCommand, SlotResult, Tag, PacketType

class LODS_MTI_Sup_Algo(AlgorithmInterface):
    """
    LODS 压力测试专用版 (Fixed Payload=128, Rho=4)
    """
    def __init__(self, 
                 max_group_size: int = 128, # 此参数仅为兼容接口，实际上受限于 max_phys_k
                 target_rho: int = 4,       # 【关键修改】锁定为 4，追求极致稳定
                 is_adaptive: bool = False): # 强制关闭自适应
        
        # --- [Configuration: Robust Baseline] ---
        self.max_group_size = 128  
        self.is_adaptive = False   
        self.target_rho = 4        
        self.current_rho = 4       # 初始化并锁定为 4
            
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
            temp_list.append({
                'hex': t.epc,
                'bin': b_str,
                'int': t.epc_int
            })
        
        self.sorted_tags_bin = sorted(temp_list, key=lambda x: x['bin'])
        self.total_tags = len(self.sorted_tags_bin)
        self.cursor = 0
        self.is_running = True
        self.verified_present = set()
        self.verified_missing = set()
        self.last_sent_context = []
        
        # 再次确保重置时也是锁定的
        self.current_rho = 4

    def _get_lcp(self, str1: str, str2: str) -> str:
        l = min(len(str1), len(str2))
        for i in range(l):
            if str1[i] != str2[i]:
                return str1[:i]
        return str1[:l]

    def _find_dynamic_slice(self, start_idx: int, limit_k_override: int = None) -> Tuple[int, str]:
        remaining = self.total_tags - start_idx
        if remaining == 0: return 0, ""
        
        limit_k = min(self.max_group_size, remaining)
        if limit_k_override is not None:
            limit_k = min(limit_k, limit_k_override)
        
        if start_idx + limit_k >= self.total_tags:
            group_first = self.sorted_tags_bin[start_idx]['bin']
            group_last = self.sorted_tags_bin[start_idx + limit_k - 1]['bin']
            mask = self._get_lcp(group_first, group_last)
            return limit_k, mask

        for k in range(limit_k, 0, -1):
            idx_last = start_idx + k - 1
            tag_first = self.sorted_tags_bin[start_idx]['bin']
            tag_last = self.sorted_tags_bin[idx_last]['bin']
            current_lcp = self._get_lcp(tag_first, tag_last)
            idx_outside = start_idx + k
            tag_outside = self.sorted_tags_bin[idx_outside]['bin']
            if tag_outside.startswith(current_lcp):
                continue 
            else:
                return k, current_lcp     
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
            if not collision:
                return seed
        return None

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # ======================================================================
        # Phase 1: 验证 (Verification) - 【无自适应逻辑】
        # ======================================================================
        if self.last_sent_context:
            # 1. 重构物理信号
            ideal_superimposed_bitmap = 0
            if prev_result.status == PacketType.IDLE:
                actual_responders_set = set()
            else:
                actual_responders_set = set(prev_result.tag_ids)

            for item in self.last_sent_context:
                if item['epc'] in actual_responders_set:
                    rho_used = item['rho']
                    start_bit = item['slot'] * rho_used
                    pattern = ((1 << rho_used) - 1) << start_bit
                    ideal_superimposed_bitmap |= pattern

            received_bitmap = ideal_superimposed_bitmap ^ prev_result.channel_noise_mask

            # 2. 逻辑判决
            # 既然恒为 Rho=4，这里的 threshold 恒为 3
            vote_threshold = 3 
            
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
            
            # --- [No Adaptation] ---
            # 始终保持最稳状态
            self.current_rho = 4
            
            self.last_sent_context = []

        # ======================================================================
        # Phase 2: 终止检查
        # ======================================================================
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # ======================================================================
        # Phase 3: 调度与切片 - 【强制短帧 + 高冗余】
        # ======================================================================
        active_rho = self.current_rho # 恒为 4
        
        # 【关键修改】: 强制物理层最大 Bits 为 128
        # 这确保了在 Clock Drift 场景下，相移误差累积最小
        MAX_REPLY_BITS = 128
        
        # 计算单次最大标签数: 128 / 4 = 32 Tags
        max_phys_k = MAX_REPLY_BITS // active_rho 
        
        current_limit_k = min(self.max_group_size, max_phys_k)
        current_limit_k = min(current_limit_k, self.total_tags - self.cursor)

        final_k = 0
        final_mask = ""
        final_seed = 0
        final_reply_bits = 0
        final_num_slots = 0
        
        while current_limit_k > 0:
            k, mask = self._find_dynamic_slice(self.cursor, limit_k_override=current_limit_k)
            desired_len = k * active_rho
            # 限制在 [4, 128] 之间
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

    def is_finished(self) -> bool:
        return not self.is_running

    def get_results(self):
        return self.verified_present, self.verified_missing