# -*- coding: utf-8 -*-
import hashlib
from typing import List, Set, Dict, Tuple
from framework import (
    AlgorithmInterface,
    ReaderCommand,
    PacketType,
    SlotResult,
    Tag
)

class ECUMI_Algorithm(AlgorithmInterface):
    """
    ECUMI
    """
    
    def __init__(self, rho: float = 1.0):
        self.rho = rho
        self.x_prime = 10  # Optimal x' value from Section 5.2.1
        
        self.unverified_tags = set()  # N_rem
        self.present_tags = set()
        self.missing_tags = set()
        
        self.frame_index = 0
        self.current_frame_size = 0
        self.current_seed = 0
        self.indicator_vector = [] 
        
        self.slot_counter = 0
        self.is_frame_start = True
        
        self.slot_expected_map = {}

    def initialize(self, expected_tags: List[Tag]):
        self.unverified_tags = {t.epc for t in expected_tags}
        self.present_tags.clear()
        self.missing_tags.clear()
        self.frame_index = 0
        self.is_frame_start = True

    def is_finished(self) -> bool:
        return len(self.unverified_tags) == 0

    def get_results(self):
        return self.present_tags, self.missing_tags

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # Phase 3: Identification (处理上一时隙结果)
        if not self.is_frame_start and self.slot_counter > 0:
            prev_slot_idx = self.slot_counter - 1
            if self.indicator_vector[prev_slot_idx] == 1:
                self._process_identification(prev_result, prev_slot_idx)

        # 帧状态机
        if self.is_frame_start:
            return self._start_new_frame()

        if self.slot_counter < self.current_frame_size:
            return self._execute_next_slot()
        else:
            self.is_frame_start = True
            return self.get_next_command(prev_result)

    def _start_new_frame(self) -> ReaderCommand:
        n_rem = len(self.unverified_tags)
        
        # Section 5.2.2: Optimal frame size f' = 0.2341 * N
        self.current_frame_size = max(1, int(0.2341 * n_rem))
        
        self.current_seed = self.frame_index + 2024
        self.frame_index += 1
        
        self.indicator_vector = [0] * self.current_frame_size
        self.slot_expected_map = {}
        
        # Phase 2: Unfolding Logic
        temp_slots = {}
        
        for epc in self.unverified_tags:
            s_idx = self._hash_slot(epc, self.current_seed, self.current_frame_size)
            b_pos = self._hash_bit(epc, self.current_seed, self.x_prime)
            
            if s_idx not in temp_slots:
                temp_slots[s_idx] = []
            temp_slots[s_idx].append((epc, b_pos))
            
        # 判定 Usable Slot: 比特位置必须唯一 (无碰撞)
        for s_idx, mappings in temp_slots.items():
            bit_positions = [m[1] for m in mappings]
            if len(set(bit_positions)) == len(bit_positions):
                self.indicator_vector[s_idx] = 1
                self.slot_expected_map[s_idx] = {m[0]: m[1] for m in mappings}
            else:
                self.indicator_vector[s_idx] = 0 
        
        self.slot_counter = 0
        self.is_frame_start = False
        
        return ReaderCommand(
            payload_bits=self.current_frame_size,
            expected_reply_bits=0,
            response_protocol=lambda t: False
        )

    def _execute_next_slot(self) -> ReaderCommand:
        current_s = self.slot_counter
        is_usable = (self.indicator_vector[current_s] == 1)
        
        s_idx = current_s
        seed = self.current_seed
        f_size = self.current_frame_size
        
        # --- 关键修正：注入 Unverified 状态检查 ---
        # Python 闭包特性：这里引用的 self 是动态的，
        # 能够实时访问到最新的 self.unverified_tags
        def protocol_logic(tag: Tag) -> bool:
            # [Fix] 模拟灭活机制：
            # 如果标签不在 unverified_tags 中（即已被识别为 Present 或 Missing），
            # 它必须保持静默，绝对不能响应，否则会污染可用槽的信号。
            if tag.epc not in self.unverified_tags:
                return False
                
            my_slot = self._hash_slot(tag.epc, seed, f_size)
            return (my_slot == s_idx) and is_usable

        reply_bits = self.x_prime if is_usable else 0
        self.slot_counter += 1
        
        return ReaderCommand(
            payload_bits=0,
            expected_reply_bits=reply_bits,
            response_protocol=protocol_logic
        )

    def _process_identification(self, result: SlotResult, slot_idx: int):
        expected_map = self.slot_expected_map.get(slot_idx, {})
        if not expected_map:
            return

        # 1. 构建 Actual Signal (仅基于未灭活的标签响应)
        actual_signal_int = 0
        for epc in result.tag_ids:
            # 这里的 epc 肯定是 unverified 的，因为 protocol_logic 做了过滤
            b_pos = self._hash_bit(epc, self.current_seed, self.x_prime)
            actual_signal_int |= (1 << b_pos)
            
        # 2. 注入信道噪声
        received_signal_int = actual_signal_int ^ result.channel_noise_mask
        
        # 3. 验证期望标签
        processed_epcs = []
        for epc, expected_bit_pos in expected_map.items():
            received_bit = (received_signal_int >> expected_bit_pos) & 1
            
            # 逻辑判定
            if received_bit == 1:
                self.present_tags.add(epc)
                processed_epcs.append(epc)
            else:
                self.missing_tags.add(epc)
                processed_epcs.append(epc)
                
        # 立即移除已处理标签 -> 实现 Instant Inactivation
        for epc in processed_epcs:
            if epc in self.unverified_tags:
                self.unverified_tags.remove(epc)

    def _hash_slot(self, epc: str, seed: int, frame_size: int) -> int:
        key = f"{epc}-{seed}"
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return h % frame_size

    def _hash_bit(self, epc: str, seed: int, x_len: int) -> int:
        key = f"{epc}-{seed}-BIT"
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return h % x_len