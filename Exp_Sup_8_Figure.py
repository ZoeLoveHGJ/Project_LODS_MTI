# -*- coding: utf-8 -*-
"""
Exp_Sup_8_Figure.py (V5.0 - Standard Engine Call)
补充实验8 绘图：LODS-MTI vs Real Baselines
严格遵循 Science_Figure V10.0 的标准调用方式。

【特性】
1. 零手动绘图：完全托管给 SciencePlotter 引擎。
2. 样式自动匹配：利用 highlight 参数强制指定主算法样式。
3. 绝对标准：输出符合 V10.0 定义的绝对几何尺寸图片。
"""

import os
import sys

# 1. 导入绘图引擎
try:
    from Science_Figure import SciencePlotter
except ImportError:
    print("❌ 错误: 未找到 Science_Figure.py。")
    sys.exit(1)

# =========================================================
# 配置区
# =========================================================
# 数据源目录
INPUT_ROOT = "Results_Exp_Sup_8_Guard_Time" 

OUTPUT_DIR = "Paper_Figures/Exp_Sup_8_Tg_Sensitivity"

# =========================================================
# 主程序
# =========================================================
if __name__ == "__main__":
    # 1. 数据文件检查
    # 注意：Tool.py 自动拆分的文件名为 raw_throughput.csv
    data_file = os.path.join(INPUT_ROOT, "raw_throughput.csv")
    
    if not os.path.exists(data_file):
        print(f"❌ 数据文件缺失: {data_file}")
        print("   -> 请检查 INPUT_ROOT 变量是否指向了正确的实验结果目录。")
        sys.exit(1)

    # 2. 初始化引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动 Science_Figure V10.0 引擎...")
    print(f"   数据源: {data_file}")

    # 3. 定义绘图任务 (Task)
    # SciencePlotter 的核心设计哲学：通过字典描述“画什么”
    task_tg_sensitivity = {
        'file': data_file,
        
        # X轴数据列名
        'x_col': 'Guard_Interval_Bits',
        
        # Y轴数据含义 (用于从 metric_label_map 查找 Label)
        # 对应 Science_Figure.py line 89: 'throughput': 'System Throughput (tags/s)'
        'y_col': 'throughput',
        
        # X轴 Label
        'xlabel': r'Physical Guard Interval $T_g$ (bits)',
        
        # 强制指定刻度 (可选)
        'xticks': [0.0, 0.5, 1.0, 1.5, 2.0],
        
        # [关键] 强制高亮主算法
        # 这会通知引擎将此列强制映射到 Style 0 (红色五角星)
        # 请确保此名称与 CSV 中的列名完全一致
        'highlight': 'LODS-MTI',
        
        # 排除不需要绘制的列 (可选)
        # 'exclude': ['Some_Other_Algo']
    }

    # 4. 执行绘图
    # layout_type='single' 表示单张图
    plotter.draw_scientific_figure(
        tasks=[task_tg_sensitivity], 
        layout_type='single', 
        filename="Fig8_Tg_Robustness_Standard"
    )

    print(f"\n✅ 绘图完成！")
    print(f"📂 输出目录: {OUTPUT_DIR}")
    print(f"📝 说明: 这里的图例、坐标轴字体、子图尺寸均由 Science_Figure 统一管控，")
    print(f"        确保了与论文中其他图表风格的绝对一致性。")