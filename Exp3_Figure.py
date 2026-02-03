# -*- coding: utf-8 -*-
"""
Exp1_Figure.py
实验1 专属绘图脚本：系统效率与可扩展性
(System Efficiency & Scalability Visualization)

【依赖关系】
1. 数据源: Results_Exp1_Parallel/ (由 Exp1_Efficiency_Parallel.py 生成)
2. 绘图核: Science_Figure.py
3. 配置文件: Algorithm_Config.py
"""

import os
from Science_Figure import SciencePlotter

# =========================================================
# 配置区
# =========================================================
# 输入目录：必须与 Exp1_Efficiency_Parallel.py 中的 OUTPUT_DIR 一致
# INPUT_DIR = "Results_Exp1_Parallel"
# INPUT_DIR = "Results_Exp1_Parallel"
INPUT_DIR = "Results_Exp3_BER"
# INPUT_DIR = "Results_Exp1_Parallel"
# INPUT_DIR = "Results_Exp1_Parallel"

# 输出目录：专门存放论文图片
OUTPUT_DIR = "Paper_Figures/Exp3_BER"

# X轴标签 (LaTeX 格式)
X_LABEL = "Bit Error Ratio ($ratio$)"
X_COL_NAME ="BIT_ERROR_RATE"
FILE_NAME = "Fig_Exp3_BER"

XTICK = [0.00,0.02,0.04,0.06,0.08,0.09] # 如果需要指定x轴刻度
# =========================================================
# 主程序
# =========================================================
if __name__ == "__main__":
    base_cfg = {
        'highlight': 'LODS_MTI', 
        'mark_step': 2, 
    }

    # 1. 安全检查
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 错误: 未找到数据目录 '{INPUT_DIR}'")
        print("   -> 请先运行 'Exp3.py' 生成数据。")
        exit()

    # 2. 初始化绘图引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动绘图引擎，源数据: {INPUT_DIR}")

    tasks = [
        # (b) Time
        {
            'file': os.path.join(INPUT_DIR, "raw_Reliability.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Reliability',
            'xlabel': X_LABEL,
            'xticks':XTICK,
            **base_cfg,
        },
        # (a) Efficiency
        {
            'file': os.path.join(INPUT_DIR, "raw_Goodput.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Good Throughput (tags/s)',
            'xlabel': X_LABEL,
            'xticks':XTICK,
            **base_cfg,
        },

        # (b) Time
        {
            'file': os.path.join(INPUT_DIR, "raw_energy_per_tag_uj.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Energy Cost Per Tag (uJ)',
            'xlabel': X_LABEL,
            'xticks':XTICK,
            **base_cfg,
        }
    ]

    print("running Fig : Overall Performance...")
    plotter.draw_scientific_figure(
        tasks=tasks,
        layout_type='triple_row', # 1x3 布局
        filename=FILE_NAME,
    )

    print(f"\n🎉 绘图完成！请查看文件夹: {OUTPUT_DIR}")
    # print(f"   1. Fig_Exp1_Scalability_Quad.pdf (推荐用于正文)")
    # print(f"   2. Fig_Exp1_Scalability_Triple.pdf (推荐用于正文)")
    print(f"   3. Fig_Exp3.pdf (备选)")