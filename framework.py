# -*- coding: utf-8 -*-
"""
framework.py
RFID 高保真仿真框架核心 (Universal Physics Kernel)

该模块提供了一个通用的 RFID 物理层仿真框架，支持多种信道损伤模拟，
包括噪声、位翻转、时钟漂移、突发擦除 (Burst Erasure) 以及时序抖动。
其核心逻辑实现了"物理-MAC"跨层交互，能够为不同的标签检测算法提供实时反馈。
"""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Any, Dict, Callable, Optional

# ==============================================================================
# 1. 基础数据结构
# ==============================================================================

class PacketType(Enum):
    """物理信号状态"""
    IDLE = auto()       # 寂静 / Preamble Detection Failed / CRC Error
    COLLISION = auto()  # 冲突
    SUCCESS = auto()    # 成功 (Success/Decodable)
    
    QUERY = auto()
    ACK = auto()

class Tag:
    def __init__(self, epc: str, is_present: bool = True):
        self.epc = epc
        self.epc_int = int(epc, 16)
        self.is_present = is_present
        self.rssi = random.uniform(-80, -40)

@dataclass
class ReaderCommand:
    """
    [射频指令]
    携带物理层参数 + 协议层逻辑
    """
    # 1. 物理层开销参数
    payload_bits: int        # 指令长度 (影响下行耗时)
    expected_reply_bits: int # 期望回复长度 (影响上行耗时 & 误码计算)
    
    # 2. 协议层逻辑注入
    response_protocol: Callable[['Tag'], bool] = field(default=lambda t: False)
    
    # 3. 辅助数据
    meta_data: Any = None 

    # 告诉物理层这次传输拼接了多少个标签
    concatenated_tags_count: int = 1
@dataclass
class SlotResult:
    """
    [时隙结果] 物理层返回给 MAC 层的事实
    """
    status: PacketType
    tag_ids: List[str]
    resolved_data: Any = None
    
    # 随机比特翻转掩码 (Random Bit Flip)
    channel_noise_mask: int = 0 
    
    # 扩展物理层信息，用于传递突发擦除 (Burst Erasure) 和时序偏移 (Jitter Offset)
    # 格式: {'erasure': int_mask, 'shift': int_offset}
    extra_info: Optional[Dict[str, Any]] = None

class SimulationConfig:
    """环境配置开关"""
    def __init__(self, 
                 TOTAL_TAGS=1000, 
                 MISSING_RATE=0.0, 
                 ENABLE_NOISE=False,          
                 packet_error_rate=0.0,       
                 BIT_ERROR_RATE=0.0,          
                 ENABLE_CAPTURE_EFFECT=False, 
                 CAPTURE_RATIO_DB=3.0,        
                 ENABLE_ENERGY_TRACKING=False,
                 CLOCK_DRIFT_RATE=0.0,
                 # 物理损伤参数
                 BURST_ERASURE_LEN=0,   # 突发擦除长度 (bits), 0表示关闭
                 JITTER_OFFSET=0,       # 时序采样偏移 (bits), 0表示关闭
                 # 物理保护间隔 (单位: 比特时长 T_bit)
                 GUARD_INTERVAL_BITS=0.0):    
        
        self.TOTAL_TAGS = TOTAL_TAGS
        self.MISSING_RATE = MISSING_RATE
        self.ENABLE_NOISE = ENABLE_NOISE
        self.packet_error_rate = packet_error_rate
        self.BIT_ERROR_RATE = BIT_ERROR_RATE
        self.ENABLE_CAPTURE_EFFECT = ENABLE_CAPTURE_EFFECT
        self.CAPTURE_RATIO_DB = CAPTURE_RATIO_DB
        self.ENABLE_ENERGY_TRACKING = ENABLE_ENERGY_TRACKING
        self.CLOCK_DRIFT_RATE = CLOCK_DRIFT_RATE
        self.GUARD_INTERVAL_BITS = GUARD_INTERVAL_BITS
        self.BURST_ERASURE_LEN = BURST_ERASURE_LEN
        self.JITTER_OFFSET = JITTER_OFFSET

