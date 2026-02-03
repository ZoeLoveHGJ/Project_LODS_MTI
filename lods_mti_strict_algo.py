# -*- coding: utf-8 -*-
"""
Improve_One_Strict_Algo.py
Improve_One (LODS) 的消融实验变体：去除投票机制的严格匹配版本。
用途：用于证明 Majority Voting 机制在噪声环境下的必要性。
"""

from typing import List, Tuple, Any, Optional
from framework import AlgorithmInterface, ReaderCommand, SlotResult, Tag, PacketType

class LODS_MTI_Strict_Algorithm(AlgorithmInterface):
    """
    [Ablation Study Version]
    逻辑与 Improve_One 完全一致，除了验证阶段：
    要求接收到的比特必须与期望波形 100% 匹配（无任何误码）才判定为 Present。
    """
    def __init__(self, 
                 max_group_size: int = 32, 
                 target_rho: int = 4,       
                 is_adaptive: bool = True): 
        
        self.max_group_size = max_group_size
        self.is_adaptive = is_adaptive
        self.target_rho = target_rho
        
        if self.is_adaptive:
            self.current_rho = 4 
        else:
            self.current_rho = target_rho
            
        self.perfect_streak = 0
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
        self.perfect_streak = 0
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
        # Phase 1: 验证 (Strict Verification)
        # ======================================================================
        if self.last_sent_context:
            # 1. 构建物理信号 (与原版一致)
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

            # 2. 注入噪声 (与原版一致)
            received_bitmap = ideal_superimposed_bitmap ^ prev_result.channel_noise_mask

            # 3. 严格判定逻辑 (Strict Logic Here!)
            round_is_perfect = True 
            
            for item in self.last_sent_context:
                epc_hex = item['epc']
                slot = item['slot']
                rho = item['rho']
                
                # 计算该标签期望的完美掩码 (全是1)
                start_bit = slot * rho
                expected_mask = ((1 << rho) - 1) << start_bit
                
                # 提取实际接收到的信号片段
                segment = received_bitmap & expected_mask
                
                # 【修改点】: 去除 count('1') >= threshold 的投票逻辑
                # 改为: 必须每一位都与期望掩码一致 (segment == expected_mask)
                # 这意味着只要有 1 bit 因为噪声翻转了，或者丢包了，就直接判定 Missing
                if segment == expected_mask:
                    self.verified_present.add(epc_hex)
                else:
                    self.verified_missing.add(epc_hex)
                    # 只要发生任何不匹配，就认为环境极其恶劣
                    round_is_perfect = False
            
            # 4. 自适应控制 (与原版一致，但这在严格模式下会迅速退化到高冗余)
            if self.is_adaptive:
                if round_is_perfect:
                    self.perfect_streak += 1
                    if self.perfect_streak >= 2:
                        self.current_rho = 2
                else:
                    self.current_rho = 4
                    self.perfect_streak = 0
            
            self.last_sent_context = []

        # ======================================================================
        # Phase 2 & 3: 调度逻辑 (保持完全一致)
        # ======================================================================
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        current_limit_k = min(self.max_group_size, self.total_tags - self.cursor)
        final_k = 0
        final_mask = ""
        final_seed = 0
        final_reply_bits = 0
        final_num_slots = 0
        active_rho = self.current_rho
        
        while current_limit_k > 0:
            k, mask = self._find_dynamic_slice(self.cursor, limit_k_override=current_limit_k)
            desired_len = k * active_rho
            reply_bits = max(4, min(desired_len, 96))
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

        base_len = 4 + len(final_mask) + 4 
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