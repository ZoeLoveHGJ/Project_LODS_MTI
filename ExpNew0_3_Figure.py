# -*- coding: utf-8 -*-
"""
Plot_Exp0_3.py
Refactored for Top-Tier Journal Standards (IEEE/ACM/Nature Sub-journals).
Features: Log-scale X-axis, Academic Color Palette, Minimalist Layout.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
import numpy as np

# =========================================================
# 1. 全局配置与科研样式设定 (Journal Quality Config)
# =========================================================
DATA_DIR = "Results_ExpNew0_3"
OUTPUT_DIR = os.path.join("Paper_Figures", "ExpNew0_3_Group_Size")
OUTPUT_NAME = "Fig_Exp0_3_Group_Size"

# 定义高级配色方案
COLORS = {
    'primary_line': '#FB7878',      # 深蓝 (Science/Nature 常用)
    'fill_area':    '#BCD6AD',      # 与线同色，后续透明度处理
    'highlight':    '#8076a3',      # 深红，用于强调最优值
    'grid':         '#e0e0e0',      # 极淡的灰色网格
    'text':         '#333333'       # 深灰字体，比纯黑柔和
}

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'mathtext.fontset': 'stix',     # 完美的 LaTeX 数学公式渲染
    'font.size': 12,                # 基础字号
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'axes.linewidth': 1.2,          # 边框线宽
    'lines.linewidth': 2.0,         # 曲线线宽
    'xtick.direction': 'out',       # 刻度朝外，现代风格更常用，或者 'in' 视具体期刊要求
    'ytick.direction': 'out',
    'legend.frameon': False,        # 图例去边框
    'figure.dpi': 300,
})

def plot_optimization_curve():
    # =========================================================
    # 2. 数据加载
    # =========================================================
    csv_path = os.path.join(DATA_DIR, "raw_Throughput.csv")
    
    if not os.path.exists(csv_path) and not os.path.exists(DATA_DIR):
        print("⚠️ 演示模式：正在生成模拟数据...")
        os.makedirs(DATA_DIR, exist_ok=True)
        # 模拟典型的对数增长数据
        k_vals = [4, 8, 16, 24, 32, 48, 64, 128, 256]
        # 模拟吞吐量：先快后慢，最后饱和
        t_vals = [1800, 3200, 4200, 6800, 6850, 9700, 10500, 11706, 11710]
        pd.DataFrame({'GroupSize': k_vals, 'Throughput': t_vals}).to_csv(csv_path, index=False)

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Error: File not found at {csv_path}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 数据预处理
    if 'GroupSize' in df.columns:
        df.set_index('GroupSize', inplace=True)
    elif df.index.name != 'GroupSize' and 'GroupSize' not in df.columns:
        df.set_index(df.columns[0], inplace=True)
    
    df.sort_index(inplace=True)
    
    x = df.index.values
    y = df.iloc[:, 0].values # 取第一列数据

    # =========================================================
    # 3. 创建画布与核心绘制
    # =========================================================
    # 宽高比建议：4:3 或 1.618 (黄金分割)
    fig, ax = plt.subplots(figsize=(7, 5)) 

    # --- 关键修改：设置 X 轴为 Log Scale (Base 2) ---
    ax.set_xscale('log', base=2)

    # 绘制主曲线
    ax.plot(x, y, 
            color=COLORS['primary_line'], 
            marker='o', 
            linestyle='-', 
            linewidth=2.0, 
            markersize=6,       # 稍微调小，显得精致
            markeredgecolor='white', # 增加白边，增加层次感
            markeredgewidth=1.5,
            label='System Throughput',
            zorder=5)

    # 填充区域 (Opacity adjusted)
    ax.fill_between(x, y, alpha=0.4, color=COLORS['fill_area'], zorder=1)

    # =========================================================
    # 4. 寻找并高亮标注峰值 (Elegant Annotation)
    # =========================================================
    max_idx = np.argmax(y)
    max_y = y[max_idx]
    max_x = x[max_idx]

    # 高亮最佳点：不再用巨大的五角星，而是用高对比度的实心点
    ax.plot(max_x, max_y, 
            marker='o', 
            markersize=8, 
            color=COLORS['highlight'], # 红色高亮
            markeredgecolor='white', 
            markeredgewidth=1.5,
            zorder=10)

    # 精细标注
    # 文字位置：放在点的左上方或正上方，留出空间
    # 格式化：使用 LaTeX 语法
    label_text = r"$\bf{Optimal\ Point}$" + "\n" + f"$K={max_x}$\n$T={max_y:.0f}$"
    
    ax.annotate(label_text, 
                xy=(max_x, max_y), 
                xytext=(max_x, max_y * 0.85), # 将文字放在点下方，避免遮挡顶部空间
                # 如果点在右侧边缘，也可以考虑 xytext=(max_x*0.5, max_y) 放左边
                textcoords='data',
                arrowprops=dict(arrowstyle='->', 
                                color='#555555', 
                                lw=1.2, 
                                connectionstyle="arc3,rad=0.1"), # 轻微弧度
                fontsize=11, 
                color=COLORS['text'],
                ha='center', 
                va='top')

    # =========================================================
    # 5. 坐标轴深度优化
    # =========================================================
    ax.set_xlabel("Group Size $K$ (Log Scale)", fontweight='bold')
    ax.set_ylabel("System Throughput (tags/s)", fontweight='bold')

    # --- 网格与边框 ---
    # 去掉上方和右侧的边框 (Spines)，这是现代科研图表的标准做法
    # ax.spines['top'].set_visible(False)
    # ax.spines['right'].set_visible(False)
    
    # 网格线：仅保留主网格，且颜色极淡
    ax.grid(True, which='major', linestyle='--', color=COLORS['grid'], alpha=0.7)
    
    # --- 刻度控制 ---
    # 强制显示数据中存在的 K 值
    # 使用 ScalarFormatter 避免显示为 2^3, 2^4，而是显示 8, 16...
    ax.set_xticks(x)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    
    # Y轴范围微调
    ax.set_ylim(bottom=0, top=max_y * 1.15) # 顶部留出 15% 空间给标注

    # =========================================================
    # 6. 保存输出
    # =========================================================
    plt.tight_layout()
    
    pdf_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_NAME}.pdf")
    png_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_NAME}.png")
    
    plt.savefig(pdf_path, dpi=600, format='pdf', bbox_inches='tight')
    plt.savefig(png_path, dpi=300, format='png', bbox_inches='tight')

    print(f"📊 顶级期刊风格绘图完成！")
    print(f"   PDF: {pdf_path}")
    print(f"   PNG: {png_path}")
    
    plt.show()

if __name__ == "__main__":
    plot_optimization_curve()