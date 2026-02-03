# -*- coding: utf-8 -*-
"""
baseline_algos.py
基准算法实现库。
包含：
1. StandardGen2QAlgo (标准 EPC C1G2 ALOHA)
2. StandardQueryTreeAlgo (标准查询树)
"""

from collections import deque
from typing import List, Set, Tuple
from framework import (
    AlgorithmInterface,
    ReaderCommand,
    PacketType,
    SlotResult,
    Tag,
    CONSTANTS
)

class StandardGen2QAlgo(AlgorithmInterface):
    """
    基准 1: EPC C1G2 标准 Q 算法 (Pure ALOHA)
    """
    def __init__(self, initial_q: float = 4.0):
        self.q_value = initial_q
        self.frame_size = round(2**self.q_value)
        self.slots_remaining = self.frame_size
        self.is_frame_start = True
        
        self.collision_count = 0
        self.idle_count = 0
        self.consecutive_idle_frames = 0 
        self.max_idle_frames_to_stop = 3 
        self.has_new_tag_this_frame = False

    def initialize(self, expected_tags: List[Tag]): 
        pass 

    def is_finished(self) -> bool:
        return self.consecutive_idle_frames >= self.max_idle_frames_to_stop

    def get_results(self):
        return set(), set() 

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        if prev_result:
            if prev_result.outcome == 'COLLISION':
                self.collision_count += 1
            elif prev_result.outcome == 'IDLE':
                self.idle_count += 1
            elif prev_result.outcome == 'SUCCESS':
                self.has_new_tag_this_frame = True
        
        if self.slots_remaining <= 0:
            c = 0.5
            if self.collision_count > 0:
                self.q_value = min(15.0, self.q_value + c)
            elif self.idle_count > 0:
                self.q_value = max(0.0, self.q_value - c)
            
            if not self.has_new_tag_this_frame and self.collision_count == 0:
                self.consecutive_idle_frames += 1
            else:
                self.consecutive_idle_frames = 0
            
            self.frame_size = round(2**self.q_value)
            if self.frame_size < 1: self.frame_size = 1
            self.slots_remaining = self.frame_size
            self.is_frame_start = True
            self.collision_count = 0
            self.idle_count = 0
            self.has_new_tag_this_frame = False

        self.slots_remaining -= 1
        
        if self.is_frame_start:
            self.is_frame_start = False
            return ReaderCommand(PacketType.QUERY, 22, data=("", self.q_value))
        else:
            return ReaderCommand(PacketType.QUERY_REP, 4, data=("", 0))


class StandardQueryTreeAlgo(AlgorithmInterface):
    """
    基准 2: 标准查询树 (Pure Deterministic)
    """
    def __init__(self):
        self.queue = deque(['']) 
        self.active_prefix = None
    
    def initialize(self, expected_tags: List[Tag]): pass 
    def is_finished(self) -> bool: return not self.queue and self.active_prefix is None
    def get_results(self): return set(), set()

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        if prev_result:
            if prev_result.outcome == 'COLLISION':
                self.queue.append(self.active_prefix + '0')
                self.queue.append(self.active_prefix + '1')
            self.active_prefix = None

        if not self.queue: return ReaderCommand(PacketType.SELECT, 0)

        self.active_prefix = self.queue.popleft()
        
        return ReaderCommand(
            cmd_type=PacketType.QUERY,
            payload_bits=22 + len(self.active_prefix),
            data=(self.active_prefix, 0)
        )