# -*- coding: utf-8 -*-
"""
Exp_Sup_1_Change_Figure.py (Optimized for Publication)
物理帧长抗漂移对比绘图

【修改说明】
1. 字体: 全局 Times New Roman, 字号适配 IEEE 双栏标准。
2. 配色: 采用高对比度学术配色 (Deep Blue vs Teal Green)。
3. 尺寸: 放大至 8x6 英寸，提升清晰度。
4. 路径: 严格保留原始内容。
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# =========================================================
# 🎨 配置区
# =========================================================
INPUT_DIR = "Results_Exp_Sup_1_Change"
INPUT_FILE = "Payload_Drift_Comparison.csv"
OUTPUT_DIR = "Paper_Figures/Exp_Sup_1_Theoretical_Validation"

# --- 顶刊配色方案 (High-Contrast) ---
# 蓝色 (Long Frame - Brittle): 深沉、稳重
COLOR_256 = "#D62728"  
# 绿色 (Short Frame - Robust): 鲜明、具有通过性 (使用 Teal Green 提升高级感)
COLOR_128 = "#009E73"  

def apply_publication_style():
    """应用 IEEE 期刊绘图风格"""
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Liberation Serif'],
        'mathtext.fontset': 'stix', # 确保公式字体也是 Times 风格
        'font.size': 14,
        'axes.labelsize': 18,       # 坐标轴标签字号
        'axes.titlesize': 18,
        'xtick.labelsize': 16,      # 刻度字号
        'ytick.labelsize': 16,
        'legend.fontsize': 14,
        'lines.linewidth': 2.5,     # 线宽加粗
        'lines.markersize': 10,     # 点加粗
        'figure.dpi': 300,
        'savefig.bbox': 'tight',
        'grid.linestyle': '--',
        'grid.alpha': 0.5,
    })

def draw_validation_figure():
    # 应用样式
    apply_publication_style()

    csv_path = os.path.join(INPUT_DIR, INPUT_FILE)
    if not os.path.exists(csv_path):
        print(f"❌ 错误: 找不到数据文件 {csv_path}")
        print("   请先运行 Exp_Sup_1_Change.py 生成数据。")
        return

    # 1. 读取数据
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ 读取CSV失败: {e}")
        return
    
    # 2. 初始化画布 (放大尺寸: 8x6)
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 3. 绘制折线图 (带置信区间)
    # Payload = 256 (Baseline) -> Brittle
    sns.lineplot(data=df[df['Payload_Bits'] == 256], x='Drift_Percent', y='Recall',
                 color=COLOR_256, marker='o', markersize=10, linewidth=2.5,
                 label='Long Payload Bits ($L_{phy}=256$ bits)', ax=ax, ci=95) # 显示置信区间

    # Payload = 128 (Optimized) -> Robust
    sns.lineplot(data=df[df['Payload_Bits'] == 128], x='Drift_Percent', y='Recall',
                 color=COLOR_128, marker='^', markersize=10, linewidth=2.5,
                 label='Short Payload Bits ($L_{phy}=128$ bits)', ax=ax, ci=95)

    # 4. 添加关键物理边界线 (Theoretical Limits)
    # 理论崩溃点 A: 0.2%
    ax.axvline(x=0.2, color=COLOR_256, linestyle='--', linewidth=2, alpha=0.7)
    # 文本背景框，防止与网格线混淆
    ax.text(0.205, 0.45, "Limit for 256b\n($\\delta \\approx 0.2\\%$)", 
            color=COLOR_256, fontsize=14, ha='left', va='center', fontweight='bold',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))

    # 理论崩溃点 B: 0.4%
    ax.axvline(x=0.4, color=COLOR_128, linestyle='--', linewidth=2, alpha=0.7)
    ax.text(0.405, 0.60, "Limit for 128b\n($\\delta \\approx 0.4\\%$)", 
            color=COLOR_128, fontsize=14, ha='left', va='center', fontweight='bold',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))

    # 5. 添加标注箭头 (验证公式)
    # 使用 annotate 绘制双向箭头
    ax.annotate('', xy=(0.4, 0.35), xytext=(0.2, 0.35),
                arrowprops=dict(arrowstyle='<->', color='black', lw=2))
    # 文字说明
    ax.text(0.3, 0.37, "Tolerance Doubled", ha='center', va='bottom', 
            fontsize=14, fontweight='bold', color='#333333')

    # 6. 坐标轴美化
    ax.set_xlabel("Clock Drift Rate (%)", fontweight='bold')
    ax.set_ylabel("Identification Reliability", fontweight='bold')
    
    # 设置范围和刻度
    ax.set_ylim(0.0, 1.05) # 稍微留一点头部空间
    ax.set_xlim(0, 0.6)    # 聚焦
    
    # 增加次刻度 (Minor Ticks) 使图表更显专业
    ax.minorticks_on()
    ax.tick_params(which='minor', direction='in', length=3)
    ax.tick_params(which='major', direction='in', length=6)

    # 网格线设置: 主网格明显，次网格隐约
    ax.grid(which='major', linestyle='--', linewidth=0.75, alpha=0.6)
    ax.grid(which='minor', linestyle=':', linewidth=0.5, alpha=0.3)

    # 图例优化
    # frameon=False 更现代，或者 framealpha=0.9 保持清晰
    ax.legend(loc='lower left', frameon=True, framealpha=0.35, edgecolor='gray', fancybox=False)
    
    plt.tight_layout()

    # 7. 保存
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    save_path = os.path.join(OUTPUT_DIR, "Fig_Sup_1_Theoretical_Validation.pdf")
    png_path = os.path.join(OUTPUT_DIR, "Fig_Sup_1_Theoretical_Validation.png")
    
    plt.savefig(save_path)
    plt.savefig(png_path)
    
    print(f"🎉 绘图完成！")
    print(f"   尺寸: 8x6 inches | 字体: Times New Roman")
    print(f"   保存路径: {save_path}")

if __name__ == "__main__":
    draw_validation_figure()