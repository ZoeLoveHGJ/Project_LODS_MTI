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
INPUT_DIR = "Results_Exp2_MissingRate"

# 输出目录：专门存放论文图片
OUTPUT_DIR = "Paper_Figures/Exp2_MissingRate"
FILE_NAME = "Fig_Exp2_Missing_Rate"
# X轴标签 (LaTeX 格式)
X_LABEL = "Tag Missing Ratio"
# X轴对应的列名
X_COL_NAME = "MISSING_RATE"
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
        print("   -> 请先运行 'Exp2.py' 生成数据。")
        exit()

    # 2. 初始化绘图引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动绘图引擎，源数据: {INPUT_DIR}")

    tasks = [
        # (b) Time
        {
            'file': os.path.join(INPUT_DIR, "raw_total_time_ms.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Idenfitication Time (ms)',
            'xlabel': X_LABEL,
            **base_cfg,
        },
        # (a) Efficiency
        {
            'file': os.path.join(INPUT_DIR, "raw_verification_concurrency.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Verification Concurrency (tags/query)',
            'xlabel': X_LABEL,
            **base_cfg,

        },
        # (b) Time
        {
            'file': os.path.join(INPUT_DIR, "raw_energy_per_tag_uj.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Energy Cost Per Tag (uJ)',
            'xlabel': X_LABEL,
            **base_cfg,
        },

        # (b) Time
        {
            'file': os.path.join(INPUT_DIR, "raw_edp.csv"),
            'x_col': X_COL_NAME,
            'y_col': 'Energy-Delay Product (J.s)',
            'xlabel': X_LABEL,
            **base_cfg,

        }
    ]

    print("running Fig : Overall Performance...")
    plotter.draw_scientific_figure(
        tasks=tasks,
        layout_type='quad', # 1x3 布局
        filename=FILE_NAME,
    )

    print(f"\n🎉 绘图完成！请查看文件夹: {OUTPUT_DIR}")