# -*- coding: utf-8 -*-
"""
Exp_Sup_7_Figure.py
补充实验7 专属绘图脚本：微观物理层损伤鲁棒性 (Micro-Physical Resilience)
(Burst Erasure & Timing Jitter)

【展示目标】
1. 核心证明：展示 "LODS (rho=4)" (红线/Robust) 如何通过多数投票机制，
   在物理层发生比特丢失或滑移时实现 "自愈合 (Self-Healing)"。
2. 对比反差：展示 "LODS (rho=2)" (非红线) 在微小损伤下的脆弱性，
   从而证明冗余设计不仅仅是为了抗高斯白噪，更是为了抗结构性物理损伤。

【依赖关系】
1. 数据源: Results_Exp_Sup_7/ (由 Exp_Sup_7_Bit_Fly.py 生成)
   - 子目录: Burst_Experiment/
   - 子目录: Jitter_Experiment/
2. 绘图核: Science_Figure.py
"""

import os
from Science_Figure import SciencePlotter

# =========================================================
# 配置区
# =========================================================
# 根数据目录
INPUT_ROOT = "Results_Exp_Sup_7"
# 输出目录
OUTPUT_DIR = "Paper_Figures/Exp_Sup_7_Micro_Resilience"

# =========================================================
# 主程序
# =========================================================
if __name__ == "__main__":
    # 基础配置
    # 策略：高亮 rho=4 (Robust Mode)，这是我们想要推崇的配置
    base_cfg = {
        'highlight': 'LODS (rho=4)',  # 对应 Exp_Sup_7.py 中的 label
        'mark_step': 1,  # 数据点很少(0-8)，必须全部画出
        'grid': True,
        # 强制指定 Y 轴标签，覆盖默认的字典映射
        'y_col': 'Identification Reliability (Recall)', 
    }

    # 1. 安全检查
    if not os.path.exists(INPUT_ROOT):
        print(f"❌ 错误: 未找到数据目录 '{INPUT_ROOT}'")
        print("   -> 请先运行 'Exp_Sup_7_Bit_Fly.py' 生成数据。")
        exit()

    burst_file = os.path.join(INPUT_ROOT, "Burst_Experiment", "raw_Reliability.csv")
    jitter_file = os.path.join(INPUT_ROOT, "Jitter_Experiment", "raw_Reliability.csv")

    if not os.path.exists(burst_file) or not os.path.exists(jitter_file):
        print("❌ 错误: 子目录数据缺失。请检查 Exp_Sup_7_Bit_Fly.py 是否完整运行了两个 Phase。")
        exit()

    # 2. 初始化绘图引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动绘图引擎，源数据: {INPUT_ROOT}")

    # =====================================================
    # 图表: 微观损伤鲁棒性双子图
    # Left: Burst Erasure | Right: Timing Jitter
    # =====================================================
    tasks_resilience = [
        # (a) Burst Erasure Tolerance
        # 预期：rho=4 在 x=1 时几乎不降，x=2 时轻微下降；rho=2 在 x=1 时直线下降。
        {
            'file': burst_file,
            'x_col': 'Metric_Value',        # Exp_Sup_7 中统一使用的 X 轴键名
            'xlabel': r"Burst Erasure Length ($L_{burst}$ bits)",
            'title': 'Resilience to Burst Erasure', # 可选标题
            # 显式指定刻度，确保 0-8 整数显示
            'xticks': list(range(0, 9)), 
            **base_cfg,
        },
        # (b) Timing Jitter Tolerance
        # 预期：rho=4 在 x=1 时保持高位平台区；rho=2 立即失效。
        {
            'file': jitter_file,
            'x_col': 'Metric_Value',
            'xlabel': r"Timing Jitter Offset ($\Delta t$ bits)",
            'title': 'Resilience to Sampling Jitter',
            'xticks': list(range(0, 5)),
            **base_cfg,
        }
    ]

    print("running Fig: Micro-Physical Resilience Analysis (Double)...")
    
    # 绘制 1x2 布局
    plotter.draw_scientific_figure(
        tasks=tasks_resilience,
        layout_type='double', 
        filename="Fig_Sup_7_Micro_Resilience",
    )

    print(f"\n🎉 绘图完成！请查看文件夹: {OUTPUT_DIR}")
    print(f"   生成的图片将是论文 Section V-B (Validation) 中最有力的证据之一。")
    print(f"   💡 预期视觉效果：")
    print(f"      [左图] 红线在 Burst=1 处应当有一个明显的'平台(Plateau)'，证明单比特丢失不影响决策。")
    print(f"      [右图] 红线在 Jitter=1 处应当依然坚挺，展示对时序滑移的容忍度。")