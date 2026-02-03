# -*- coding: utf-8 -*-
"""
Exp_Sup_2_Figure_V2_Optimized.py
实验二专属绘图 (Nature/Science 顶刊风格优化版)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import numpy as np
from scipy.stats import gaussian_kde
import matplotlib.transforms as transforms

# =========================================================
# 配置区
# =========================================================
INPUT_DIR = "Results_Exp_Sup_2"
INPUT_FILE = "raw_Micro_Dynamics_Combined.csv"
OUTPUT_DIR = "Paper_Figures/Exp_Sup_2_Micro_Dynamics"

# --- 顶刊级配色方案 (Nature/Science Style) ---
# 使用低饱和度、高辨识度的颜色
COLOR_IDEAL_FILL  = "#A6CEE3"    # 柔和蓝 (直方图填充)
COLOR_IDEAL_LINE  = "#1F78B4"    #以此为主的深蓝 (线条)
COLOR_STRESS_FILL = "#FB9A99"    # 柔和红 (直方图填充)
COLOR_STRESS_LINE = "#E31A1C"    # 深红 (线条)

# 背景区域颜色 (极淡，不抢视觉重心)
COLOR_SAFE_ZONE   = "#EDF8E9"    # 极淡的灰绿色
COLOR_IDEAL_ZONE  = "#EFF3FF"    # 极淡的灰蓝色

def get_kde_peak(data, bw_method=None):
    """
    辅助函数：计算数据的 KDE 峰值 (Mode)
    """
    if len(data) == 0: return 0
    kde = gaussian_kde(data, bw_method=bw_method)
    # 在数据范围内生成细密网格寻找最大值
    x_grid = np.linspace(min(data)*0.8, max(data)*1.2, 1000)
    y_grid = kde(x_grid)
    peak_x = x_grid[np.argmax(y_grid)]
    return peak_x, kde(peak_x)[0]

def draw_comparison_figure():
    csv_path = os.path.join(INPUT_DIR, INPUT_FILE)
    
    # 为了演示，如果文件不存在，生成模拟数据 (你可以删除这段)
    if not os.path.exists(csv_path):
        print(f"⚠️ Warning: {csv_path} not found. Generating dummy data for visual check...")
        os.makedirs(INPUT_DIR, exist_ok=True)
        # 模拟双峰数据
        np.random.seed(42)
        d1 = np.random.normal(32, 3, 1000)   # Stress
        d2 = np.random.normal(65, 2, 1000)   # Ideal
        df = pd.DataFrame({
            'K': np.concatenate([d1, d2]),
            'Scenario': ['Stress']*1000 + ['Ideal']*1000
        })
    else:
        df = pd.read_csv(csv_path)

    df_ideal = df[df['Scenario'].str.contains("Ideal")]
    df_stress = df[df['Scenario'].str.contains("Stress")]

    # =====================================================
    # 0. 画布设置 (使用 Arial 字体)
    # =====================================================
    # 宽长比 16:9 略微调整，适合双列排版
    fig, ax = plt.subplots(figsize=(8.5, 5)) 
    
    # 顶刊通常偏好无衬线字体 (Arial/Helvetica) 以提高图表可读性
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans'] 
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.linewidth'] = 1.0 # 坐标轴线宽

    # =====================================================
    # 1. 动态计算峰值 (实现完美居中对齐)
    # =====================================================
    # 计算 Stress 场景的峰值
    peak_stress_x, peak_stress_y = get_kde_peak(df_stress['K'], bw_method=0.5)
    # 计算 Ideal 场景的峰值
    peak_ideal_x, peak_ideal_y = get_kde_peak(df_ideal['K'], bw_method=1.0)
    
    print(f"🔍 Detected Peaks -> Stress: {peak_stress_x:.2f}, Ideal: {peak_ideal_x:.2f}")

    # =====================================================
    # 2. 绘制背景区域 (Layer 0 - 底层)
    # =====================================================
    # 2.1 Hyper-Stable Zone (绿色背景) - 居中对齐 Stress 峰值
    # 设定宽度为 12 (或基于标准差计算)
    zone_width_stress = 14
    rect_stress = patches.Rectangle((peak_stress_x - zone_width_stress/2, 0), zone_width_stress, 1.0, 
                                    linewidth=0, edgecolor='none', facecolor=COLOR_SAFE_ZONE, 
                                    transform=ax.get_xaxis_transform(), zorder=0)
    ax.add_patch(rect_stress)

    # 2.2 Ideal Zone (蓝色背景，可选) - 居中对齐 Ideal 峰值
    zone_width_ideal = 10
    rect_ideal = patches.Rectangle((peak_ideal_x - zone_width_ideal/2, 0), zone_width_ideal, 1.0, 
                                   linewidth=0, edgecolor='none', facecolor=COLOR_IDEAL_ZONE, 
                                   transform=ax.get_xaxis_transform(), zorder=0)
    ax.add_patch(rect_ideal)
    
    # 区域文字标注
    ax.text(peak_stress_x, 0.95, "Hyper-Stable Zone\n(Drift Resilient)", 
            ha='center', va='top', transform=ax.get_xaxis_transform(), 
            color='#2E8B57', fontsize=10, fontweight='bold', zorder=1)

    # =====================================================
    # 3. 数据绘制 (Layer 1 - 中层)
    # =====================================================
    bins = range(0, 145, 3) # 稍微细化 Bin
    
    # --- Stress Case (红色) ---
    sns.histplot(data=df_stress, x='K', bins=bins, stat='probability',
                 color=COLOR_STRESS_FILL, alpha=0.6, edgecolor='white', linewidth=0.5,
                 ax=ax, zorder=10, label='_nolegend_')
    
    # --- Ideal Case (蓝色) ---
    sns.histplot(data=df_ideal, x='K', bins=bins, stat='probability',
                 color=COLOR_IDEAL_FILL, alpha=0.4, edgecolor='white', linewidth=0.5,
                 ax=ax, zorder=5, label='_nolegend_')

    # KDE 曲线使用副轴 (Twinx)
    ax_kde = ax.twinx()
    
    sns.kdeplot(data=df_stress['K'], color=COLOR_STRESS_LINE, linewidth=3, 
                ax=ax_kde, bw_adjust=0.6, fill=False, zorder=11, label='Stress (Drift=10%): Robust')
    
    sns.kdeplot(data=df_ideal['K'], color=COLOR_IDEAL_LINE, linestyle='--', linewidth=2.5, 
                ax=ax_kde, bw_adjust=1.0, fill=False, zorder=6, label='Ideal (No Drift): High Speed')

    # =====================================================
    # 4. 关键标注与修饰 (Layer 2 - 顶层)
    # =====================================================
    
    # A. 动态迁移箭头 (基于计算出的峰值连接)
    # 箭头起点：Ideal 峰值, 终点：Stress 峰值 + 偏移
    arrow_y = ax_kde.get_ylim()[1] * 0.45
    
    style = patches.ArrowStyle("->", head_length=0.6, head_width=0.4)
    arrow = patches.FancyArrowPatch((peak_ideal_x - 5, arrow_y), (peak_stress_x + 5, arrow_y),
                                    connectionstyle="arc3,rad=-0.2", 
                                    color='#333333', arrowstyle=style,
                                    linestyle='--', linewidth=2, zorder=20)
    ax_kde.add_patch(arrow)

    # 箭头文字
    t = ax_kde.text((peak_stress_x + peak_ideal_x)/2, arrow_y * 1.3, 
                    "Adaptive Constraint\n(Active Migration)", 
                    ha='center', va='bottom', fontsize=10, color='#333333', fontweight='bold')
    # 给文字加个白色半透明底，防止遮挡曲线
    t.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))

    # B. K_max 阈值线
    ax.axvline(x=128, color='#777777', linestyle=':', linewidth=1.5, zorder=1)
    ax.text(125, 0.7, " $K_{max}=128$", ha='right', va='bottom', 
            color='#555555', fontsize=12, transform=ax.get_xaxis_transform())

    # =====================================================
    # 5. 轴系美化 (Clean Layout)
    # =====================================================
    # 去除上方和右侧边框 (Despine) - 现代顶刊标准
    # ax.spines['top'].set_visible(False)
    # ax.spines['right'].set_visible(False)
    # ax_kde.spines['top'].set_visible(False)
    # ax_kde.spines['right'].set_visible(False)
    ax_kde.spines['left'].set_visible(False) # KDE 轴通常不需要显示左轴线

    # 坐标轴标签
    ax.set_xlabel("Dynamic Batch Size ($K$)", fontsize=13, fontweight='bold', labelpad=10)
    ax.set_ylabel("Probability / Frequency", fontsize=13, fontweight='bold', labelpad=10)
    ax.set_xlim(0, 145)
    
    # 隐藏 KDE 的 Y 轴刻度 (因为这是双轴，避免混淆)
    ax_kde.set_yticks([])
    ax_kde.set_ylabel("")

    # 设置 Y 轴上限，留出头部空间
    hist_max = np.histogram(df_stress['K'], bins=bins, density=False)[0].max() / len(df_stress)
    ax.set_ylim(0, hist_max * 1.4) # 留出 40% 头部空间给图例和文字
    ax_kde.set_ylim(0, ax_kde.get_ylim()[1] * 1.2)

    # 网格线：轻微的灰色，置于底层
    ax.grid(axis='y', linestyle='--', alpha=0.3, color='gray', zorder=0)

    # =====================================================
    # 6. 自定义无边框图例
    # =====================================================
    # 手动创建图例句柄，确保形状美观
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=COLOR_IDEAL_LINE, lw=2.5, linestyle='--', label='Ideal (No Drift)'),
        Line2D([0], [0], color=COLOR_STRESS_LINE, lw=3, label='Stress (Robust)'),
        patches.Patch(facecolor=COLOR_SAFE_ZONE, label='Stable Zone'),
    ]
    
    ax.legend(handles=legend_elements, loc='upper right', 
              fontsize=12, frameon=False, ncol=1) # frameon=False 去掉边框

    plt.tight_layout()

    # 保存
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    save_path = os.path.join(OUTPUT_DIR, "Fig_Sup_2_Micro_Dynamics_Publication.pdf")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(OUTPUT_DIR, "Fig_Sup_2_Micro_Dynamics_Publication.png"), dpi=300, bbox_inches='tight')
    
    print(f"🎉 绘图完成！已生成符合出版标准的图片：\n -> {save_path}")

if __name__ == "__main__":
    draw_comparison_figure()