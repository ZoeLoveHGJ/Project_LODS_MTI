# -*- coding: utf-8 -*-
"""
Plot_Exp0_2.py
专用于绘制 "Rollercoaster" 动态场景的双轴图 (IEEE Standard Version).
适配：200轮三段式实验 (Ideal -> Storm -> Ideal)

【功能特点】
1. 双轴展示：左轴为执行时间 (Time)，右轴为准确率 (Recall/Accuracy)。
2. 科研级样式：Times New Roman 字体，清晰的图例分类，高分辨率输出。
3. 自动归档：自动创建文件夹并保存 PDF/PNG 双格式。
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# =========================================================
# 1. 全局配置与科研样式设定
# =========================================================
DATA_DIR = "Results_ExpNew0_2"
OUTPUT_DIR = os.path.join("Paper_Figures", "ExpNew0_2_Rollercoaster")
OUTPUT_NAME = "Fig_Exp0_2_Adaptive"

# 字体与渲染设置 (IEEE 标准)
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 14,
    'axes.titlesize': 14,
    'axes.labelsize': 14,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 14,
    'figure.titlesize': 16,
    'mathtext.fontset': 'stix',  # 数学公式字体
    'axes.linewidth': 1.5,       # 坐标轴线宽
    'lines.linewidth': 2.0,      # 默认线宽
    'xtick.direction': 'in',     # 刻度朝内
    'ytick.direction': 'in',
    'xtick.major.size': 5,
    'ytick.major.size': 5,
})

# 算法样式定义
STYLES = {
    'Adaptive':     {'color': '#FB7878', 'marker': 'o', 'ms': 0, 'label': 'LODS-Adaptive'}, # 红色 (重点)
    'Fixed-Fast':   {'color': '#BCD6AD', 'marker': '',  'ms': 0, 'label': 'Fixed (rho=2)'},         # 绿色 (背景板/理想)
    'Fixed-Robust': {'color': '#8076a3', 'marker': '',  'ms': 0, 'label': 'Fixed (rho=4)'}          # 紫色 (对比/鲁棒)
}

def plot_rollercoaster():
    # =========================================================
    # 2. 数据加载与预处理
    # =========================================================
    file_time = os.path.join(DATA_DIR, "raw_Time_ms.csv")
    file_recall = os.path.join(DATA_DIR, "raw_Recall.csv")

    if not os.path.exists(file_time) or not os.path.exists(file_recall):
        print(f"❌ 数据缺失: 请检查 {DATA_DIR} 目录下是否有 raw_Time_ms.csv 和 raw_Recall.csv")
        return

    df_time = pd.read_csv(file_time)
    df_recall = pd.read_csv(file_recall)

    # 统一索引 (假设第一列是X轴变量，通常是 Round 或 Time)
    x_col = df_time.columns[0] 
    df_time.set_index(x_col, inplace=True)
    df_recall.set_index(x_col, inplace=True)
    df_time.sort_index(inplace=True)
    df_recall.sort_index(inplace=True)

    # =========================================================
    # 3. 创建画布 (双轴系统)
    # =========================================================
    fig, ax1 = plt.subplots(figsize=(12, 6)) # 加宽一点以适应200轮
    ax2 = ax1.twinx()  # 共享x轴的右侧y轴

    # 设置层级: 背景(0) -> 网格(1) -> 数据(2) -> 图例(3)
    ax1.set_zorder(ax2.get_zorder() + 1) # 把左轴放到前面，方便操作
    ax1.patch.set_visible(False)         # 隐藏背景以显示右轴内容

    # =========================================================
    # 4. 绘制背景区域 (Phases - 适配 200 轮)
    # =========================================================
    # Phase 1: Ideal (0 - 50)
    ax2.axvspan(0, 50, color='#2CA02C', alpha=0.04, lw=0, zorder=0)
    # Phase 2: Noisy (Storm) (50 - 150)
    ax2.axvspan(50, 150, color='#D62728', alpha=0.04, lw=0, zorder=0)
    # Phase 3: Recovery (150 - 200)
    ax2.axvspan(150, 200, color='#2CA02C', alpha=0.04, lw=0, zorder=0)

    # 添加区域文字标注 (顶部居中)
    # y坐标需要根据数据动态调整，这里先取最大值的1.1倍作为文字基准线
    y_max_time = df_time.max().max() 
    text_y_pos = 100 # 稍微留出点余量
    
    # Phase I 中心: 25
    ax1.text(25, text_y_pos, "Phase I: Ideal\n(Baseline)", ha='center', va='bottom', 
             color='#2CA02C', fontweight='bold', fontsize=14)
    
    # Phase II 中心: 100
    ax1.text(100, text_y_pos, "Phase II: Dynamic Change\n(Max BER=10%, Loss=30%)", ha='center', va='bottom', 
             color='#D62728', fontweight='bold', fontsize=14)
    
    # Phase III 中心: 175
    ax1.text(175, text_y_pos, "Phase III: Recovery\n(Ideal)", ha='center', va='bottom', 
             color='#2CA02C', fontweight='bold', fontsize=14)

    # =========================================================
    # 5. 绘制核心曲线
    # =========================================================
    legend_handles_algo = []
    
    for algo in df_time.columns:
        if algo not in STYLES: continue
        s = STYLES[algo]
        
        # --- 左轴: Time (实线) ---
        # 如果是 Adaptive，加粗并置顶
        lw = 3.0 if 'Adaptive' in algo else 1.8
        alpha = 1.0 if 'Adaptive' in algo else 0.7
        zorder = 10 if 'Adaptive' in algo else 5
        
        l1, = ax1.plot(df_time.index, df_time[algo], 
                       color=s['color'], linestyle='-', linewidth=lw, 
                       alpha=alpha, zorder=zorder)
        
        # --- 右轴: Recall (点虚线) ---
        # Recall 使用较粗的虚线以增强视觉辨识度
        l2, = ax2.plot(df_recall.index, df_recall[algo], 
                       color=s['color'], linestyle='--', linewidth=2.5, 
                       alpha=0.8, zorder=zorder)
        
        # 收集算法图例句柄 (仅用颜色代表)
        legend_handles_algo.append(l1)

    # =========================================================
    # 6. 坐标轴与网格修饰
    # =========================================================
    # 标签
    ax1.set_xlabel("Simulation Round (Time)", fontweight='bold')
    ax1.set_ylabel("Identification Time (ms)", fontweight='bold')
    ax2.set_ylabel("Recall (Accuracy)", fontweight='bold', rotation=270, labelpad=20)
    
    # 范围 (适配 200 轮)
    ax1.set_xlim(0, 200)
    
    # Y轴范围动态微调
    ax1.set_ylim(bottom=60, top=y_max_time * 1.25) # 留足顶部空间给文字
    ax2.set_ylim(0.6, 1.02) # Recall 固定 0.6~1.02
    
    # 网格 (仅基于左轴)
    ax1.grid(True, which='major', linestyle='--', alpha=0.5, color='gray')

    # =========================================================
    # 7. 智能双图例设计 (核心优化)
    # =========================================================
    # 图例 1: 算法颜色 (左上)
    algo_labels = [STYLES[col]['label'] for col in df_time.columns if col in STYLES]
    leg1 = ax1.legend(legend_handles_algo, algo_labels, loc='upper left', 
                      title="Algorithms", framealpha=0.95, edgecolor='black', fancybox=False,
                      bbox_to_anchor=(0.05, 0.65))
    leg1.get_frame().set_linewidth(0.5)

    # 图例 2: 线型含义 (右上)
    line_time = Line2D([0], [0], color='black', lw=2, linestyle='-', label='Execution Time')
    line_recall = Line2D([0], [0], color='black', lw=2, linestyle='--', label='Recall (Accuracy)')
    leg2 = ax2.legend(handles=[line_time, line_recall], loc='upper right', 
                      title="Metrics", framealpha=0.95, edgecolor='black', fancybox=False,
                      bbox_to_anchor=(0.95, 0.60))
    leg2.get_frame().set_linewidth(0.5)

    # =========================================================
    # 8. 保存与输出
    # =========================================================
    plt.tight_layout()
    
    # 自动创建目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 已创建输出目录: {OUTPUT_DIR}")

    # 保存 PDF (矢量)
    pdf_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_NAME}.pdf")
    plt.savefig(pdf_path, dpi=600, format='pdf', bbox_inches='tight')
    
    # 保存 PNG (预览)
    png_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_NAME}.png")
    plt.savefig(png_path, dpi=300, format='png', bbox_inches='tight')

    print(f"📊 绘图完成！")
    print(f"   - PDF: {pdf_path}")
    print(f"   - PNG: {png_path}")
    
    # plt.show() 

if __name__ == "__main__":
    plot_rollercoaster()