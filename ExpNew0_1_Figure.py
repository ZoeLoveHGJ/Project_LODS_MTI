# -*- coding: utf-8 -*-
"""
ExpNew0_1_Figure.py
实验 New0.1 专属绘图脚本：投票机制验证 (Recall vs BER)
(Internal Validation: Voting Mechanism Robustness)

【依赖关系】
1. 数据源: Results_ExpNew0_1/ (需包含 raw_Recall.csv)
2. 绘图核: Science_Figure.py
3. 配置文件: Algorithm_Config.py
"""

import os
import sys

# 确保能找到 Science_Figure
sys.path.append(os.getcwd())
from Science_Figure import SciencePlotter

# =========================================================
# 配置区
# =========================================================
# 输入目录：存放 csv 文件的位置
INPUT_DIR = "Results_ExpNew0_1"

# 输出目录：生成的 PDF/PNG 存放位置
OUTPUT_DIR = "Paper_Figures/ExpNew0_1_Vote"

# X轴标签 (LaTeX 格式)
X_LABEL = r"Bit Error Rate ($P_{e}$)"

# =========================================================
# 主程序
# =========================================================
if __name__ == "__main__":
    # 1. 安全检查
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 错误: 未找到数据目录 '{INPUT_DIR}'")
        print("   -> 请确保已运行仿真并生成了 CSV 数据。")
        # 为了防止直接报错退出，这里仅做提示，如果文件夹不存在脚本会停止
        sys.exit(1)

    # 2. 初始化绘图引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动绘图引擎，源数据: {INPUT_DIR}")
    print(f"📂 输出目录: {OUTPUT_DIR}")

    # -----------------------------------------------------
    # 图表定义: Recall vs BER
    # -----------------------------------------------------
    
    tasks_validation = [
        {
            # 文件名：Tool.py 自动拆分出的文件名通常是 raw_{指标名}.csv
            'file': os.path.join(INPUT_DIR, "raw_Recall.csv"),
            
            # X 轴列名：CSV 中代表横坐标的列
            'x_col': 'BER',
            
            # Y 轴列名：用于自动查找 Y 轴 Label (如果 Science_Figure 字典里没有，则直接显示此字符串)
            'y_col': 'Recall',
            
            # X 轴显示标签
            'xlabel': X_LABEL,
            
            # (可选) 排除不需要绘图的列
#            'exclude': ['run_id', 'MISSING_RATE', 'std', 'var'],
            
            # (可选) 稀疏采样：如果点太密，可以设为 2 或 5
            'mark_step': 1,
            
            # (可选) 高亮算法：强制指定某个算法使用 Style 0 (红色五角星)
            'highlight': 'Ours (Voting)' 
        }
    ]

    print("running Fig 0-1: Recall vs BER (Single)...")
    
    # 调用 Science_Figure 的核心绘图函数
    plotter.draw_scientific_figure(
        tasks=tasks_validation,
        layout_type='single',  # 单图布局
        filename="Fig_Exp0_1_Recall_vs_BER"
    )

    print(f"\n🎉 绘图完成！请查看文件夹: {OUTPUT_DIR}")
    print(f"   -> Fig_Exp0_1_Recall_vs_BER.pdf")