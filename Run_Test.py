# -*- coding: utf-8 -*-
"""
Run_Test.py
通用算法验证与健全性检查工具 (V6.0 - 10-Round Robustness)

【更新说明】
1. 升级为 10 轮次循环测试机制，避免侥幸通过。
2. 引入 Seed 控制，确保每一轮测试的可复现性。
3. 新增“失败案例捕获”，自动记录未通过轮次的详细参数（FP/FN/环境/种子）。
4. 优化汇总表格，展示通过率与平均性能指标。
"""

import time
import random
import logging
import pandas as pd
from typing import List, Dict, Optional

# --- 导入核心框架 ---
from framework import (
    run_high_fidelity_simulation,
    SimulationConfig,
    Tag,
    AlgorithmInterface
)

# --- 导入配置中心 ---
from Algorithm_Config import ALGORITHM_LIBRARY

# 测试列表 (在此处修改要测试的算法)
RUN_TEST = ['LODS_MTI'] 

# 测试配置
ROUND_COUNT = 100         # 测试总轮次
TEST_TAGS = 500          # 标签数量
TEST_MISSING_RATE = 0.5  # 缺失率

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
# 屏蔽底层日志，专注结果
logging.getLogger('framework').setLevel(logging.WARNING)

class AlgorithmTester:
    def __init__(self):
        self.results_summary = []
        self.failed_cases = [] # 专门存储失败的案例详情

    def generate_scenario(self, total_tags: int, missing_rate: float, seed: int) -> List[Tag]:
        """
        生成符合 Hash 计算要求的 Hex EPC 标签
        :param seed: 随机种子，确保场景生成的唯一性与可复现性
        """
        # 使用局部随机源生成标签，避免污染全局状态，但打乱时受全局seed控制
        tags = []
        num_missing = int(total_tags * missing_rate)
        
        # 使用固定的 Base ID
        base_id_int = 0xE200001D4500000000000000
        
        for i in range(total_tags):
            epc_int = base_id_int + i
            epc_hex = format(epc_int, '024X') 
            tags.append(Tag(epc=epc_hex, is_present=True))

        # 根据种子进行打乱
        # 注意：为了让 framework 的 Aloha 随机性也受控，我们在 run_single_test 中设置全局 seed
        # 这里直接利用全局 random 即可
        random.shuffle(tags)
        
        for i in range(num_missing):
            tags[i].is_present = False
            
        return tags

    def run_single_test(self, 
                        round_idx: int,
                        seed: int,
                        algo_key: str, 
                        total_tags: int, 
                        missing_rate: float,
                        env_type: str = "Ideal"):
        """
        运行单个测试用例
        """
        
        if algo_key not in ALGORITHM_LIBRARY:
            logger.error(f"❌ 算法 '{algo_key}' 未定义")
            return

        algo_conf = ALGORITHM_LIBRARY[algo_key]
        algo_class = algo_conf['class']
        algo_params = algo_conf.get('params', {})
        
        # --- 1. 关键：设置全局随机种子 ---
        # 这确保了：场景生成、噪声发生、碰撞槽选择 在这一轮都是确定的
        random.seed(seed)
        
        # --- 2. 配置物理环境 ---
        sim_config = SimulationConfig(
            TOTAL_TAGS=total_tags,
            MISSING_RATE=missing_rate,
            ENABLE_ENERGY_TRACKING=True
        )

        if env_type == "Noisy":
            sim_config.ENABLE_NOISE = True
            sim_config.packet_error_rate = 0.1 # 10% 丢包
        elif env_type == "Capture":
            sim_config.ENABLE_CAPTURE_EFFECT = True
            sim_config.CAPTURE_RATIO_DB = 3.0
            
        # 日志前缀
        log_prefix = f"[{algo_key}][{env_type}][R{round_idx+1}]"

        # --- 3. 准备数据 ---
        scenario_tags = self.generate_scenario(total_tags, missing_rate, seed)
        ground_truth_missing = {t.epc for t in scenario_tags if not t.is_present}
        
        # --- 4. 初始化算法 ---
        try:
            algo_instance = algo_class(**algo_params)
            algo_instance.initialize(scenario_tags)
        except Exception as e:
            logger.error(f"{log_prefix} ❌ 初始化失败: {e}")
            return

        # --- 5. 运行仿真 ---
        start_cpu = time.time()
        try:
            stats = run_high_fidelity_simulation(algo_instance, sim_config, scenario_tags)
        except Exception as e:
            logger.error(f"{log_prefix} ❌ 仿真崩溃: {e}", exc_info=True)
            self.failed_cases.append({
                "轮次": round_idx + 1,
                "算法": algo_key,
                "环境": env_type,
                "种子(Seed)": seed,
                "错误原因": f"CRASH: {str(e)}",
                "指标": "N/A"
            })
            return
        cpu_duration = time.time() - start_cpu

        # --- 6. 验证结果 (Accuracy) ---
        found_present, found_missing = algo_instance.get_results()
        
        # 兼容性处理：如果算法只返回 Present 集合
        if not found_missing and found_present:
            all_epcs = {t.epc for t in scenario_tags}
            found_missing = all_epcs - found_present

        tp = len(found_missing.intersection(ground_truth_missing))
        fp = len(found_missing) - tp  # 误报：把在场的当成了缺失
        fn = len(ground_truth_missing) - tp # 漏报：没把缺失的找出来
        
        is_pass = (fp == 0 and fn == 0)
        status_icon = "✅" if is_pass else "❌"

        # --- 7. 计算核心指标 ---
        total_time_s = stats.get('total_time_us', 0) / 1e6
        total_slots = stats.get('total_slots', 0)
        throughput = total_tags / total_time_s if total_time_s > 0 else 0
        
        # 识别效率
        if 'phy_efficiency' in stats:
             phy_efficiency = stats['phy_efficiency']
        else:
             phy_efficiency = stats.get('success_slots', 0) / total_slots if total_slots > 0 else 0
        id_efficiency = total_tags / total_slots if total_slots > 0 else 0

        # --- 8. 失败处理与日志 ---
        if not is_pass:
            # 记录详细失败信息
            fail_info = {
                "轮次": round_idx + 1,
                "算法": algo_key,
                "环境": env_type,
                "种子(Seed)": seed,
                "错误原因": f"FP={fp}, FN={fn}",
                "指标": f"Slots={total_slots}, Eff={id_efficiency:.3f}"
            }
            self.failed_cases.append(fail_info)
            logger.warning(f"{log_prefix} {status_icon} 失败! FP={fp}, FN={fn} (Seed={seed})")
        else:
            # 成功则仅输出简略信息
            logger.info(f"{log_prefix} {status_icon} 通过 | 耗时: {total_time_s*1000:.1f}ms | 效率: {id_efficiency:.3f}")

        # 添加到总表
        self.results_summary.append({
            "算法": algo_key,
            "环境": env_type,
            "轮次": round_idx + 1,
            "是否通过": 1 if is_pass else 0,
            "耗时(ms)": total_time_s * 1000,
            "效率(tags/slot)": id_efficiency,
            "吞吐量": throughput
        })

    def print_summary(self):
        if not self.results_summary: return
        df = pd.DataFrame(self.results_summary)
        
        print("\n" + "="*100)
        print("                                   测试结果报告 (Summary)                                   ")
        print("="*100)

        # --- 第一部分：打印失败案例详情 (如果有) ---
        if self.failed_cases:
            print("\n⚠️  检测到测试失败 (Failed Cases Details):")
            print("-" * 100)
            fail_df = pd.DataFrame(self.failed_cases)
            # 调整列宽显示
            print(fail_df.to_string(index=False))
            print("-" * 100 + "\n")
        else:
            print("\n🎉  恭喜！所有 10 轮测试全部通过 (All Passed)。\n")

        # --- 第二部分：聚合统计表 ---
        print("📊  性能统计 (按算法与环境分组):")
        print("-" * 100)
        
        # 分组计算统计值
        summary_df = df.groupby(['算法', '环境']).agg({
            '是否通过': ['count', 'sum'],  # count=总次数, sum=通过次数
            '耗时(ms)': 'mean',
            '效率(tags/slot)': 'mean',
            '吞吐量': 'mean'
        }).reset_index()

        # 重命名列以使其易读
        summary_df.columns = ['算法', '环境', '总轮次', '通过数', '平均耗时(ms)', '平均效率', '平均吞吐']
        
        # 计算通过率
        summary_df['通过率'] = (summary_df['通过数'] / summary_df['总轮次']).apply(lambda x: f"{x:.1%}")
        
        # 格式化数值保留小数
        summary_df['平均耗时(ms)'] = summary_df['平均耗时(ms)'].map('{:.2f}'.format)
        summary_df['平均效率'] = summary_df['平均效率'].map('{:.3f}'.format)
        summary_df['平均吞吐'] = summary_df['平均吞吐'].map('{:.0f}'.format)

        # 调整列顺序
        final_cols = ['算法', '环境', '总轮次', '通过率', '平均耗时(ms)', '平均效率', '平均吞吐']
        print(summary_df[final_cols].to_string(index=False))
        print("="*100 + "\n")

