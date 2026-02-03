# -*- coding: utf-8 -*-
"""
Exp_Sup_6_Figure.py
补充实验6 专属绘图脚本：硬件可行性验证 (Hardware Feasibility)
(Arbitrary K vs. Power-of-2 Constraint)

【展示目标】
1. 核心证明：展示 "LODS-MTI (Power-of-2)" (红线) 与 "LODS-MTI (Arbitrary K)" (对比线)
   在吞吐量和时延上几乎完全重合。
2. 论点支撑：这证明了将模运算优化为位运算(Bitwise AND)不会造成性能损失，
   从而确立了算法在无源标签上的工程可行性。

【依赖关系】
1. 数据源: Results_Exp_Sup_6/ (由 Exp_Sup_6_Hardware.py 生成)
2. 绘图核: Science_Figure.py
"""

import os
from Science_Figure import SciencePlotter

# =========================================================
# 配置区
# =========================================================
# 输入目录：必须与 Exp_Sup_6_Hardware.py 中的 OUTPUT_DIR 一致
INPUT_DIR = "Results_Exp_Sup_6"
# 输出目录：论文图片存放位置
OUTPUT_DIR = "Paper_Figures/Exp_Sup_6_Hardware_Feasibility"

# X轴标签：标签总数 N
X_LABEL = r"Number of Tags ($N$)"

# =========================================================
# 主程序
# =========================================================
if __name__ == "__main__":
    # 基础配置
    # 策略：高亮 "Power-of-2" 版本，暗示这是最终推荐的工程实现
    base_cfg = {
        'highlight': 'LODS-MTI (Power-of-2)',  # 对应 Exp_Sup_6.py 中的 label
        'mark_step': 1,  # 点比较少(10个)，全画出来
        'grid': True,
    }

    # 1. 安全检查
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 错误: 未找到数据目录 '{INPUT_DIR}'")
        print("   -> 请先运行 'Exp_Sup_6_Hardware.py' 生成数据。")
        exit()

    # 2. 初始化绘图引擎
    plotter = SciencePlotter(output_dir=OUTPUT_DIR)
    print(f"🎨 启动绘图引擎，源数据: {INPUT_DIR}")

    # =====================================================
    # 图表: 硬件可行性验证双子图 (Throughput & Time)
    # =====================================================
    tasks_hardware = [
        # (a) System Throughput
        # 预期：两条线重合，证明限制 K 为 2^n 不影响吞吐量
        {
            'file': os.path.join(INPUT_DIR, "raw_System_Throughput.csv"),
            'x_col': 'TOTAL_TAGS',          # Exp_Sup_6.py 中指定的 x_axis_key
            'y_col': 'System Throughput (tags/s)', # Y轴标签
            'xlabel': X_LABEL,
            **base_cfg,
        },
        # (b) Identification Time
        # 预期：两条线重合，证明时间开销一致
        {
            'file': os.path.join(INPUT_DIR, "raw_Total_Time_ms.csv"),
            'x_col': 'TOTAL_TAGS',
            'y_col': 'Identification Time (ms)',
            'xlabel': X_LABEL,
            **base_cfg,
        }
    ]

    print("running Fig: Hardware Feasibility Analysis (Double)...")
    
    # 绘制 1x2 布局
    plotter.draw_scientific_figure(
        tasks=tasks_hardware,
        layout_type='double', 
        filename="Fig_Sup_6_Hardware_Feasibility",
    )

    print(f"\n🎉 绘图完成！请查看文件夹: {OUTPUT_DIR}")
    print(f"   生成的图片可直接用于 Section IV-F (Feasibility Analysis) 或 Discussion")
    print(f"   💡 预期视觉效果：")
    print(f"      红线 (Power-of-2) 应与另一条线紧密重叠，")
    print(f"      直接视觉化地证明了 'Complexity Reduction without Performance Loss'。")