# -*- coding: utf-8 -*-
"""
Science_Figure.py
科研绘图专用引擎 (Publication-Ready Plotting Engine)
版本: V10.0 (Absolute Geometry Layout)

【核心特性 V10.0】
1. 绝对几何布局: 彻底摒弃 tight_layout，确保所有子图物理尺寸严格一致 (默认 3.5 x 2.8 inch)。
2. 刚性间距控制: 无论标签长短，子图间距、图例间距固定不变。
3. 统一图例系统: 图例置于顶部固定区域，不再挤压图形空间。
4. 完美品字形: 'triple_row' 布局下，第三张图自动居中且尺寸无畸变。
"""

import os
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from typing import List, Dict, Tuple, Any

# --- 导入配置中心 ---
try:
    from Algorithm_Config import ALGORITHM_LIBRARY, PLOT_STYLE_PALETTE
except ImportError:
    print("⚠️ 警告: 未找到 Algorithm_Config.py，将使用默认空配置。")
    ALGORITHM_LIBRARY = {}
    PLOT_STYLE_PALETTE = []

# ==============================================================================
# 0. 绝对几何参数配置 (单位: 英寸 Inch)
# ==============================================================================
GEOMETRY_CONFIG = {
    # --- 子图本身的大小 ---
    'SUBPLOT_W': 3.5,       # 子图宽度 (不含轴标签)
    'SUBPLOT_H': 3.0,       # 子图高度 (不含轴标签) -> 建议比宽小一点，长方形更美观
    
    # --- 刚性边距 (给轴标签、刻度预留的空间) ---
    'MARGIN_LEFT': 0.9,     # 左边距 (预留给 Y 轴标题)
    'MARGIN_RIGHT': 0.2,    # 右边距
    'MARGIN_BOTTOM': 0.7,   # 下边距 (预留给 X 轴标题)
    'MARGIN_TOP': 0.6,      # 上边距 (含图例区域)
    
    # --- 子图之间的间距 ---
    'SPACE_W': 0.9,         # 列间距 (防止 (b) 的 Y轴标签 撞到 (a))
    'SPACE_H': 0.9,         # 行间距 (防止 (c) 的 标题 撞到 (a) 的 X轴标签)
    
    # --- 图例微调 ---
    'LEGEND_Y_OFFSET': 0.05, # 图例中心相对于 MARGIN_TOP 的垂直偏移

    # --- 新增：子图标题控制 ---
    'CAPTION_GAP': 0.65,     # 子图编号 (a) 距离子图底边的绝对距离 (英寸)
                        # 注意：这个距离包含 X轴 Label 的空间，需大于 XLabel 的占用
}

LAYOUT_CONFIG = {
    'LABEL_POS': (-0.22, 1.05), # 子图编号 (a) 的位置 (相对于子图 Axes 坐标)
}

# ==============================================================================
# 1. 全局样式配置
# ==============================================================================
def apply_science_style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Liberation Serif'],
        'mathtext.fontset': 'stix',
        'font.size': 16,
        'axes.labelsize': 16,
        'xtick.labelsize': 14,
        'ytick.labelsize': 14,
        'legend.fontsize': 14,
        'lines.linewidth': 2,
        'lines.markersize': 6,
        'axes.linewidth': 1.5,
        'grid.linestyle': '--',
        'grid.alpha': 0.5,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight', # 仅用于最后裁剪多余白边，不影响内部布局
        'savefig.pad_inches': 0.05
    })

