# -*- coding: utf-8 -*-
"""
lods_mti_bit_fly_algo.py (V10.0 - Bit-Level Resilience)
LODS-MTI 算法的物理层增强版，用于验证抗比特擦除和时序抖动的能力。

【特性】
1. 声明 supports_phy_impairments = True，接收框架透传的物理损伤数据。
2. 在逻辑层精确模拟物理信号的 "Bit Slip" 和 "Burst Erasure"。
"""

import math
from typing import List, Tuple, Any, Set, Optional
from framework import AlgorithmInterface, ReaderCommand, SlotResult, Tag, PacketType

class LODS_MTI_BitFly_Algorithm(AlgorithmInterface):
    """
    LODS-MTI 算法 (Bit-Fly / Impairment Aware Version)
    """
    
    # [关键] 声明支持物理层损伤透传
    # 告诉框架：即使发生擦除或移位，也不要直接报 IDLE，而是通过 extra_info 给我数据
    supports_phy_impairments = True

    def __init__(self, 
                 max_group_size: int = 128, 
                 target_rho: int = 4,       
                 is_adaptive: bool = True,
                 max_payload_bit: int = 256):
        
        self.max_group_size = max_group_size
        self.is_adaptive = is_adaptive
        self.target_rho = target_rho
        self.max_payload_bit = max_payload_bit

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
        
        if self.is_adaptive:
            self.current_rho = 4
        else:
            self.current_rho = self.target_rho

    # ... (辅助函数 _get_lcp 和 _find_dynamic_slice 保持不变，省略以节省篇幅) ...
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
        # Phase 1: 验证与自适应 (含物理损伤模拟)
        # ======================================================================
        error_flag = False
        if self.last_sent_context:
            
            # 1. 基础重构：计算理想的无噪声信号
            ideal_superimposed_bitmap = 0
            # 注意：即使 prev_result.status 看起来像 IDLE，只要有 extra_info，我们也要尝试解码
            if prev_result.status == PacketType.IDLE and prev_result.extra_info is None:
                actual_responders_set = set()
            else:
                actual_responders_set = set(prev_result.tag_ids)

            for item in self.last_sent_context:
                if item['epc'] in actual_responders_set:
                    rho_used = item['rho']
                    start_bit = item['slot'] * rho_used
                    pattern = ((1 << rho_used) - 1) << start_bit
                    ideal_superimposed_bitmap |= pattern
            
            # 2. [核心增强] 注入微观物理损伤 (Micro-Physical Impairments)
            corrupted_signal = ideal_superimposed_bitmap
            
            # 从 SlotResult 获取透传数据
            impairments = getattr(prev_result, 'extra_info', None)
            
            if impairments:
                # A. 时序滑移 (Jitter / Bit Slip)
                # 物理含义：采样点滞后，导致数据整体左移 (假设高位是时间轴后端)
                # 这里的位操作方向取决于具体的端序定义，通常左移模拟数据“晚到了”
                shift_amt = impairments.get('shift', 0)
                if shift_amt > 0:
                    corrupted_signal = corrupted_signal << shift_amt
                
                # B. 突发擦除 (Burst Erasure)
                # 物理含义：Deep Fade 导致一段区间的能量归零
                erasure_mask = impairments.get('erasure', 0)
                if erasure_mask > 0:
                    # 使用按位与非 (AND NOT) 来清除被擦除的位
                    # 注意 Python 整数是无限长的，取反需要小心掩码宽度
                    # 这里利用 Python 的特性，erasure_mask 只有特定位是1，直接取反会变成 ...1111000111...
                    corrupted_signal = corrupted_signal & (~erasure_mask)

            # 3. 叠加随机信道噪声 (最后一步)
            received_bitmap = corrupted_signal ^ prev_result.channel_noise_mask

            # 4. 逻辑判决 (保持原有的多数投票逻辑)
            last_rho = self.last_sent_context[0]['rho']
            vote_threshold = 3 if last_rho >= 4 else last_rho
            
            total_checks = 0
            error_cnt = 0 
            
            for item in self.last_sent_context:
                epc_hex = item['epc']
                slot = item['slot']
                rho = item['rho']
                total_checks += 1
                
                start_bit = slot * rho
                expected_mask = ((1 << rho) - 1) << start_bit
                segment = received_bitmap & expected_mask
                match_count = bin(segment).count('1')
                
                # 投票判决：即使经历了移位和擦除，只要剩下的 '1' 够多，依然判定存在
                if match_count >= vote_threshold:
                    self.verified_present.add(epc_hex)
                    if match_count < rho:
                        error_flag = True
                        error_cnt += 1
                else:
                    self.verified_missing.add(epc_hex)
                    error_cnt += 1
            
            # 自适应逻辑
            if self.is_adaptive and total_checks > 0:
                error_rate = error_cnt / total_checks
                if error_rate <= 0.3:
                    self.current_rho = 2 
                else:
                    self.current_rho = 4 
            
            self.last_sent_context = []

        # ======================================================================
        # Phase 2 & 3: 调度逻辑 (保持不变)
        # ======================================================================
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        active_rho = self.current_rho
        MAX_REPLY_BITS = self.max_payload_bit
        if active_rho >= 4 and error_flag:
            MAX_REPLY_BITS = min(128, self.max_payload_bit)
        else:
            MAX_REPLY_BITS = self.max_payload_bit
        
        # ... (后续切片和 Hash 逻辑与原版完全一致) ...
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