# -*- coding: utf-8 -*-
"""
ISMTI_Algo.py
复现 2025 Elsevier Computer Networks: ISMTI
Reference: Chu Chu et al. "Efficient missing tag identification..."

【机制复现说明】
1. Bit-Tracking: 通过构建 EV (Expected Vector) 和 AV (Actual Vector) 进行位级比对。
2. Dynamic Frame: 基于估计的缺失率 q，查表(Table 1)获取最优 p2，动态调整帧长 f2。
3. Estimation: 利用 N11/N1 比例实时估计下一轮的 q (Eq. 23)。
4. High Fidelity PHY:
   - 不使用上帝视角 tag_ids 直接判断。
   - 而是重构物理波形 -> 叠加信道噪声 -> 解码为 AV。
   - 这确保了在 Noisy 环境下，算法会真实地产生 FP/FN，符合论文 Sec 6.5 的设定。
"""

import math
import hashlib
from typing import List, Set
from framework import (
    AlgorithmInterface,
    ReaderCommand,
    PacketType,
    SlotResult,
    Tag
)

class ISMTI_Algorithm(AlgorithmInterface):
    def __init__(self, initial_q: float = 0.5):
        self.initial_q_param = initial_q
        self.q = initial_q
        
        # 集合管理
        self.all_expected_epcs = set()
        self.unverified_tags = set()
        self.present_tags = set()
        self.missing_tags = set()
        
        # 运行时参数
        self.round_idx = 0
        self.f2 = 0         
        self.w = 96  # 论文固定物理时隙位宽 (Sec 6)
        self.seed = 0
        
        # 物理层控制
        self.current_physical_slot = 0
        self.total_physical_slots = 0
        
        # 向量存储 (Bit-Tracking 核心)
        self.EV = [] # Expected Vector based on Inventory
        self.AV = [] # Actual Vector based on PHY response
        
        self.is_completed = False

    def initialize(self, expected_tags: List[Tag]):
        self.all_expected_epcs = {t.epc for t in expected_tags}
        self.unverified_tags = self.all_expected_epcs.copy()
        self.present_tags.clear()
        self.missing_tags.clear()
        
        self.round_idx = 0
        self.is_completed = False
        self.q = self.initial_q_param
        
        # 启动第一轮
        self._start_new_round()

    def _start_new_round(self):
        """
        开始新一轮识别：
        1. 估算参数
        2. 构建 EV
        3. 重置 AV
        """
        num_unverified = len(self.unverified_tags)
        if num_unverified == 0:
            self.is_completed = True
            return

        # [Sec 5.2] Parameter Optimization
        # 根据当前估计的 q 查表获取最优 p2
        p2 = self._get_optimal_p2(self.q)
        
        # 计算虚拟帧长 f2 (vector length)
        # f2 = N_unverified / p2
        self.f2 = max(1, int(math.ceil(num_unverified / p2)))
        
        # 更新种子，保证每轮哈希独立
        self.seed = self.round_idx + 2025 
        
        # [Sec 5.1.1] 构建 EV (Expected Vector)
        # 0: Empty, 1: Singleton, 2: Collision (Multi-mapping)
        self.EV = [0] * self.f2
        temp_map = {} 
        for epc in self.unverified_tags:
            bit_idx = self._hash(epc, self.seed, self.f2)
            temp_map[bit_idx] = temp_map.get(bit_idx, 0) + 1
            
        for b_idx, count in temp_map.items():
            if count == 1:
                self.EV[b_idx] = 1
            elif count > 1:
                self.EV[b_idx] = 2
        
        # 初始化 AV，等待物理层填充
        self.AV = [0] * self.f2
        
        # 将虚拟向量长度 f2 映射到物理时隙 (每个时隙承载 w=96 bits)
        self.current_physical_slot = 0
        self.total_physical_slots = math.ceil(self.f2 / self.w)
        
        self.round_idx += 1

    def _get_optimal_p2(self, q: float) -> float:
        """
        [Table 1] The optimal value of p2 based on missing rate q.
        忠实复现论文表格数据。
        """
        if q >= 0.95: return 20.0
        if q >= 0.90: return 10.0
        if q >= 0.85: return 6.64
        if q >= 0.80: return 4.90
        if q >= 0.75: return 3.78
        if q >= 0.70: return 2.98
        # 论文未给出 <0.7 的具体值，但根据 Eq.7 和低缺失率特性，
        # ISMTI 行为应退化为 SSMTI (p1 optimal ≈ 1.5)
        return 1.5

    def _hash(self, epc: str, seed: int, mod: int) -> int:
        """MD5 Hash mimicking standard EPC C1G2 primitives"""
        s = f"{epc}_{seed}"
        val = int(hashlib.md5(s.encode()).hexdigest(), 16)
        return val % mod

    def is_finished(self) -> bool:
        return self.is_completed

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # --- [Step 1] 处理上一时隙的物理信号 ---
        # 只要不是刚启动的 Dummy Result，都进行处理
        # 注意：即使 status=IDLE，也需要处理，因为 BER 可能导致本该有的信号变成了 IDLE
        if not (prev_result.status == PacketType.IDLE and not prev_result.tag_ids and prev_result.channel_noise_mask == 0):
             self._process_slot_result(prev_result)

        # --- [Step 2] 检查是否需要换轮 ---
        if self.current_physical_slot >= self.total_physical_slots:
            self._analyze_frame_and_update()
            
            if self.is_completed:
                # 发送结束指令
                return ReaderCommand(payload_bits=-1, expected_reply_bits=0)
            
            self._start_new_round()
        
        # --- [Step 3] 生成当前时隙指令 ---
        curr_seed = self.seed
        curr_f2 = self.f2
        curr_w = self.w
        curr_slot_idx = self.current_physical_slot
        
        # 计算 Payload (模拟通信开销)
        # 基础 Query 命令开销 (22 bits)
        payload = 22
        
        # [Sec 5.1.2] Reader broadcasts indicator vector V2.
        # V2 长度为 f2。通常在轮次交替时发送。
        # 这里我们将 V2 的开销计入每一轮的第一个时隙。
        # 第一轮不需要发送 V2 (因为还没有历史信息)。
        if curr_slot_idx == 0 and self.round_idx > 1:
            payload += self.f2 

        # 定义标签响应逻辑 (运行在 Framework 内部)
        # 只有 "未被验证" 的标签才参与
        def protocol_logic(tag: Tag) -> bool:
            if tag.epc not in self.unverified_tags:
                return False
            # [Sec 5.1.1] Tag computes actual slot index i and bit index j
            h = self._hash(tag.epc, curr_seed, curr_f2)
            slot = h // curr_w
            return slot == curr_slot_idx

        self.current_physical_slot += 1
        
        return ReaderCommand(
            payload_bits=payload,
            expected_reply_bits=self.w, # 期望收到 96bit 字符串
            response_protocol=protocol_logic
        )

    def _process_slot_result(self, result: SlotResult):
        """
        [PHY Layer] Bit-Tracking & Noise Injection
        """
        # 计算刚才那个时隙对应的逻辑索引
        slot_idx = self.current_physical_slot - 1
        
        # 1. 重构理想物理波形 (Ideal Waveform Reconstruction)
        # 利用框架提供的 Ground Truth (result.tag_ids)
        ideal_response_int = 0
        if result.tag_ids:
            for epc in result.tag_ids:
                h = self._hash(epc, self.seed, self.f2)
                # 再次确认该标签是否属于当前时隙 (防御性编程)
                if (h // self.w) == slot_idx:
                    bit_pos = h % self.w
                    ideal_response_int |= (1 << bit_pos)
        
        # 2. 注入信道噪声 (Apply BER)
        # 这里的 noise_mask 来自 framework，1 表示发生了比特翻转
        noise_mask = getattr(result, 'channel_noise_mask', 0)
        observed_int = ideal_response_int ^ noise_mask
        
        # 3. 更新 AV (Bit-Tracking)
        # 仅基于 observed_int 更新，这体现了算法对噪声的"无知"
        for i in range(self.w):
            if (observed_int >> i) & 1:
                global_idx = slot_idx * self.w + i
                if global_idx < self.f2:
                    self.AV[global_idx] = 1

    def _analyze_frame_and_update(self):
        """
        [Sec 5.1.2] Missing Tag Identification Phase
        对比 EV 和 AV，应用规则 i-iv，并更新缺失率估计。
        """
        N_1 = 0   # 期望单标签映射的比特数 (EV=1)
        N_11 = 0  # 实际观测到的单标签比特数 (EV=1 & AV=1)
        verified_in_this_round = set()
        
        for epc in list(self.unverified_tags):
            h = self._hash(epc, self.seed, self.f2)
            
            ev_val = self.EV[h]
            av_val = self.AV[h]
            is_verified = False
            
            # [Rule ii] EV=2, AV=0 -> Missing
            # 意味着本该有多个标签回复，结果全空 -> 全部缺失
            if ev_val == 2 and av_val == 0:
                self.missing_tags.add(epc)
                is_verified = True
                
            # [Rule iii] EV=1 -> Determined
            # 期望只有一个标签回复
            elif ev_val == 1:
                if av_val == 1:
                    # AV=1 -> Present
                    self.present_tags.add(epc)
                    N_11 += 1 
                else:
                    # AV=0 -> Missing
                    # (注意：如果是 Noisy 环境，这里可能误判)
                    self.missing_tags.add(epc)
                N_1 += 1 
                is_verified = True
            
            # [Rule iv] EV=2, AV=1 -> Undetermined
            # 期望多个，实际有回复。无法确定具体是谁在场，谁缺失，或者都缺失。
            # do nothing, keep in unverified_tags

            if is_verified:
                verified_in_this_round.add(epc)

        # 移除本轮已验证的标签
        self.unverified_tags -= verified_in_this_round
        
        # [Eq. 23 & 24] Update Missing Rate Estimation
        # q_hat = 1 - (N11 / N1)
        if N_1 > 0:
            ratio = N_11 / N_1
            # 限制在 [0, 1] 范围内
            self.q = max(0.0, min(1.0, 1.0 - ratio))
        else:
            # 如果本轮没有 singleton slots，保留上一轮 q 或设为 0
            self.q = 0.0

    def get_results(self):
        return self.present_tags, self.missing_tags