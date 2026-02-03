# -*- coding: utf-8 -*-
"""
lods_mti_limit_algo.py (Hardware Feasibility Variant)
基于 LODS-MTI V9.0 修改

【实验目的】
验证硬件极简性：强制分组大小 K 必须为 2 的整数次方 (Power of 2)。
当 K = 2^n 时，标签端的取模运算 (Hash % K) 可退化为按位与操作 (Hash & (K-1))，
从而消除对除法器/取模器的硬件需求，验证算法在极低功耗硬件上的落地能力。

【核心修改】
重写 _find_dynamic_slice 方法：
- 搜索策略从 "线性递减" 改为 "按位右移"。
- 仅允许返回 128, 64, 32, 16, 8, 4, 2, 1 等值。
"""

import math
from typing import List, Tuple, Any, Set, Optional
from framework import AlgorithmInterface, ReaderCommand, SlotResult, Tag, PacketType

class LODS_MTI_LIMIT_Algorithm(AlgorithmInterface):
    """
    LODS 算法变体 - 强制 2^n 分组 (Hardware Friendly Version)
    """
    def __init__(self, 
                 max_group_size: int = 128, 
                 target_rho: int = 4,       
                 is_adaptive: bool = True,
                 max_payload_bit: int = 256): 
        
        self.max_group_size = max_group_size
        self.is_adaptive = is_adaptive
        self.target_rho = target_rho
        self.max_payload_bit = max_payload_bit

        # 初始密度设定
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
        """
        【修改版】只寻找 2 的幂次方的 K
        """
        remaining = self.total_tags - start_idx
        if remaining == 0: return 0, ""
        
        # 1. 确定上限
        limit_k = min(self.max_group_size, remaining)
        if limit_k_override is not None:
            limit_k = min(limit_k, limit_k_override)
            
        if limit_k < 1: return 0, ""

        # 2. 找到 <= limit_k 的最大 2 的幂次方 (例如 50 -> 32)
        # bit_length() 返回二进制位数， 1 << (len-1) 即为最大 2^n
        start_p2 = 1 << (limit_k.bit_length() - 1)
        
        # 3. 仅在 2 的幂次方中递减搜索 (32 -> 16 -> 8 -> ...)
        k = start_p2
        while k > 0:
            # 边界检查逻辑与原版一致：确保 mask 能区分 Group 内外
            if start_idx + k >= self.total_tags:
                # 已经是最后一组，直接返回
                group_first = self.sorted_tags_bin[start_idx]['bin']
                group_last = self.sorted_tags_bin[start_idx + k - 1]['bin']
                mask = self._get_lcp(group_first, group_last)
                return k, mask

            idx_last = start_idx + k - 1
            tag_first = self.sorted_tags_bin[start_idx]['bin']
            tag_last = self.sorted_tags_bin[idx_last]['bin']
            current_lcp = self._get_lcp(tag_first, tag_last)
            
            idx_outside = start_idx + k
            tag_outside = self.sorted_tags_bin[idx_outside]['bin']
            
            if tag_outside.startswith(current_lcp):
                # 当前 LCP 无法区分第 k+1 个标签，说明 k 太大了
                # 【修改点】直接右移一位，尝试下一个更小的 2 的幂次方
                k = k >> 1 
                continue 
            else:
                # 找到了合法的切片
                return k, current_lcp     
        
        # 兜底：k=1 总是 2 的幂次方 (2^0)
        return 1, self.sorted_tags_bin[start_idx]['bin']

    def _find_perfect_seed(self, epc_ints: List[int], mod_size: int) -> Optional[int]:
        # 寻找完美哈希种子
        for seed in range(16):
            slots = set()
            collision = False
            for val in epc_ints:
                # 这里的 mod_size 在 limit 版本中大概率也是 2^n
                # 这证明了硬件上无需除法器
                s = (val ^ seed) % mod_size
                if s in slots:
                    collision = True
                    break
                slots.add(s)
            if not collision:
                return seed
        return None

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # Phase 1: 验证与自适应 (Copy from V9.0)
        error_flag = False
        if self.last_sent_context:
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
                
                if match_count >= vote_threshold:
                    self.verified_present.add(epc_hex)
                    if match_count < rho:
                        error_flag = True
                        error_cnt += 1
                else:
                    self.verified_missing.add(epc_hex)
                    error_cnt += 1
            
            if self.is_adaptive and total_checks > 0:
                error_rate = error_cnt / total_checks
                if error_rate <= 0.3:
                    self.current_rho = 2 
                else:
                    self.current_rho = 4 
            
            self.last_sent_context = []

        # Phase 2: 终止检查
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # Phase 3: 调度与切片 (使用新的 _find_dynamic_slice)
        active_rho = self.current_rho
        MAX_REPLY_BITS = self.max_payload_bit
        if active_rho >= 4 and error_flag:
            MAX_REPLY_BITS = min(128, self.max_payload_bit)
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
            # 调用修改后的切片逻辑，保证 k 是 2^n
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
                # 如果当前 k 找不到种子，尝试更小的
                # 原版是 k-1，这里我们跳到下一个更小的 2 的幂次方
                # 但由于 _find_dynamic_slice 内部已经保证返回的是满足 LCP 的最大 2^n
                # 这里简单减 1 会导致下一轮循环重新计算出下一个 2^n
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