# ==============================================================================
# 2. 核心绘图类
# ==============================================================================
class SciencePlotter:
    def __init__(self, output_dir="figures_pub"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        apply_science_style()
        
        self.metric_label_map = {
            'throughput': 'System Throughput (tags/s)',
            'identification_efficiency': r'Identification Efficiency ($\eta$)',
            'collision_rate': 'Collision Rate',
            'total_time_ms': 'Identification Time (ms)',
            'total_time_s': 'Identification Time (s)',
            'edp': r'Energy-Delay Product ($J \cdot s$)',
            'reader_energy_mj': 'Reader Energy Consumption (mJ)',
            'total_tag_energy_uj': 'Tag Energy Consumption ($\mu$J)',
            'verification_concurrency': 'Verification Concurrency (tags/query)',
            'energy_per_tag_uj': r'Energy Cost Per Tag ($\mu$J)',
            'time_efficiency_index': 'Normalized Time Efficiency'
        }

    def _get_style_by_id(self, style_id: int, label_txt: str) -> Dict:
        if not PLOT_STYLE_PALETTE:
             return {"color": "black", "linestyle": "-", "marker": "o", "label": label_txt}
        safe_id = style_id % len(PLOT_STYLE_PALETTE)
        style = PLOT_STYLE_PALETTE[safe_id].copy()
        style['label'] = label_txt
        return style

    def _resolve_algo_styles(self, algo_list: List[str], highlight_target: str = None) -> Dict[str, int]:
        style_map = {}
        used_ids = set()
        unknown_algos = []
        if highlight_target and highlight_target in algo_list:
            style_map[highlight_target] = 0
            used_ids.add(0)
        for algo in algo_list:
            if algo == highlight_target: continue 
            if algo in ALGORITHM_LIBRARY:
                conf_id = ALGORITHM_LIBRARY[algo].get('style_id', 0)
                style_map[algo] = conf_id
                used_ids.add(conf_id)
            else:
                unknown_algos.append(algo)
        current_id = 1 
        for algo in unknown_algos:
            while current_id in used_ids: current_id += 1
            style_map[algo] = current_id
            used_ids.add(current_id)
            current_id += 1
        return style_map

    def _load_data(self, csv_path: str) -> pd.DataFrame:
        if not os.path.exists(csv_path):
            print(f"⚠️ 警告: 文件未找到 -> {csv_path}")
            return pd.DataFrame()
        return pd.read_csv(csv_path)

    # --------------------------------------------------------------------------
    # [核心] 绝对几何计算引擎
    # --------------------------------------------------------------------------
    def _calc_absolute_geometry(self, layout_type: str) -> Tuple[Tuple[float, float], List[Tuple[float, float, float, float]], float]:
        """
        计算画布尺寸和每个子图的精确位置。
        返回: (fig_size_inch, list_of_axes_rects, legend_center_y_ratio)
        """
        cfg = GEOMETRY_CONFIG
        
        # 1. 确定行列结构
        layout_map = {
            'single': (1, 1), 'double': (1, 2), 'triple': (1, 3),
            'quad': (2, 2), 'quad_row': (1, 4), 'triple_row': (2, 2) # triple_row 特殊处理
        }
        rows, cols = layout_map.get(layout_type, (1, 1))
        
        # 2. 计算画布物理总尺寸 (Inches)
        # 宽度 = 左边距 + N个子图 + (N-1)个间距 + 右边距
        total_w = cfg['MARGIN_LEFT'] + cols * cfg['SUBPLOT_W'] + (cols - 1) * cfg['SPACE_W'] + cfg['MARGIN_RIGHT']
        # 高度 = 下边距 + M个子图 + (M-1)个间距 + 上边距
        total_h = cfg['MARGIN_BOTTOM'] + rows * cfg['SUBPLOT_H'] + (rows - 1) * cfg['SPACE_H'] + cfg['MARGIN_TOP']
        
        # 3. 生成每个子图的 Rect [left, bottom, width, height] (归一化 0~1)
        axes_rects = []
        
        # 辅助函数：将物理尺寸转换为归一化坐标
        def get_rect(row_idx, col_idx, col_offset_inch=0):
            # X轴方向: 左边距 + 前面的列 * (宽+间距) + 额外偏移
            x_inch = cfg['MARGIN_LEFT'] + col_idx * (cfg['SUBPLOT_W'] + cfg['SPACE_W']) + col_offset_inch
            # Y轴方向: 顶部总高 - 上边距 - (当前行+1)*(高+间距) + 间距 (因为是从下往上算，所以比较绕，直接用Bottom基准更稳)
            # 更好的算法：从下往上数
            # 倒数第 row_idx 行 (row_idx=0 是最上面) -> 实际是第 (rows - 1 - row_idx) 行
            inv_row = rows - 1 - row_idx
            y_inch = cfg['MARGIN_BOTTOM'] + inv_row * (cfg['SUBPLOT_H'] + cfg['SPACE_H'])
            
            return [x_inch / total_w, y_inch / total_h, cfg['SUBPLOT_W'] / total_w, cfg['SUBPLOT_H'] / total_h]

        if layout_type == 'triple_row':
            # 特殊布局：品字形
            # 第一行：正常 2 个
            axes_rects.append(get_rect(0, 0)) # (a)
            axes_rects.append(get_rect(0, 1)) # (b)
            
            # 第二行：居中 1 个
            # 计算第一行的中心点宽度
            row1_content_w = 2 * cfg['SUBPLOT_W'] + cfg['SPACE_W']
            # 计算偏移量：让第二行的第1个图居中于第一行
            # 偏移 = (第一行总宽 - 单图宽) / 2
            center_offset = (row1_content_w - cfg['SUBPLOT_W']) / 2
            axes_rects.append(get_rect(1, 0, col_offset_inch=center_offset)) # (c)
            
        else:
            # 标准网格布局
            for r in range(rows):
                for c in range(cols):
                    axes_rects.append(get_rect(r, c))

        # 4. 计算图例的 Y 轴中心位置
        # 图例位于 MARGIN_TOP 的中间区域
        legend_y_inch = total_h - (cfg['MARGIN_TOP'] / 2) + cfg['LEGEND_Y_OFFSET']
        legend_y_ratio = legend_y_inch / total_h
        
        return (total_w, total_h), axes_rects, legend_y_ratio

    # --------------------------------------------------------------------------
    # 主绘图函数
    # --------------------------------------------------------------------------
    def draw_scientific_figure(self, 
                               tasks: List[Dict], 
                               layout_type: str = "single", 
                               filename: str = "fig_output"):
        
        # 1. 获取绝对几何参数
        # fig_size 是 (宽inch, 高inch)
        fig_size, axes_rects, legend_y = self._calc_absolute_geometry(layout_type)
        total_h_inch = fig_size[1] # 获取画布总高度，用于计算比例
        
        fig = plt.figure(figsize=fig_size)
        
        axes_list = []
        legend_handles = {}

        # 2. 按几何位置创建 Axes 并绘图
        # 注意：tasks 数量可能少于或多于布局位置，需截断或跳过
        for idx, rect in enumerate(axes_rects):
            if idx >= len(tasks): break
            
            # 使用 add_axes 精确放置
            ax = fig.add_axes(rect)
            axes_list.append(ax)
            
            task = tasks[idx]
            df = self._load_data(task.get('file'))
            if df.empty: continue
            
            x_col = task.get('x_col', 'TOTAL_TAGS')
            
            # 样式与绘图
            mark_step = task.get('mark_step', 1) 
            exclude_cols = task.get('exclude', [])
            algo_cols = [c for c in df.columns if c != x_col and c not in exclude_cols]
            
            highlight_target = task.get('highlight', None)
            style_map = self._resolve_algo_styles(algo_cols, highlight_target)
            algo_cols.sort(key=lambda x: style_map.get(x, 99))

            for algo_name in algo_cols:
                sid = style_map.get(algo_name)
                conf = ALGORITHM_LIBRARY.get(algo_name, {})
                label_txt = conf.get('label', algo_name)
                style = self._get_style_by_id(sid, label_txt)
                
                line, = ax.plot(df[x_col], df[algo_name], markevery=mark_step, **style)
                
                if style['label'] not in legend_handles:
                    legend_handles[style['label']] = line

            # 坐标轴与标签设置
            ax.set_xlabel(task.get('xlabel', r'Number of Tags ($N$)'))
            ax.set_ylabel(self.metric_label_map.get(task.get('y_col'), task.get('y_col')))
            ax.grid(True, linestyle='--', alpha=0.5)
            
            # 刻度设置
            custom_xticks = task.get('xticks', None)
            if custom_xticks: ax.set_xticks(sorted(custom_xticks))
            ax.ticklabel_format(style='sci', axis='y', scilimits=(-2, 3), useMathText=True)
            
            # ==================================================================
            # === [核心修改点] 绝对坐标放置子图标题 ===
            # ==================================================================
            # 1. 计算文本中心的 X 坐标 (子图的水平中心)
            #    rect[0] 是 left, rect[2] 是 width
            center_x = rect[0] + rect[2] / 2
            
            # 2. 计算文本基线的 Y 坐标 (子图底边 - 物理距离)
            #    rect[1] 是 bottom (0-1), GEOMETRY_CONFIG['CAPTION_GAP'] 是英寸
            #    需要将英寸转换为 0-1 比例： Inches / Total_Height_Inches
            gap_ratio = GEOMETRY_CONFIG['CAPTION_GAP'] / total_h_inch
            caption_y = rect[1] - gap_ratio
            
            # 3. 使用 fig.text 而不是 ax.text
            #    这样可以完全脱离 axes 内部坐标系，实现绝对对齐
            fig.text(center_x, caption_y, f"({chr(97 + idx)})", 
                     fontsize=16, fontweight='bold', 
                     ha='center', va='top') # ha='center' 保证水平居中
            # ==================================================================

        # ==================================================================
        # 3. 统一图例绘制 (Absolute Geometry 修正版)
        # ==================================================================
        unique_labels = list(legend_handles.keys())
        final_handles = list(legend_handles.values())
        num_items = len(unique_labels)
        
        if num_items > 0:
            # --- [核心修改] 绝对物理尺寸配置 ---
            MAX_COLS = 4                # 每行最多显示几个图例
            LEGEND_ROW_GAP_INCH = 0.25  # 行与行之间的【固定物理间距】(英寸)
                                        # 0.25 inch 约等于一行文字的高度加上舒适的留白
            
            # 实时计算归一化间距 (Normalized Spacing) = 物理间距 / 画布总高
            # 这样无论画布多高多矮，肉眼看到的行间距都是固定的
            row_spacing_norm = LEGEND_ROW_GAP_INCH / fig_size[1]
            
            # --- 1. 将图例切分为多行 (Chunking) ---
            legend_chunks = []
            for i in range(0, num_items, MAX_COLS):
                chunk_labels = unique_labels[i : i + MAX_COLS]
                chunk_handles = final_handles[i : i + MAX_COLS]
                legend_chunks.append((chunk_labels, chunk_handles))
            
            num_rows = len(legend_chunks)
            
            # --- 2. 计算起始 Y 坐标 ---
            # 算法: 让多行整体的中心点依然对齐 legend_y
            # Start_Y = Center_Y + (Total_Height / 2)
            # 这里简化为：最上面一行的 Y = 中心 + (行数 - 1) * 半个间距
            start_y = legend_y + (num_rows - 1) * row_spacing_norm / 2
            
            # --- 3. 循环绘制每一行 ---
            for i, (labels_group, handles_group) in enumerate(legend_chunks):
                # 当前行的 Y 坐标
                current_y = start_y - (i * row_spacing_norm)
                
                # 关键技巧：ncol=len(labels_group)
                # 比如最后一行只有3个，就设ncol=3，配合 loc='center'，
                # Matplotlib 会把这3个的矩形框整体居中，从而实现"倒金字塔"或"居中对齐"效果
                leg = fig.legend(handles=handles_group, labels=labels_group,
                                 loc='center',             
                                 bbox_to_anchor=(0.5, current_y), 
                                 ncol=len(labels_group), 
                                 frameon=False, 
                                 columnspacing=1.5,
                                 handletextpad=0.5)
                
                # 样式修正 (颜色跟随线条 + 粗体)
                for text, handle in zip(leg.get_texts(), handles_group):
                    text.set_color(handle.get_color()) 
                    text.set_fontweight('bold')

        # 4. 保存 (不使用 tight_layout)
        pdf_path = os.path.join(self.output_dir, f"{filename}.pdf")
        png_path = os.path.join(self.output_dir, f"{filename}.png")
        
        # ⚠️ 关键：不使用 bbox_inches='tight' 来保存 PDF，以保留我们精心计算的留白
        # 但 PNG 为了展示方便可以使用，或者保持一致。
        # 为了“绝对一致性”，建议 PDF 不使用 tight，PNG 使用。
        plt.savefig(pdf_path, format='pdf') 
        plt.savefig(png_path, format='png', dpi=300)
        
        print(f"✅ 图表已生成 (Layout: {layout_type}, Size: {fig_size[0]:.1f}x{fig_size[1]:.1f}\"): {pdf_path}")
        plt.close()

if __name__ == "__main__":
    print("Science_Figure V10.0: Absolute Geometry Engine Ready.")
    # 示例调用
    # plotter = SciencePlotter()
    # tasks = [...]
    # plotter.draw_scientific_figure(tasks, layout_type='triple_row', filename='test_fix')