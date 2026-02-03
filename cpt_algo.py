# -*- coding: utf-8 -*-
"""
cpt_algo.py
"""

import math
import hashlib
from collections import deque
from typing import List, Dict, Tuple, Set, Optional
from framework import (
    AlgorithmInterface,
    ReaderCommand,
    PacketType,
    SlotResult,
    Tag
)

class CPT_Node:
    """CPT树节点结构"""
    def __init__(self, tags: List[str], parent=None):
        self.tags = tags            
        self.bit_index = -1         
        self.left: Optional[CPT_Node] = None
        self.right: Optional[CPT_Node] = None
        self.parent = parent
        self.bit_value_from_parent = -1 

class CPT_Algorithm(AlgorithmInterface):
    def __init__(self, pseudo_id_len: int = 14):
        self.initial_pid_len = pseudo_id_len
        self.pseudo_ids: Dict[str, str] = {} 
        self.pid_length = 0
        self.leaves: List[CPT_Node] = []
        self.current_leaf_idx = 0
        self.last_leaf_node: Optional[CPT_Node] = None 
        self.finished = False  
        self.present_tags = set()
        self.all_expected_epcs = set()

    def initialize(self, expected_tags: List[Tag]):
        self.all_expected_epcs = {t.epc for t in expected_tags}
        self.present_tags.clear()
        self.finished = False
        self.current_leaf_idx = 0
        self.leaves = []
        self.last_leaf_node = None
        
        num_tags = len(expected_tags)
        
        # --- Step 1: Construct Pseudo-IDs [cite: 227-231] ---
        needed_len = max(self.initial_pid_len, 2 * math.ceil(math.log2(num_tags + 1)))
        
        while True:
            temp_pids = {}
            collision = False
            seen_pids = set()
            
            for tag in expected_tags:
                h_val = int(hashlib.md5(tag.epc.encode()).hexdigest(), 16)
                pid_bin = format(h_val, '0128b')[-needed_len:]
                if pid_bin in seen_pids:
                    collision = True
                    break
                seen_pids.add(pid_bin)
                temp_pids[tag.epc] = pid_bin
            
            if not collision:
                self.pseudo_ids = temp_pids
                self.pid_length = needed_len
                break
            else:
                needed_len += 1 
        
        # --- Step 2: Construct CPT [cite: 234-242] ---
        epc_list = [t.epc for t in expected_tags]
        root = CPT_Node(epc_list)
        self._build_tree_recursive(root)
        self._collect_leaves(root)

    def _build_tree_recursive(self, node: CPT_Node):
        if len(node.tags) <= 2:
            return 

        best_bit = -1
        min_diff = float('inf')
        
        for b in range(self.pid_length):
            count_0 = 0
            count_1 = 0
            for epc in node.tags:
                if self.pseudo_ids[epc][b] == '0':
                    count_0 += 1
                else:
                    count_1 += 1
            
            if count_0 > 0 and count_1 > 0:
                diff = abs(count_0 - count_1)
                if diff < min_diff:
                    min_diff = diff
                    best_bit = b
                if diff == 0: break 
        
        if best_bit == -1:
            return 

        node.bit_index = best_bit
        tags_0 = [epc for epc in node.tags if self.pseudo_ids[epc][best_bit] == '0']
        tags_1 = [epc for epc in node.tags if self.pseudo_ids[epc][best_bit] == '1']
        
        node.left = CPT_Node(tags_0, parent=node)
        node.left.bit_value_from_parent = 0
        node.right = CPT_Node(tags_1, parent=node)
        node.right.bit_value_from_parent = 1
        
        self._build_tree_recursive(node.left)
        self._build_tree_recursive(node.right)

    def _collect_leaves(self, node: CPT_Node):
        if node.left is None and node.right is None:
            self.leaves.append(node)
        else:
            if node.left: self._collect_leaves(node.left)
            if node.right: self._collect_leaves(node.right)

    def is_finished(self) -> bool:
        return self.finished

    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        if prev_result.status != PacketType.IDLE or prev_result.tag_ids:
             self._process_result(prev_result)

        if self.current_leaf_idx >= len(self.leaves):
            self.finished = True
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        target_leaf = self.leaves[self.current_leaf_idx]
        self.current_leaf_idx += 1
        
        constraints = []
        curr = target_leaf
        while curr.parent is not None:
            constraints.append((curr.parent.bit_index, curr.bit_value_from_parent))
            curr = curr.parent
        constraints.reverse() 
        
        payload_bits = 0
        if self.last_leaf_node is None:
            payload_bits = len(constraints) * math.ceil(math.log2(self.pid_length))
        else:
            payload_bits = 12 
        self.last_leaf_node = target_leaf

        current_constraints = constraints
        pids_ref = self.pseudo_ids

        def protocol_logic(tag: Tag) -> bool:
            if tag.epc not in pids_ref: return False
            my_pid = pids_ref[tag.epc]
            for bit_idx, expected_val in current_constraints:
                if int(my_pid[bit_idx]) != expected_val:
                    return False
            return True

        return ReaderCommand(
            payload_bits=max(10, payload_bits),
            expected_reply_bits=1,
            response_protocol=protocol_logic
        )

    def _process_result(self, result: SlotResult):
        """
        解析时隙结果 (Physics Aware Version)
        """
        # --- 关键修改：检查物理层噪声 ---
        # 如果 mask != 0，说明接收到的比特与实际发送的不符。
        # 在高可靠性要求下，任何误码都应导致丢包或解码失败。
        is_corrupted = (result.channel_noise_mask != 0)

        if result.status == PacketType.SUCCESS:
            # Singleton: 只有在未发生误码时才确认标签存在
            if not is_corrupted and result.resolved_data:
                self.present_tags.add(result.resolved_data[0])
            # 如果 is_corrupted 为 True，这部分数据被丢弃 (False Negative)，符合物理规律
                
        elif result.status == PacketType.COLLISION:
            # Manchester Decoding: 
            # 只有当信号干净（无误码）且冲突数量符合算法预期（<=2）时，才认为可解码 [cite: 78]
            if not is_corrupted:
                responding_tags = result.tag_ids 
                if responding_tags and len(responding_tags) <= 2:
                    for tag_epc in responding_tags:
                        self.present_tags.add(tag_epc)
            # 如果发生误码，曼彻斯特波形特征被破坏，无法区分是 2 个标签还是噪声，丢弃。

    def get_results(self):
        missing = self.all_expected_epcs - self.present_tags
        return self.present_tags, missing