class AlgorithmInterface:
    """算法必须实现的最小接口"""
    
    # 特性声明：如果算法类中设置此 flag 为 True，框架会将物理损伤数据透传给它，
    # 而不是直接判定为丢包。这允许算法尝试自行从受损信号中恢复数据。
    # 默认为 False，保证基准算法的行为符合标准 CRC 失败逻辑。
    supports_phy_impairments: bool = False

    def initialize(self, expected_tags: List[Tag]): 
        raise NotImplementedError
        
    def get_next_command(self, prev_result: SlotResult) -> ReaderCommand: 
        raise NotImplementedError
        
    def is_finished(self) -> bool: 
        raise NotImplementedError
        
    def get_results(self) -> Tuple[Any, Any]: 
        raise NotImplementedError

# ==============================================================================
# 2. 物理层常量
# ==============================================================================

CONSTANTS = {
    'T_PREAMBLE': 300.0,  
    'T1': 240.0,          
    'T2': 120.0,          
    'BLF': 40000,         
    'READER_RATE': 80000, 
    'P_TX_READER': 1.0,   
    'P_RX_READER': 0.2,   
    'P_TX_TAG': 100e-6,   
    'P_RX_TAG': 10e-6,    
    'MAX_SLOTS_LIMIT': 200000 
}

# ==============================================================================
# 3. 核心仿真引擎
# ==============================================================================

