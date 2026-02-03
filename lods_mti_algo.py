# -*- coding: utf-8 -*-
"""
Improve_One_Algo.py (V9.0 - Tolerance Optimization)
基于“错误容忍度”的自适应逻辑，解决恢复期滞后问题。

【核心修改】
1. 废弃 round_is_perfect 布尔判定。
2. 引入 TOLERANCE_THRESHOLD (15%)。
   - 只有当本轮错误率 (Error Rate) > 15% 时，才维持 Rho=4。
   - 否则即使有少量错误，也激进切回 Rho=2，以提升恢复期响应速度。

   提出容忍度的概念，确保快速进入理想/非理想状态。
"""

import math
from typing import List, Tuple, Any, Set, Optional
from framework import AlgorithmInterface, ReaderCommand, SlotResult, Tag, PacketType

class LODS_MTI_Algorithm(AlgorithmInterface):
    """
    LODS 算法实现类 (V9.0 - Tolerance Aware)
    """
    def __init__(self, 
                 max_group_size: int = 128, 
                 target_rho: int = 4,       
                 is_adaptive: bool = True,
                 max_payload_bit: int = 256): # 最大负载 
        
        self.max_group_size = max_group_size
        self.is_adaptive = is_adaptive
        self.target_rho = target_rho
        self.max_payload_bit = max_payload_bit # <--- 保存参数

        # 初始密度设定：悲观启动
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
        # Phase 1: 验证与自适应 (Verification & Adaptation)
        # ======================================================================
        error_flag = False
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

            # 2. 逻辑判决 (引入计数器)
            last_rho = self.last_sent_context[0]['rho']
            vote_threshold = 3 if last_rho >= 4 else last_rho
            
            total_checks = 0
            error_cnt = 0 # 统计本轮的不完美点 (Missing 或 Bit翻转)
            
            for item in self.last_sent_context:
                epc_hex = item['epc']
                slot = item['slot']
                rho = item['rho']
                total_checks += 1
                
                start_bit = slot * rho
                expected_mask = ((1 << rho) - 1) << start_bit
                segment = received_bitmap & expected_mask
                match_count = bin(segment).count('1')
                
                if match_count >= vote_threshold:
                    self.verified_present.add(epc_hex)
                    # 虽然识别成功，但如果有坏点，计入 Error
                    if match_count < rho:
                        error_flag = True
                        error_cnt += 1
                else:
                    self.verified_missing.add(epc_hex)
                    # Missing 显然也是 Error
                    error_cnt += 1
            
            # 【核心修改】基于容忍度的自适应切换
            # TOLERANCE_THRESHOLD = 0.3 (允许 30% 的坏点)
            if self.is_adaptive and total_checks > 0:
                error_rate = error_cnt / total_checks
                # 如果错误率低于 30%，我们认为环境已经足够好了，切回高速
                # 这解决了 Recovery Phase 滞后的问题
                if error_rate <= 0.3:
                    self.current_rho = 2 
                else:
                    self.current_rho = 4 
            
            self.last_sent_context = []

        # ======================================================================
        # Phase 2: 终止检查
        # ======================================================================
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # ======================================================================
        # Phase 3: 调度与切片
        # ======================================================================
        active_rho = self.current_rho
        MAX_REPLY_BITS = self.max_payload_bit # <--- 使用参数
        if active_rho >= 4 and error_flag:
            MAX_REPLY_BITS = min(128, self.max_payload_bit)  # 强制减半！时长变短，漂移容忍度翻倍
        else:
            MAX_REPLY_BITS = self.max_payload_bit
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