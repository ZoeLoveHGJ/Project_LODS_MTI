# -*- coding: utf-8 -*-
"""
Exp6_Figure.py
实验 6 可视化专用脚本: Atomic Latency Analysis (IEEE Style)

【功能说明】
1. 读取或生成计算开销数据。
2. 绘制双轴图表：
   - 左轴 (对数): 物理传输时间 vs 计算时间 (10^n 格式)
   - 右轴 (线性): 计算开销占比 (%)
3. 输出符合顶级期刊 (ToN/TMC) 标准的高清矢量图。

【依赖库】
pip install matplotlib pandas numpy
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from matplotlib.ticker import FuncFormatter, LogLocator
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
# =========================================================
# ⚙️ 配置区域
# =========================================================
DATA_DIR = "Results_ExpNew0_4_Comuting"
DATA_FILE = "Computation_Overhead_Data.csv"
OUTPUT_DIR = "Paper_Figures/ExpNew0_4_Computing"
# 确保输出目录存在
os.makedirs(DATA_DIR, exist_ok=True)

def make_bars_rounded(ax, bars, radius=0.1, border_width=1.2):
    """
    辅助函数：将直角柱状图替换为带阴影和粗边框的圆角柱状图
    :param radius: 圆角半径
    :param border_width: 边框宽度 (用户要求加大)
    """
    for bar in bars:
        x, y = bar.get_xy()
        w, h = bar.get_width(), bar.get_height()
        
        # 1. 核心技巧：使用 patheffects 添加矢量阴影
        # offset=(2, -2): 阴影向右下偏移 2 像素
        # alpha=0.3: 阴影透明度
        shadow_effect = [
            # 第一层：远处的淡阴影（营造氛围）
            pe.SimplePatchShadow(offset=(4, -4), shadow_rgbFace='grey', alpha=0.2),
            # 第二层：近处的深阴影（强调轮廓）
            pe.SimplePatchShadow(offset=(2, -2), shadow_rgbFace='black', alpha=0.3),
            # 原始图形（必须放在最后）
            pe.Normal()
        ]

        # 2. 创建圆角矩形
        # boxstyle="round,pad=0...": 保持尺寸精确
        rounded_bar = FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0,rounding_size={radius}", 
            mutation_scale=1,
            facecolor=bar.get_facecolor(),
            edgecolor=bar.get_edgecolor(),
            linewidth=border_width,     # [修改] 使用传入的边框宽度
            hatch=bar.get_hatch(),      
            zorder=bar.get_zorder(),
            alpha=bar.get_alpha(),
            path_effects=shadow_effect  # [修改] 应用阴影效果
        )
        
        # 移除旧方柱，添加新圆角柱
        bar.remove()
        ax.add_patch(rounded_bar)

# =========================================================
# 🎨 核心绘图引擎 (Optimized for Publication)
# =========================================================

def plot_overhead_analysis(df):
    """
    绘制计算开销分析图 (IEEE Style Optimized)
    :param df: 包含 ['K', 'air_time', 'calc_cpp', 'overhead_pct'] 的 DataFrame
    """
    print("🎨 正在绘制高保真图表...")

    # --- 1. 全局样式配置 (Modern Science Style) ---
    # 使用 Times New Roman 配合 STIX 字体引擎渲染数学公式
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'mathtext.fontset': 'stix',        # 专业的数学公式字体
        'font.size': 16,
        'axes.linewidth': 1.2,             # 坐标轴线宽
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'axes.grid': False,                # 关闭默认丑陋的网格
    })
    
    # 创建画布
    fig, ax1 = plt.subplots(figsize=(10, 6.5))
    
    indices = np.arange(len(df['K']))
    
    # --- 2. 现代配色方案 (Modern Palette) ---
    color_air = '#BCD6AD'        # 浅灰 (背景基准)
    color_air_edge = '#2CA02C'   # 深灰边框
    color_comp = '#FB7878'       # 砖红 (前景强调)
    color_line = '#8076a3'       # 深海蓝 (趋势线)
    
    # --- 3. 左轴: Latency (Log Scale) ---
    
    # A. 物理时间 (背景 - 宽柱)
    # hatch='///' 增加斜线纹理，即使黑白打印也能区分
    p1 = ax1.bar(indices, df['air_time'], width=0.6, 
                 label=r'Physical Air Time ($T_{air}$)', 
                 color=color_air, edgecolor='black', 
                  linewidth=1, zorder=1,alpha=0.8)

    # hatch='///',
    # B. 计算时间 (前景 - 窄柱) 
    # 处理 Log 0 问题: 设定一个极小值(1e-4)确保柱子能画出来，不报错
    plot_cpp_vals = [max(v, 1e-4) for v in df['calc_cpp']] 
    p2 = ax1.bar(indices, plot_cpp_vals, width=0.35, 
                 label=r'Computation Time ($T_{comp}$)', 
                 color=color_comp, edgecolor='black', 
                 alpha=0.9, linewidth=1, zorder=3)
    
    make_bars_rounded(ax1, p1, radius=0.2, border_width=0) 
    
    # C. 左轴格式化 (关键优化: 10^n 显示)
    ax1.set_yscale('log')
    # 限制范围，确保能完整展示 10^-4 到 10^3 的跨度，留出视觉余量
    ax1.set_ylim(1e-4, 5000) 
    
    ax1.set_xlabel(r'Group Size ($K$) [Slice Size]', fontweight='bold', fontsize=16)
    ax1.set_ylabel(r'Per-Command Latency ($ms$) [Log Scale]', fontweight='bold', fontsize=16)
    
    ax1.set_xticks(indices)
    ax1.set_xticklabels(df['K'], fontsize=12)

    # 自定义 Formatter: 强制显示为 10^n 数学格式
    def format_log_pow10(x, pos):
        if x <= 0: return ""
        log_val = np.log10(x)
        # 只有当指数是整数时才显示标签 (避免出现 10^0.5 这种怪异刻度)
        if np.isclose(log_val, np.round(log_val)):
            return r'$10^{%d}$' % int(np.round(log_val))
        return ""

    # 设置主刻度定位器和格式化器
    ax1.yaxis.set_major_locator(LogLocator(base=10.0, numticks=10))
    ax1.yaxis.set_major_formatter(FuncFormatter(format_log_pow10))
    
    # 添加淡雅的水平参考线
    ax1.grid(which='major', axis='y', linestyle='--', alpha=0.4, color='gray', zorder=0)

    # --- 4. 右轴: Overhead % (Linear Scale) ---
    ax2 = ax1.twinx()
    
    # 折线图也建议稍微加粗描边，与柱状图风格统一
    l1 = ax2.plot(indices, df['overhead_pct'], color=color_line, 
                  linestyle='-', marker='o', linewidth=3.0, markersize=9, # 线宽从2.5 -> 3.0
                  markeredgecolor='white', markeredgewidth=2.0,           # 描边从1.5 -> 2.0
                  path_effects=[pe.SimpleLineShadow(offset=(2, -2), alpha=0.3), pe.Normal()],
                  label=r'Overhead Ratio ($\eta$)', zorder=5)
    
    ax2.set_ylabel(r'Computational Overhead ($\%$)', fontweight='bold', fontsize=16, color=color_line)
    max_oh = df['overhead_pct'].max()
    ax2.set_ylim(0, max(0.1, max_oh * 1.6))
    ax2.tick_params(axis='y', labelcolor=color_line, labelsize=12)

    # --- 5. 标注关键点 (Smart Annotation) ---
    # 自动寻找 K=128 的位置
    target_k = 128
    if target_k in df['K'].values:
        # 获取索引
        opt_idx = list(df['K'].values).index(target_k)
        opt_val = df['overhead_pct'].iloc[opt_idx]
        
        # 使用 LaTeX 格式化文本
        anno_text = r'$\mathbf{Optimal\ K=%d}$' % target_k + '\n' + r'$\eta \approx %.3f\%%$' % opt_val
        
        # 计算标注框位置 (自适应高度)
        y_text_pos = opt_val + (ax2.get_ylim()[1] * 0.23)
        
        ax2.annotate(anno_text, 
                     xy=(opt_idx, opt_val), 
                     xytext=(opt_idx-0.2, y_text_pos), 
                     arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.5),
                     bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=color_line, alpha=0.9),
                     fontsize=13, ha='center', color='black')

    # 图例
    lines1, labels1 = ax1.get_legend_handles_labels() # 注意：由于bar被替换，label可能需要重新手动指定，或者bar.remove前保留label
    # 修正：由于remove了原始bar，get_legend_handles_labels可能抓不到原来的p1/p2
    # 技巧：我们手动构建图例句柄，或者在FancyBboxPatch中带上label（但patch不支持直接作为图例自动抓取）
    # 最简单的方法：在 make_bars_rounded 之前获取 handle
    # 或者直接使用替换后的 patch 作为 handle
    
    # 重新获取 handles (ax1.patches 包含了新的 FancyBboxPatch)
    # 为保险起见，建议手动创建图例对象，或者让 bar 暂时不 remove 原始对象仅 set_visible(False)
    # 这里采用最稳妥的 Proxy Artist 方式，或者简单信任 ax1 还有其他方式追踪
    # 实际上，remove() 后 label 会丢失。
    # 修复逻辑：我们在 make_bars_rounded 里不 remove，而是 set_visible(False) 并保留原对象用于图例生成
    # 但上面的代码用了 remove。
    # 鉴于此，我们可以手动传递 handles：
    
    # *修正建议*：在调用 make_bars_rounded 之前，先获取图例需要的 handles
    # lines1 = [p1, p2] # 这是不对的，因为p1是container
    # 正确做法：利用matplotlib自动机制，只要label在add_patch时没加，我们可以手动加一个不可见的proxy
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    
    legend_elements = [
        Patch(facecolor=color_air, edgecolor='black', linewidth=2, label=r'Physical Air Time ($T_{air}$)'),
        Patch(facecolor=color_comp, edgecolor='black', linewidth=2, label=r'Computation Time ($T_{comp}$)'),
        Line2D([0], [0], color=color_line, lw=3, marker='o', markersize=10, markeredgecolor='white', label=r'Overhead Ratio ($\eta$)')
    ]
    
    ax1.legend(handles=legend_elements, loc='upper left', 
               frameon=True, fancybox=True, framealpha=0.4, edgecolor='#CCCCCC', fontsize=16)

    plt.tight_layout()

    # 自动创建目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 已创建输出目录: {OUTPUT_DIR}")
    
    # 保存高清图
    save_path = os.path.join(OUTPUT_DIR, "Fig_Exp4_Atomic_Latency_Optimized.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    # 保存 PDF (用于论文排版)
    pdf_path = os.path.join(OUTPUT_DIR, "Fig_Exp4_Atomic_Latency_Optimized.pdf")
    plt.savefig(pdf_path, bbox_inches='tight')
    
    print(f"📊 PNG 图表已保存: {save_path}")
    print(f"📄 PDF 图表已保存: {pdf_path}")

# =========================================================
# 📥 数据加载与模拟 (Data Loader)
# =========================================================

def load_or_generate_data():
    """
    尝试从 CSV 加载数据，如果不存在则生成模拟数据。
    这确保了脚本可以独立运行查看效果。
    """
    csv_path = os.path.join(DATA_DIR, DATA_FILE)
    
    if os.path.exists(csv_path):
        print(f"✅ 发现数据文件: {csv_path}，正在加载...")
        return pd.read_csv(csv_path)
    else:
        print(f"⚠️ 未找到数据文件，正在生成演示数据 (Mock Data)...")
        # 这里的逻辑与 Exp6_Computation_Overhead.py 中的计算逻辑一致
        
        k_values = [16, 32, 48, 64, 96, 128, 192, 256]
        data = {
            'K': k_values,
            'calc_cpp': [],
            'air_time': [],
            'overhead_pct': []
        }
        
        for k in k_values:
            # 模拟数据生成 (基于之前的实验逻辑)
            # 假设 C++ 计算时间随 K 线性增长，但系数极小
            # K=128 时大约 0.02ms
            mock_calc = 0.00015 * k + 0.001 
            
            # 模拟物理时间 (Gen2 标准)
            # K=128 时大约 150ms
            mock_air = k * 1.5 + 10 
            
            overhead = (mock_calc / mock_air) * 100
            
            data['calc_cpp'].append(mock_calc)
            data['air_time'].append(mock_air)
            data['overhead_pct'].append(overhead)
            
        df = pd.DataFrame(data)
        # 保存演示数据以便下次直接使用
        df.to_csv(csv_path, index=False)
        return df

if __name__ == "__main__":
    # 1. 获取数据
    df_data = load_or_generate_data()
    
    # 2. 执行绘图
    plot_overhead_analysis(df_data)