if __name__ == "__main__":
    tester = AlgorithmTester()
    
    print(f"🚀 启动鲁棒性循环测试 (Robustness Loop Test)")
    print(f"🎯 算法: {RUN_TEST}")
    print(f"⚙️  设置: 标签数={TEST_TAGS}, 缺失率={TEST_MISSING_RATE}, 轮次={ROUND_COUNT}\n")

    start_all = time.time()

    # --- 10轮 循环 ---
    for round_i in range(ROUND_COUNT):
        # 每一轮使用一个基准种子
        # 这样能保证这一轮里的 "Ideal" 和 "Noisy" 面对的是同一个标签分布（虽然random.seed会重置）
        current_seed = 2024 + round_i 
        
        for algo in RUN_TEST:
            # 1. 理想环境测试
            tester.run_single_test(
                round_idx=round_i,
                seed=current_seed, 
                algo_key=algo, 
                total_tags=TEST_TAGS, 
                missing_rate=TEST_MISSING_RATE, 
                env_type="Ideal"
            )
            
            # 2. 噪声环境测试
            tester.run_single_test(
                round_idx=round_i,
                seed=current_seed, 
                algo_key=algo, 
                total_tags=TEST_TAGS, 
                missing_rate=TEST_MISSING_RATE, 
                env_type="Noisy"
            )
            
    print(f"⏳ 测试总耗时: {time.time() - start_all:.2f}s")
    
    # 打印最终报表
    tester.print_summary()