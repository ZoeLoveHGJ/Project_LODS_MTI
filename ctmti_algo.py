# -*- coding: utf-8 -*-
"""
ctmti_algo.py
"""

import math
import hashlib
from collections import deque
from typing import List, Dict, Set, Tuple, Optional
from framework import (
    AlgorithmInterface,
    ReaderCommand,
    PacketType,
    SlotResult,
    Tag
)

class CTMTI_Algorithm(AlgorithmInterface):
    def __init__(self, B: int = 4, alpha: float = 0.5):
        """
        :param B: 分叉数 (Branching Factor)，原文建议 2 或 4。
        :param alpha: 哈希参数 (用于模拟随机性)，本复现中使用 seed 变化代替。
        """
        self.B = B
        
        # 结果集
        self.all_expected_epcs = set()
        self.present_tags = set()
        self.missing_tags = set()
        
        # 任务栈
        # 每个元素是一个元组: (tag_epcs_in_this_node, current_seed)
        self.stack = deque()
        
        # 当前处理的任务状态
        self.current_group: List[str] = []
        self.current_seed = 0
        
        # 状态机控制
        self.is_completed = False
        self.waiting_for_response = False

    def initialize(self, expected_tags: List[Tag]):
        self.all_expected_epcs = {t.epc for t in expected_tags}
        self.present_tags.clear()
        self.missing_tags.clear()
        self.stack.clear()
        self.is_completed = False
        
        # 初始任务：根节点包含所有预期标签
        initial_list = list(self.all_expected_epcs)
        # 将其压入栈 (List, Seed)
        self.stack.append((initial_list, 0))
        self.waiting_for_response = False

    def is_finished(self) -> bool:
        return self.is_completed

    def get_results(self):
        return self.present_tags, self.missing_tags

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # --- 1. 处理上一时隙的响应 ---
        if self.waiting_for_response:
            # 只有非 Dummy 结果才处理
            # 注意：即使是 IDLE，也包含了重要的 "全0" 信息，必须处理
            if not (prev_result.status == PacketType.IDLE and not prev_result.tag_ids and prev_result.channel_noise_mask == 0 and not self.current_group):
                 self._process_result(prev_result)
            self.waiting_for_response = False

        # --- 2. 检查是否完成 ---
        if not self.stack:
            self.is_completed = True
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # --- 3. 准备下一个查询 (Pop Stack) ---
        # 弹出一个节点进行处理
        self.current_group, self.current_seed = self.stack.pop()
        
        # 优化：如果当前组已经被判定完了（例如在父节点逻辑中被过滤），跳过
        # 但在标准的 Tree Logic 中，压栈的通常是需要 Query 的。
        # 唯一的特例是：如果压栈时我们知道它只有一个标签，其实可以直接验证？
        # CTMTI 协议逻辑是：发送查询 -> 标签响应 -> 判决。
        # 所以即使只有 1 个预期标签，也要发一次 Query 来确认它是否真的在场。
        
        # 定义响应逻辑
        # 闭包捕获
        curr_seed = self.current_seed
        curr_B = self.B
        curr_group_set = set(self.current_group)

        def protocol_logic(tag: Tag) -> bool:
            # 只有属于当前子树节点的标签才响应
            if tag.epc not in curr_group_set:
                return False
            
            # 计算映射位置 (模拟 Collision Reconciling String 的作用)
            # 映射到 0 .. B-1
            # 响应逻辑：在对应的 Bit 位发送脉冲
            # 仿真框架只支持 "Is Responding", 具体的 Bit Pattern 由 _process_result 模拟
            return True

        self.waiting_for_response = True
        
        # Payload: 广播 Seed 和 Group 特征 (模拟 S_cr)
        # Reply: B bits (Bit-tracking)
        return ReaderCommand(
            payload_bits=20, 
            expected_reply_bits=self.B,
            response_protocol=protocol_logic
        )

    def _process_result(self, result: SlotResult):
        """
        核心逻辑：解析 Bit-Tracking 响应并进行树分裂
        """
        # 1. 重构物理层位图 (Ideal Bitmap)
        # 根据 tag_ids (Ground Truth) 计算如果不受噪声影响，阅读器应该收到什么
        ideal_bitmap = 0
        
        # 只有在 current_group 中的标签才会响应 (协议约束)
        # 但物理上，只要 Tag 认为自己符合条件就会发。
        # 仿真中 protocol_logic 已经做了筛选，所以 result.tag_ids 都是合法的。
        
        if result.tag_ids:
            for epc in result.tag_ids:
                # 计算该标签选择的分支
                h = self._hash(epc, self.current_seed, self.B)
                # 设置对应位
                ideal_bitmap |= (1 << h)
        
        # 2. 施加信道噪声 (Apply BER)
        # 获取噪声掩码
        noise_mask = getattr(result, 'channel_noise_mask', 0)
        if noise_mask is None: noise_mask = 0
        
        # 截断 noise_mask 只取前 B 位 (防止溢出)
        noise_mask &= ((1 << self.B) - 1)
        
        # 观测位图 = 理想 ^ 噪声
        observed_bitmap = ideal_bitmap ^ noise_mask
        
        # 3. 树分裂判决 (Tree Splitting Decision)
        # 我们需要将 current_group 中的预期标签，按同样的逻辑分配到 B 个桶中
        # 然后对比 Observed Bitmap
        
        expected_buckets = [[] for _ in range(self.B)]
        for epc in self.current_group:
            h = self._hash(epc, self.current_seed, self.B)
            expected_buckets[h].append(epc)
            
        # 遍历 B 个分支进行判决
        # 注意：栈是后进先出 (LIFO)，为了保持 B-ary 顺序，通常逆序压栈
        for i in range(self.B - 1, -1, -1):
            expected_count = len(expected_buckets[i])
            observed_bit = (observed_bitmap >> i) & 1
            
            if expected_count == 0:
                # 预期无标签
                if observed_bit == 1:
                    # Ghost Signal (噪声导致 0->1)
                    # CTMTI 算法根据 Expected Tree 运行，通常会忽略非预期的 Ghost 路径，
                    # 或者进入空转。这里忠实原文：如果收到信号但没预期，通常意味着“未知标签”，
                    # 但在 MTI 中我们只关心 Missing。所以忽略 Ghost。
                    pass
                else:
                    # Correctly Empty
                    pass
                    
            elif expected_count == 1:
                # 预期有 1 个标签 (Singleton)
                if observed_bit == 1:
                    # 信号确认 -> 标记为 Present
                    self.present_tags.add(expected_buckets[i][0])
                else:
                    # 信号丢失 (1->0) -> 标记为 Missing (FP)
                    # 这是 Noisy 环境下 FP 的来源
                    self.missing_tags.add(expected_buckets[i][0])
                    
            else: # expected_count > 1
                # 预期有冲突 (Collision)
                if observed_bit == 1:
                    # 收到信号 -> 需要进一步分裂
                    # 压入栈：(子集, 新种子)
                    # 新种子通常基于当前种子演化，避免死循环
                    new_seed = (self.current_seed * 1103515245 + 12345) & 0x7FFFFFFF
                    self.stack.append((expected_buckets[i], new_seed))
                else:
                    # 信号丢失 (1->0) -> 这一整组标签都被误判为 Missing
                    # 极其严重的 FP
                    for t in expected_buckets[i]:
                        self.missing_tags.add(t)

    def _hash(self, epc: str, seed: int, mod: int) -> int:
        """模拟 Collision Reconciling 的映射逻辑"""
        s = f"{epc}_{seed}"
        val = int(hashlib.md5(s.encode()).hexdigest(), 16)
        return val % mod