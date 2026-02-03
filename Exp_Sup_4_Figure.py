# -*- coding: utf-8 -*-
"""
Exp_Sup_4_Figure_Final.py
实验四专属绘图：自适应容忍度阈值敏感性分析 (Tolerance Sensitivity)
版本: Final (IEEE Transactions Style)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.lines import Line2D

# =========================================================
# 配置区
# =========================================================
INPUT_DIR = "Results_Exp_Sup_4"
OUTPUT_DIR = "Paper_Figures/Exp_Sup_4_Tolerance"

# 必须存在的文件
FILE_GOODPUT = "raw_Goodput.csv"
FILE_RECALL = "raw_Recall.csv"

# --- 用户指定的配色方案 ---
COLOR_IDEAL_FILL  = "#A6CEE3"    # 柔和蓝 (Goodput 填充)
COLOR_IDEAL_LINE  = "#1F78B4"    #以此为主的深蓝 (Goodput 线条)
COLOR_STRESS_FILL = "#FB9A99"    # 柔和红 (未使用，留作备用)
COLOR_STRESS_LINE = "#E31A1C"    # 深红 (Reliability 线条)
COLOR_SAFE_ZONE   = "#EDF8E9"    # 极淡的灰绿色 (Sweet Spot 背景)
COLOR_IDEAL_ZONE  = "#EFF3FF"    # 极淡的灰蓝色 (未使用)

def apply_paper_style():
    """应用论文标准字体 (Times New Roman)"""
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'mathtext.fontset': 'stix',
        'font.size': 12,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12,
        'axes.linewidth': 1.0
    })

def draw_sensitivity_figure():
    apply_paper_style()
    
    # 1. 读取数据 (使用全量数据更稳健)
    path_raw = os.path.join(INPUT_DIR, "00_Raw_Full_Data.csv")
    if not os.path.exists(path_raw):
        print(f"⚠️ 全量数据 {path_raw} 未找到，尝试读取拆分文件...")
        # 备选方案: 如果全量文件不在，说明 Tool.py 版本不同，请确保数据存在
        return
        
    df_raw = pd.read_csv(path_raw)
    
    # 聚合数据
    if 'Tolerance_Threshold' not in df_raw.columns:
        print("⚠️ 'Tolerance_Threshold' 列未找到，无法绘图。")
        return

    df_agg = df_raw.groupby('Tolerance_Threshold')[['Goodput', 'Recall']].mean().reset_index()
    df_agg = df_agg.sort_values('Tolerance_Threshold')

    X = df_agg['Tolerance_Threshold']
    Y_goodput = df_agg['Goodput']
    Y_recall = df_agg['Recall']

    # =====================================================
    # 2. 画布设置
    # =====================================================
    fig, ax1 = plt.subplots(figsize=(8, 5))
    
    # 3. 绘制 Sweet Spot 背景 (Layer 0)
    # A. 填充区域 (关闭默认边框)
    ax1.axvspan(0.25, 0.40, facecolor=COLOR_SAFE_ZONE, edgecolor='none', alpha=1.0, zorder=0)
    
    # B. 绘制垂直方向的虚线边框
    # 注：为了视觉可见性，这里使用了文字标签的深绿色 (#2E7D32)
    # 如果您严格需要与填充色 (#EDF8E9) 完全一致，请将 color 改为 COLOR_SAFE_ZONE
    border_color = '#2E7D32' 
    ax1.axvline(x=0.25, linestyle='--', color=border_color, linewidth=1.5, alpha=0.6, zorder=1)
    ax1.axvline(x=0.40, linestyle='--', color=border_color, linewidth=1.5, alpha=0.6, zorder=1)
    
    # C. 标注文字 (保持您之前要求的上移位置，例如 0.20)
    import matplotlib.transforms as transforms
    trans = transforms.blended_transform_factory(ax1.transData, ax1.transAxes)
    
    ax1.text(0.325, 0.48, "Safe Operating Area\n" + r"($\epsilon \approx 0.30$)", 
             ha='center', va='bottom', color='#2E7D32', fontsize=11, fontweight='bold',
             transform=trans, zorder=1)

    # =====================================================
    # 4. 绘制 Goodput (左轴, 蓝色) (Layer 1)
    # =====================================================
    ln1 = ax1.plot(X, Y_goodput, color=COLOR_IDEAL_LINE, marker='o', markersize=7, 
                   markeredgecolor='white', markeredgewidth=1.0,
                   linewidth=2.5, label='Effective Goodput')
    
    # 填充颜色
    ax1.fill_between(X, 0, Y_goodput, color=COLOR_IDEAL_FILL, alpha=0.4)
    
    ax1.set_xlabel(r"Tolerance Threshold ($\epsilon$)", fontweight='bold')
    ax1.set_ylabel("Effective Goodput (tags/s)", fontweight='bold', color=COLOR_IDEAL_LINE)
    ax1.tick_params(axis='y', labelcolor=COLOR_IDEAL_LINE)
    
    # 动态设置 Y 轴上限 (留 20% 空间)
    y_max_g = Y_goodput.max()
    ax1.set_ylim(0, y_max_g * 1.25) 
    
    # 标注 Peak (放置在点左侧或内部，避免溢出)
    max_idx = Y_goodput.idxmax()
    peak_x = X[max_idx]
    peak_y = Y_goodput[max_idx]
    
    # 只有当 Peak 在右侧边缘时，向左指；否则向上指
    # 这里峰值可能在最右边 (epsilon=0.6)，所以文字放在左上角比较安全
    ax1.annotate(f'Peak: {peak_y:.0f}', 
                 xy=(peak_x, peak_y), 
                 xytext=(peak_x + 0.02, peak_y + 450), # 向左平移
                 arrowprops=dict(facecolor='black', arrowstyle='->', connectionstyle="arc3,rad=0.1"),
                 ha='right', fontsize=11, fontweight='bold', color='black')

    # =====================================================
    # 5. 绘制 Reliability (右轴, 红色) (Layer 2)
    # =====================================================
    ax2 = ax1.twinx()
    ln2 = ax2.plot(X, Y_recall, color=COLOR_STRESS_LINE, marker='s', markersize=6, 
                   markeredgecolor='white', markeredgewidth=1.0,
                   linestyle='--', linewidth=2.5, label='Recall')
    
    ax2.set_ylabel("Recall", fontweight='bold', color=COLOR_STRESS_LINE)
    ax2.tick_params(axis='y', labelcolor=COLOR_STRESS_LINE)
    ax2.set_ylim(0.5, 1.05) # 稍微超过 1.0 以容纳图例
    
    # 标注 Reliability Cliff (关键！)
    # 寻找下跌点 (Recall < 0.95 的起始点)
    cliff_mask = (X > 0.45) & (Y_recall < 0.95)
    if cliff_mask.any():
        cliff_point = df_agg[cliff_mask].head(1)
        cx = cliff_point['Tolerance_Threshold'].values[0]
        cy = cliff_point['Recall'].values[0]
        
        # 文字放在点的左下方，箭头指向点，确保在框内
        ax2.annotate('Reliability Cliff\n(Over-aggressive)', 
                     xy=(cx, cy), 
                     xytext=(cx - 0.05, cy - 0.08), # 文字位置: 左下
                     arrowprops=dict(facecolor=COLOR_STRESS_LINE, edgecolor=COLOR_STRESS_LINE, 
                                     arrowstyle='->', connectionstyle="arc3,rad=-0.2"),
                     color=COLOR_STRESS_LINE, ha='center', fontsize=11, fontweight='bold')

    # =====================================================
    # 6. 图例与美化
    # =====================================================
    # 合并图例，放置在顶部中间 (ax2 的坐标系)
    lns = ln1 + ln2
    labs = [l.get_label() for l in lns]
    
    # 放在图的顶部，边框内
    ax1.legend(lns, labs, loc='upper center', bbox_to_anchor=(0.5, 1.15), 
               ncol=2, frameon=False, fontsize=14)

    # 细化网格 (仅对左轴)
    ax1.grid(True, linestyle=':', alpha=0.5, color='gray')
    
    plt.tight_layout()

    # 保存
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    save_path_pdf = os.path.join(OUTPUT_DIR, "Fig_Sup_4_Tolerance_Sensitivity.pdf")
    save_path_png = os.path.join(OUTPUT_DIR, "Fig_Sup_4_Tolerance_Sensitivity.png")
    
    plt.savefig(save_path_pdf, dpi=300, bbox_inches='tight')
    plt.savefig(save_path_png, dpi=300, bbox_inches='tight')
    
    print(f"🎉 绘图完成！\nPDF: {save_path_pdf}\nPNG: {save_path_png}")

if __name__ == "__main__":
    draw_sensitivity_figure()