def run_high_fidelity_simulation(algorithm: AlgorithmInterface, 
                                 config: SimulationConfig, 
                                 true_tags: List[Tag]) -> Dict:
    
    total_time_us = 0.0
    total_reader_energy_j = 0.0
    total_tag_energy_j = 0.0
    total_slots = 0
    collision_slots = 0
    success_slots = 0
    idle_slots = 0
    
    present_tags = [t for t in true_tags if t.is_present]
    present_tags_count = len(present_tags)
    rssi_map = {t.epc: t.rssi for t in present_tags}
    
    prev_result = SlotResult(PacketType.IDLE, [])

    while not algorithm.is_finished():
        if total_slots > CONSTANTS['MAX_SLOTS_LIMIT']:
            print(f"⚠️ [Framework] 熔断: 超过 {CONSTANTS['MAX_SLOTS_LIMIT']} 时隙。")
            break

        # A. [MAC] 获取指令
        cmd = algorithm.get_next_command(prev_result)
        if cmd.payload_bits < 0: 
            break
            
        # B. [PHY] 下行链路
        t_reader_tx = CONSTANTS['T_PREAMBLE'] + (cmd.payload_bits / CONSTANTS['READER_RATE']) * 1e6
        total_time_us += t_reader_tx
        total_reader_energy_j += (t_reader_tx * 1e-6) * CONSTANTS['P_TX_READER']
        if config.ENABLE_ENERGY_TRACKING:
            total_tag_energy_j += present_tags_count * (t_reader_tx * 1e-6) * CONSTANTS['P_RX_TAG']
        
        # C. [PHY] 标签响应
        responding_tags = []
        protocol_logic = cmd.response_protocol
        for tag in present_tags:
            if protocol_logic(tag):
                responding_tags.append(tag.epc)

        # D. [PHY] 结果判定
        total_slots += 1
        num_responses = len(responding_tags)
        
        status = PacketType.IDLE
        resolved_data = None
        noise_mask = 0 
        
        # --- D.1 基础物理状态 ---
        if num_responses == 0:
            status = PacketType.IDLE
            idle_slots += 1
        elif num_responses == 1:
            epc = responding_tags[0]
            status = PacketType.SUCCESS
            success_slots += 1
            resolved_data = [epc]
        else:
            status = PacketType.COLLISION
            collision_slots += 1
            winner = None
            if config.ENABLE_CAPTURE_EFFECT:
                signal_strengths = [(e, rssi_map[e]) for e in responding_tags]
                signal_strengths.sort(key=lambda x: x[1], reverse=True)
                if len(signal_strengths) >= 2:
                    if (signal_strengths[0][1] - signal_strengths[1][1]) >= config.CAPTURE_RATIO_DB:
                        winner = signal_strengths[0][0]
            if winner:
                collision_slots -= 1 
                success_slots += 1   
                status = PacketType.SUCCESS
                resolved_data = [winner]

        # --- D.2 噪声与损伤注入 (Impaiments Injection) ---
        extra_impairments = None

        # 1. 整包丢失 (Preamble Loss)
        if config.ENABLE_NOISE and random.random() < config.packet_error_rate:
            status = PacketType.IDLE
        
        elif status != PacketType.IDLE:
            expected_len = cmd.expected_reply_bits
            if expected_len > 0:
                
                # 随机比特翻转模拟
                if config.ENABLE_NOISE and config.BIT_ERROR_RATE > 0:
                    for i in range(expected_len):
                        if random.random() < config.BIT_ERROR_RATE:
                            noise_mask |= (1 << i)
                
                # 时钟漂移模拟
                if config.CLOCK_DRIFT_RATE > 0:
                    max_safe_bits = int(0.5 / config.CLOCK_DRIFT_RATE)
                    if expected_len > max_safe_bits:
                        for i in range(max_safe_bits, expected_len):
                            noise_mask |= (1 << i)
                
                # 突发擦除与时序抖动注入
                if config.BURST_ERASURE_LEN > 0 or config.JITTER_OFFSET > 0:
                    erasure_mask = 0
                    
                    # 生成擦除掩码
                    if config.BURST_ERASURE_LEN > 0:
                        # 随机选择擦除起点，保证在有效长度内
                        max_start = max(0, expected_len - config.BURST_ERASURE_LEN)
                        start_bit = random.randint(0, max_start)
                        # 构造掩码：将 start_bit 开始的 L 位设为 1
                        erasure_mask = ((1 << config.BURST_ERASURE_LEN) - 1) << start_bit
                    
                    # 封装损伤数据
                    extra_impairments = {
                        'erasure': erasure_mask,
                        'shift': config.JITTER_OFFSET
                    }
                    
                    if not supports_phy:
                        # 对于常规算法：任何物理层的结构性损伤(位移、擦除)都会导致解码失败
                        status = PacketType.IDLE
                        resolved_data = None
        # E. [PHY] 上行链路能耗
        step_duration = 0.0
        if status == PacketType.IDLE:
            step_duration = CONSTANTS['T1'] 
        else:
            # 1. 基础耗时 (Payload + 协议开销)
            base_duration = _calc_dynamic_reply_time(cmd.expected_reply_bits)
            
            # 额外物理间隙惩罚 (Guard Interval Penalty)
            # 只有当多个标签回答拼接 (count > 1) 且设置了保护间隔时才生效
            gap_penalty = 0.0
            if cmd.concatenated_tags_count > 1 and config.GUARD_INTERVAL_BITS > 0:
                # 缝隙数量 = 标签数量 - 1
                num_gaps = cmd.concatenated_tags_count - 1
                # 单个比特耗时 (us) = (1 / BLF) * 1e6
                t_bit_us = (1.0 / CONSTANTS['BLF']) * 1e6
                # 总惩罚时间
                gap_penalty = num_gaps * config.GUARD_INTERVAL_BITS * t_bit_us
            step_duration = base_duration + gap_penalty

        total_time_us += step_duration
        total_reader_energy_j += (step_duration * 1e-6) * CONSTANTS['P_TX_READER']
        
        if config.ENABLE_ENERGY_TRACKING:
            active_cnt = num_responses
            silent_cnt = present_tags_count - active_cnt
            e_active = active_cnt * (step_duration * 1e-6) * CONSTANTS['P_TX_TAG']
            e_silent = silent_cnt * (step_duration * 1e-6) * CONSTANTS['P_RX_TAG']
            total_tag_energy_j += (e_active + e_silent)

        # 构建结果
        prev_result = SlotResult(status, responding_tags, resolved_data, 
                                 channel_noise_mask=noise_mask,
                                 extra_info=extra_impairments) # 注入损伤数据

    phy_efficiency = success_slots / total_slots if total_slots > 0 else 0.0
    
    return {
        'total_time_us': total_time_us,
        'total_reader_energy_j': total_reader_energy_j,
        'total_tag_energy_j': total_tag_energy_j,
        'total_slots': total_slots,
        'success_slots': success_slots,
        'collision_slots': collision_slots,
        'idle_slots': idle_slots,
        'phy_efficiency': phy_efficiency
    }

def _calc_dynamic_reply_time(bits_count: int) -> float:
    t_data = (bits_count / CONSTANTS['BLF']) * 1e6
    if bits_count <= 1: 
        overhead = CONSTANTS['T1'] + CONSTANTS['T2']
    elif bits_count <= 20:
        overhead = CONSTANTS['T1'] + CONSTANTS['T2']
    else:
        t_ack = (18 / CONSTANTS['READER_RATE']) * 1e6
        overhead = 3*CONSTANTS['T1'] + 2*CONSTANTS['T2'] + t_ack
    return t_data + overhead