# -*- coding: utf-8 -*-
"""
lods_mti_guard_time_algo.py
LODS-MTI 变体：物理间隙感知版 (Guard-Time Aware)

【设计目的】
仅用于 Experiment Tg_Sensitivity。
该类继承自标准 LODS_MTI_Algorithm，重写了 get_next_command。
它通过 ReaderCommand 的 meta-data 接口 (concatenated_tags_count)，
显式告知物理引擎当前批次的拼接数量，从而触发物理层的时域惩罚计算。
"""

from lods_mti_algo import LODS_MTI_Algorithm
from framework import ReaderCommand, SlotResult, PacketType

class LODS_MTI_Guard_Time_Algorithm(LODS_MTI_Algorithm):
    
    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand:
        # =================================================================
        # Phase 1: 逻辑状态更新 (完全复用父类逻辑，确保行为一致)
        # =================================================================
        # 由于 Python 对父类私有变量的处理机制，为了稳健性，这里完整展开逻辑
        # 确保 final_k 变量能被捕获用于后续传参
        
        # [代码块 A: 状态更新与自适应] ---------------------------------------
        error_flag = False
        if self.last_sent_context:
            ideal_superimposed_bitmap = 0
            # 处理 IDLE
            if prev_result.status == PacketType.IDLE:
                actual_responders_set = set()
            else:
                actual_responders_set = set(prev_result.tag_ids)

            # 重构理想波形
            for item in self.last_sent_context:
                if item['epc'] in actual_responders_set:
                    rho_used = item['rho']
                    start_bit = item['slot'] * rho_used
                    pattern = ((1 << rho_used) - 1) << start_bit
                    ideal_superimposed_bitmap |= pattern

            # 计算接收波形 (含物理层噪声)
            received_bitmap = ideal_superimposed_bitmap ^ prev_result.channel_noise_mask

            # 多数投票
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
            
            # 自适应切换逻辑
            if self.is_adaptive and total_checks > 0:
                error_rate = error_cnt / total_checks
                if error_rate <= 0.3: 
                    self.current_rho = 2 
                else:
                    self.current_rho = 4 
            
            self.last_sent_context = []
        # ------------------------------------------------------------------

        # [代码块 B: 终止检查]
        if self.cursor >= self.total_tags:
            self.is_running = False
            return ReaderCommand(payload_bits=-1, expected_reply_bits=0)

        # [代码块 C: 调度与切片]
        active_rho = self.current_rho
        MAX_REPLY_BITS = self.max_payload_bit
        # 错误恢复期降级
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
        
        # 寻找最优切片
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
        
        # 构建上下文
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

        # 计算开销
        base_len = len(final_mask) + 4 + 4
        crc_len = 5 if base_len < 32 else 16
        payload_cost = base_len + crc_len
        
        def protocol_logic(tag):
            t_bin = bin(int(tag.epc, 16))[2:].zfill(96)
            return t_bin.startswith(final_mask)

        # =================================================================
        # Phase 4: 指令生成 (Critical Change)
        # =================================================================
        # 在这里将 final_k 注入指令，这会触发 framework 中的:
        # Penalty = (final_k - 1) * GUARD_INTERVAL_BITS * T_bit
        
        cmd = ReaderCommand(
            payload_bits=payload_cost,
            expected_reply_bits=final_reply_bits,
            response_protocol=protocol_logic,
            concatenated_tags_count=final_k  # <--- 核心修改点
        )
        
        self.cursor += final_k
        return cmd