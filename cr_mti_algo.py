# -*- coding: utf-8 -*-
"""
cr_mti_algo.py
"""

import math
import hashlib
from typing import List, Dict, Set, Tuple
from framework import (
    AlgorithmInterface,
    ReaderCommand,
    PacketType,
    SlotResult,
    Tag
)

class CR_MTI_Algorithm(AlgorithmInterface):
    def __init__(self, lambda_factor: float = 15.0, w_len: int = 34):
        """
        :param lambda_factor: 负载因子 (Tags per Slot)
        :param w_len: CRS 位图长度
        """
        self.lambda_factor = lambda_factor
        self.w_len = w_len
        
        # 结果集
        self.all_expected_epcs = set()
        # 核心逻辑变更：present_tags 初始包含所有，随着发现 missing 逐步减少
        self.present_tags = set() 
        self.missing_tags = set()
        
        # 迭代控制
        self.round_index = 0
        self.max_rounds = 15      # 最大轮次防止死循环
        self.stable_threshold = 3 # 连续多少轮没有新发现则停止
        self.consecutive_no_new_missing = 0
        
        # 当前帧参数
        self.frame_size = 0
        self.seed = 0
        self.current_slot_index = 0
        
        # 预计算缓存
        self.slot_map: Dict[int, List[str]] = {}
        
        self.is_completed = False

    def initialize(self, expected_tags: List[Tag]):
        self.all_expected_epcs = {t.epc for t in expected_tags}
        
        # 初始状态：假设所有标签都在场 (Innocent until proven Guilty)
        self.present_tags = self.all_expected_epcs.copy()
        self.missing_tags = set()
        
        self.is_completed = False
        self.round_index = 0
        self.consecutive_no_new_missing = 0
        
        # 启动第一轮
        self._start_new_round()

    def _start_new_round(self):
        """配置新的一轮扫描"""
        # CR-MTI 是全网扫描，每一轮针对所有尚未确认为 Missing 的标签？
        # 或者针对所有 Expected 标签？
        # 为了应对 Masking，必须让在场标签也参与（因为是它们遮挡了缺失标签）。
        # 所以每一轮都是针对 all_expected_epcs (或者至少是 present_tags)。
        # 为了简化和最大化暴露率，我们让所有 Expected Tags 参与哈希计算。
        
        num_tags = len(self.all_expected_epcs)
        if num_tags == 0:
            self.is_completed = True
            return

        # 1. 计算帧长
        self.frame_size = max(1, int(math.ceil(num_tags / self.lambda_factor)))
        
        # 2. 更新种子 (关键：每轮不同)
        self.seed = 2023 + self.round_index * 131
        self.current_slot_index = 0
        
        # 3. 预计算本轮映射 (Expected Mapping)
        self.slot_map = {}
        # 只有目前认为 "Present" 的标签参与 Expected 构建吗？
        # 不，物理上所有在场标签都会发。逻辑上我们检查所有 Expected。
        # 只要 Expected 里的标签映射到位=0，它就是 Missing。
        for epc in self.all_expected_epcs:
            # 优化：已经确认为 Missing 的标签其实不需要再检查了，
            # 但为了逻辑简单且防止 Ghost 导致的状态跳变，全量检查是安全的。
            # 不过为了性能，我们可以只检查 unverified。
            # 这里保持全量检查以符合 "Collision Resolving" 的全局观。
            slot = self._hash_slot(epc, self.seed, self.frame_size)
            if slot not in self.slot_map:
                self.slot_map[slot] = []
            self.slot_map[slot].append(epc)
            
        self.round_index += 1

    def is_finished(self) -> bool:
        return self.is_completed

    def get_results(self):
        return self.present_tags, self.missing_tags

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # --- 1. 处理结果 ---
        # 排除 Frame Start 的 Dummy Result
        is_dummy = (prev_result.status == PacketType.IDLE and 
                    not prev_result.tag_ids and 
                    prev_result.channel_noise_mask == 0 and 
                    self.current_slot_index == 0)
        
        if not is_dummy:
             self._process_result(prev_result, self.current_slot_index - 1)

        # --- 2. 检查帧/轮次结束 ---
        if self.current_slot_index >= self.frame_size:
            # 本轮结束，检查是否收敛
            if self._check_convergence():
                self.is_completed = True
                return ReaderCommand(payload_bits=-1, expected_reply_bits=0)
            else:
                # 开启新一轮
                self._start_new_round()
                # 递归调用自己以生成新一轮的第一个命令
                # 但为了防止递归深度问题，这里让它流转下去，只是 current_slot_index 归零了
        
        # --- 3. 发送指令 ---
        curr_seed = self.seed
        curr_f = self.frame_size
        curr_slot = self.current_slot_index
        target_ref = self.all_expected_epcs # 所有预期标签都应响应

        def protocol_logic(tag: Tag) -> bool:
            if tag.epc not in target_ref: return False
            s = self._hash_slot(tag.epc, curr_seed, curr_f)
            return s == curr_slot

        self.current_slot_index += 1
        
        return ReaderCommand(
            payload_bits=32, 
            expected_reply_bits=self.w_len,
            response_protocol=protocol_logic
        )

    def _process_result(self, result: SlotResult, processed_slot_idx: int):
        if processed_slot_idx < 0: return

        # 1. Expected
        expected_tags = self.slot_map.get(processed_slot_idx, [])
        if not expected_tags: return

        expected_bit_map: Dict[int, List[str]] = {}
        for epc in expected_tags:
            b_idx = self._hash_crs(epc, self.seed, self.w_len)
            if b_idx not in expected_bit_map: expected_bit_map[b_idx] = []
            expected_bit_map[b_idx].append(epc)

        # 2. Observed
        ideal_crs = 0
        if result.tag_ids:
            for epc in result.tag_ids:
                if self._hash_slot(epc, self.seed, self.frame_size) == processed_slot_idx:
                    b = self._hash_crs(epc, self.seed, self.w_len)
                    ideal_crs |= (1 << b)
        
        noise = getattr(result, 'channel_noise_mask', 0)
        if noise is None: noise = 0
        observed_crs = ideal_crs ^ (noise & ((1 << self.w_len) - 1))

        # 3. Verification (Negative Affirmation)
        # 我们只寻找 "Missing" 的证据 (Bit=0)
        new_missing_found = False
        for b_idx, mapped_epcs in expected_bit_map.items():
            observed_bit = (observed_crs >> b_idx) & 1
            
            if observed_bit == 0:
                # 证据确凿：这一位是0，说明映射到这里的所有标签都不在
                for epc in mapped_epcs:
                    if epc not in self.missing_tags:
                        self.missing_tags.add(epc)
                        if epc in self.present_tags:
                            self.present_tags.remove(epc)
                        new_missing_found = True
            # else: observed_bit == 1
            # 不能证明 Present，因为可能是被遮挡的。保持原状。

        if new_missing_found:
            self.has_new_missing_this_round = True

    def _check_convergence(self) -> bool:
        """检查是否满足停止条件"""
        # 如果本轮发现了新的缺失标签，重置计数器
        if getattr(self, 'has_new_missing_this_round', False):
            self.consecutive_no_new_missing = 0
        else:
            self.consecutive_no_new_missing += 1
        
        # 重置标志位供下一轮使用
        self.has_new_missing_this_round = False
        
        # 判定
        if self.consecutive_no_new_missing >= self.stable_threshold:
            return True
        if self.round_index >= self.max_rounds:
            return True
        return False

    def _hash_slot(self, epc: str, seed: int, mod: int) -> int:
        s = f"SLOT_{epc}_{seed}"
        val = int(hashlib.md5(s.encode()).hexdigest(), 16)
        return val % mod

    def _hash_crs(self, epc: str, seed: int, mod: int) -> int:
        s = f"CRS_{epc}_{seed}"
        val = int(hashlib.md5(s.encode()).hexdigest(), 16)
        return val % mod