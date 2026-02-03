# -*- coding: utf-8 -*-
"""
Exp_Sup_5_Figure.py
实验五专属绘图：容忍度恢复机理验证 (Tolerance Recovery & Hysteresis Analysis)
展示 epsilon=0.30 如何消除恢复期滞后 (De-hysteresis)。

【图表逻辑】
- 左轴 (Goodput): 展示吞吐量随信道恢复的回升速度。预期 0.30 紧贴信道回升，0.10 滞后。
- 右轴 (Recall): 展示可靠性。在风暴高潮期 (Round 100左右)，两者都应保持高可靠性 (因为都切到了 Robust)。
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

# =========================================================
# 1. 全局配置与科研样式设定
# =========================================================
DATA_DIR = "Results_Exp_Sup_5_Tolerance_Recover"
OUTPUT_DIR = os.path.join("Paper_Figures", "Exp_Sup_5_Recovery")
OUTPUT_NAME = "Fig_Sup_5_Recovery_Lag"

# 字体与渲染设置 (IEEE Transaction Standard)
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 14,
    'axes.titlesize': 14,
    'axes.labelsize': 14,
    'xtick.labelsize': 15,
    'ytick.labelsize': 15,
    'legend.fontsize': 14,
    'figure.titlesize': 16,
    'mathtext.fontset': 'stix',
    'axes.linewidth': 1.5,
    'lines.linewidth': 2.0,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
})

# 算法样式定义 (映射 Exp_Sup_5.py 中的 names)
STYLES = {
    'LODS (eps=0.30)': {
        'color': '#D62728', 'lw': 3.0, 'ls': '-', 'zorder': 10, 
        'label': r'LODS ($\epsilon=0.30$, Ours)'
    }, 
    'LODS (eps=0.25)': {
        'color': '#8076a3', 'lw': 2.5, 'ls': '-', 'zorder': 8, 
        'label': r'LODS ($\epsilon=0.25$, Conservative)'
    }, 
    'LODS (eps=0.40)': {
        'color': '#1F77B4', 'lw': 2.5, 'ls': '-', 'zorder': 8, 
        'label': r'LODS ($\epsilon=0.40$, Boundary)'
    }, 
    'LODS (eps=0.60)': {
        'color': '#FF7F0E', 'lw': 2.5, 'ls': '-', 'zorder': 8, 
        'label': r'LODS ($\epsilon=0.60$, Over-aggressive)'
    }, 
    'Fixed-Robust': {
        'color': '#7F7F7F', 'lw': 2.0, 'ls': '--', 'zorder': 5, 
        'label': 'Fixed-Robust (Benchmark)'
    }
}

def plot_recovery_analysis():
    # =========================================================
    # 2. 数据加载
    # =========================================================
    file_goodput = os.path.join(DATA_DIR, "raw_Goodput.csv")
    file_recall = os.path.join(DATA_DIR, "raw_Recall.csv")

    if not os.path.exists(file_goodput) or not os.path.exists(file_recall):
        print(f"❌ 数据缺失: 请检查 {DATA_DIR}。")
        return

    df_goodput = pd.read_csv(file_goodput)
    df_recall = pd.read_csv(file_recall)

    # 统一索引 (Round)
    x_col = df_goodput.columns[0] # Usually 'Round'
    df_goodput.set_index(x_col, inplace=True)
    df_recall.set_index(x_col, inplace=True)
    df_goodput.sort_index(inplace=True)
    df_recall.sort_index(inplace=True)

    # =========================================================
    # 3. 创建画布 (双轴)
    # =========================================================
    # 宽一点，展示时序演变
    fig, ax1 = plt.subplots(figsize=(12, 6)) 
    ax2 = ax1.twinx()

    # 层级控制：让左轴的内容在右轴之上 (防止 grid 遮挡)
    ax1.set_zorder(ax2.get_zorder() + 1)
    ax1.patch.set_visible(False)

    # =========================================================
    # 4. 绘制背景区域 (Phase 1-3)
    # =========================================================
    # Phase 1: Ideal (0 - 40)
    ax2.axvspan(0, 40, color='#E5F5E0', alpha=0.5, lw=0) # 淡绿
    # Phase 2: Storm (40 - 160)
    ax2.axvspan(40, 160, color='#FEE0D2', alpha=0.5, lw=0) # 淡红
    # Phase 3: Recovery (160 - 200)
    ax2.axvspan(160, 200, color='#E5F5E0', alpha=0.5, lw=0) # 淡绿
    
    # 阶段标注
    y_max = df_goodput.max().max() * 1.15
    
    ax1.text(20, y_max*0.15, "Phase I: Ideal\n(Baseline)", 
             ha='center', va='top', color='#2CA02C', fontweight='bold', fontsize=14)
    
    ax1.text(100, y_max*0.15, "Phase II: Dynamic Storm\n(Cosine Wave: BER 0%→12%→0%)", 
             ha='center', va='top', color='#A50F15', fontweight='bold', fontsize=14)
    
    ax1.text(180, y_max*0.15, "Phase III: Stable\n(Recovery Check)", 
             ha='center', va='top', color='#2CA02C', fontweight='bold', fontsize=14)

    # =========================================================
    # 5. 绘制核心曲线
    # =========================================================
    legend_lines = []
    legend_labels = []

    for algo in df_goodput.columns:
        if algo not in STYLES: continue
        s = STYLES[algo]
        
        # --- 左轴: Goodput (实线/粗线) ---
        l1, = ax1.plot(df_goodput.index, df_goodput[algo], 
                 color=s['color'], linewidth=s['lw'], linestyle=s['ls'], 
                 alpha=0.9, zorder=s['zorder'], label=s['label'])
        
        # 收集图例
        legend_lines.append(l1)
        legend_labels.append(s['label'])
        
        # --- 右轴: Recall (细点线) ---
        # 仅绘制两条 LODS 线以减少杂乱，Fixed-Robust 的 Recall 也是参考
        if 'LODS' in algo:
            ax2.plot(df_recall.index, df_recall[algo], 
                     color=s['color'], linewidth=3, linestyle=':', 
                     alpha=0.9, zorder=s['zorder'])

    # =========================================================
    # 6. 关键机理标注 (Recovery Lag)
    # =========================================================
    # 我们关注 Round 140-170 之间的区域
    # 0.30 应该在 Round 140 左右开始爬升
    # 0.10 应该在 Round 160 甚至更晚才爬升
    
    # 画一个箭头指向 0.10 的滞后区
    # 注意：具体坐标可能需要根据数据微调，这里是预估位置
    # ax1.annotate('Recovery Lag\n(Hysteresis)', 
    #              xy=(155, 2800), xycoords='data', # 箭头尖端 (假设 0.10 在这里还在低位)
    #              xytext=(135, 4000), textcoords='data', # 文字位置
    #              arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2", color='black', lw=1.5),
    #              fontsize=11, fontweight='bold', color='#1F77B4', 
    #              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#1F77B4", alpha=0.9))

    # # 标注 0.30 的快速响应
    # ax1.annotate('Fast Alignment\n(No Lag)', 
    #              xy=(145, 4500), xycoords='data', # 箭头尖端 (假设 0.30 已经飞升)
    #              xytext=(115, 5500), textcoords='data',
    #              arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-.2", color='#D62728', lw=1.5),
    #              fontsize=11, fontweight='bold', color='#D62728',
    #              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#D62728", alpha=0.9))

    # =========================================================
    # 7. 坐标轴调整
    # =========================================================
    ax1.set_xlabel("Simulation Round (Time)", fontweight='bold',fontsize=16)
    ax1.set_ylabel("Effective Goodput (tags/s)", fontweight='bold', color='#1F78B4')
    ax2.set_ylabel("Identification Reliability (Recall)", fontweight='bold', color='#E31A1C', rotation=270, labelpad=20)
    
    ax1.set_xlim(0, 200)
    ax1.set_ylim(0, y_max * 1.05) # 动态上限
    ax2.set_ylim(0.5, 1.02) # Recall 关注高位
    
    # 隐藏右轴刻度颜色，使其不喧宾夺主
    ax2.tick_params(axis='y', colors='gray')
    ax2.spines['right'].set_color('gray')

    # Grid
    ax1.grid(True, linestyle='--', alpha=0.5)

    # =========================================================
    # 8. 图例
    # =========================================================
    # 合并图例
    # 添加一个 dummy line 表示 Recall (Dotted)
    line_recall_dummy = Line2D([0], [0], color='gray', linestyle=':', lw=2, label='Reliability (Right Axis)')
    legend_lines.append(line_recall_dummy)
    legend_labels.append('Reliability (Right Axis)')
    
    ax1.legend(legend_lines, legend_labels, loc='lower center', 
               ncol=3, frameon=True, framealpha=0.95, 
               bbox_to_anchor=(0.5, 1.02), fontsize=14)

    # =========================================================
    # 9. 输出
    # =========================================================
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    pdf_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_NAME}.pdf")
    png_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_NAME}.png")
    
    plt.savefig(pdf_path, dpi=600, bbox_inches='tight')
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    
    print(f"✅ 绘图完成！")
    print(f"PDF: {pdf_path}")

if __name__ == "__main__":
    plot_recovery_analysis()