# -*- coding: utf-8 -*-
"""
Exp_Sup_1_Figure.py
补充实验1 专属绘图脚本：时钟漂移容忍度分析
(Clock Drift Tolerance Analysis)

【展示目标】
1. 左图 (Reliability): 验证相干约束理论，展示 Fixed-128 (红线) 的物理崩溃点。
2. 右图 (Goodput): 展示 Adaptive (蓝线) 如何通过牺牲少量速率换取极高的鲁棒性。

【依赖关系】
1. 数据源: Results_Exp_Sup_1/ (由 Exp_Sup_1.py 生成)
2. 绘图核: Science_Figure.py
"""

import os
from Science_Figure import SciencePlotter

# =========================================================
# 配置区
# =========================================================
# 输入目录：必须与 Exp_Sup_1.py 中的 OUTPUT_DIR 一致
INPUT_DIR = "Results_Exp_Sup_1"
# INPUT_DIR = "Results_Exp_Sup_1_All"
# INPUT_DIR = "Results_Exp_Sup_1"
# 输出目录：论文图片存放位置
OUTPUT_DIR = "Paper_Figures/Exp_Sup_1_Feasibility_Drift"

# X轴标签：时钟漂移率 (使用 LaTeX 公式)
# 注：输入数据是 0.0 ~ 0.2，这里标注为 ratio 或 %
X_LABEL = r"Clock Drift Rate ($\delta$)"

# =========================================================
# 主程序
# =========================================================
if __name__ == "__main__":
    # 基础配置：高亮我们的自适应算法
    base_cfg = {
        'highlight': 'LODS-MTI (Adaptive)',  # 对应 Exp_Sup_1.py 中的 label
        'mark_step': 1,  # 数据点较少(10个左右)，每个点都画标记
        'grid': True,
    }

    # 1. 安全检查
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 错误: 未找到数据目录 '{INPUT_DIR}'")
        print("   -> 请先运行 'Exp_Sup_1.py' 生成数据。")
        exit()

    # 2. 初始化绘图引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动绘图引擎，源数据: {INPUT_DIR}")

    # =====================================================
    # 图表 A: 物理可行性双子图 (Reliability & Goodput)
    # =====================================================
    tasks_drift = [
        # (a) Reliability / Recall
        {
            'file': os.path.join(INPUT_DIR, "raw_Recall.csv"),
            'x_col': 'Drift_Rate',           # Exp_Sup_1.py 中指定的 x_axis_key
            'y_col': 'Identification Reliability', # Y轴标签
            'xlabel': X_LABEL,
            'ylim': (0.0, 1.05),             # 固定 Y 轴范围 [0, 1] 以便清晰展示
            **base_cfg,
        },
        # (b) Effective Throughput (Goodput)
        {
            'file': os.path.join(INPUT_DIR, "raw_Goodput.csv"),
            'x_col': 'Drift_Rate',
            'y_col': 'Effective Goodput (tags/s)', # 强调是“有效”吞吐量
            'xlabel': X_LABEL,
            **base_cfg,
        }
    ]

    print("running Fig: Drift Tolerance Analysis (Double)...")
    
    # 绘制 1x2 布局
    plotter.draw_scientific_figure(
        tasks=tasks_drift,
        layout_type='double', 
        filename="Fig_Sup_1_Feasibility_Drift_Tolerance",
    )

    print(f"\n🎉 绘图完成！请查看文件夹: {OUTPUT_DIR}")
    print(f"   生成的图片可直接用于 Section IV. Feasibility Analysis")
    print(f"   1. 左图应显示红线在 x=0.15 附近断崖下跌 (验证理论边界)。")
    print(f"   2. 右图应显示蓝线在 x=0.20 时依然保持较高吞吐量 (验证安全裕量)。")