# -*- coding: utf-8 -*-
"""
Science_Figure_Template.py
科研绘图调用模板 (Template & Examples)
适配引擎版本: V9.0
功能：
1. 生成包含 6 种算法的复杂测试数据。
2. 穷举演示所有支持的子图排布 (Single, Double, Triple, Quad, Quad-Row)。
"""

import os
import pandas as pd
import numpy as np
import shutil

# 导入绘图引擎
from Science_Figure import SciencePlotter, ALGORITHM_LIBRARY, PLOT_STYLE_PALETTE

# ==============================================================================
# 1. 模拟环境准备 (生成 6 条曲线数据)
# ==============================================================================
def create_dummy_data():
    """生成模拟 CSV，包含 1 个高亮算法 + 5 个对比算法"""
    if os.path.exists("data_mock"):
        shutil.rmtree("data_mock")
    os.makedirs("data_mock")

    print(">>> 正在生成模拟数据 (6条曲线)...")
    
    # 生成 50 个数据点 (展示稀疏采样效果)
    x = np.linspace(100, 1000, 50)
    
    # 模拟数据
    # BGCT 是 Proposed Method (高亮)
    data_common = {
        'TOTAL_TAGS': x,
        'BGCT':           x * 2.5 + np.random.rand(50)*30, 
        'Standard_Aloha': x * 0.5 + np.random.rand(50)*20,
        'Tree_Split':     x * 1.2 + np.random.rand(50)*30,
        'Binary_Tree':    x * 1.0 + np.random.rand(50)*25,
        'Query_Tree':     x * 1.8 + np.random.rand(50)*40,
        'Hybrid_Scheme':  x * 2.1 + np.random.rand(50)*35,
        'Ohter_SoTA':  x * 2.3 + np.random.rand(50)*25,
        'Debug_Info':     np.zeros(50) # 干扰列
    }
    
    # 1. 吞吐量 (Throughput)
    df_th = pd.DataFrame(data_common)
    df_th.to_csv("data_mock/throughput.csv", index=False)
    
    # 2. 碰撞率 (Collision Rate)
    # 稍微改一下数据让两张图看起来不一样
    df_col = df_th.copy()
    for col in df_col.columns:
        if col != 'TOTAL_TAGS':
            df_col[col] = df_col[col] / (x * 3) + np.random.rand(50)*0.1
    df_col.to_csv("data_mock/collision.csv", index=False)

    # --- 配置样式库 (Label & Style ID) ---
    if not ALGORITHM_LIBRARY:
        ALGORITHM_LIBRARY.update({
            'BGCT':           {'style_id': 0, 'label': 'BGCT (Proposed)'}, 
            'Standard_Aloha': {'style_id': 1, 'label': 'FSA-Standard'},
            'Tree_Split':     {'style_id': 2, 'label': 'Tree-Splitting'},
            'Binary_Tree':    {'style_id': 3, 'label': 'Binary-Tree'},
            'Query_Tree':     {'style_id': 4, 'label': 'Query-Tree'},
            'Hybrid_Scheme':  {'style_id': 5, 'label': 'Hybrid-Scheme'}
        })
    
    # --- 扩充颜色池 (确保 6 种颜色不重复) ---
    if not PLOT_STYLE_PALETTE:
        PLOT_STYLE_PALETTE.extend([
            {"color": "#D62728", "linestyle": "-",  "marker": "o", "lw": 2}, # 0: 红/实线 (Highlight)
            {"color": "#1F77B4", "linestyle": "--", "marker": "s"},          # 1: 蓝/虚线
            {"color": "#2CA02C", "linestyle": "-.", "marker": "^"},          # 2: 绿/点划线
            {"color": "#FF7F0E", "linestyle": ":",  "marker": "v"},          # 3: 橙/点线
            {"color": "#9467BD", "linestyle": "--", "marker": "D"},          # 4: 紫/长虚线
            {"color": "#8C564B", "linestyle": "-",  "marker": "x"}           # 5: 棕/实线
        ])

# ==============================================================================
# 2. 穷举所有布局 (All Layouts)
# ==============================================================================
def run_all_layouts():
    plotter = SciencePlotter(output_dir="figures_all_layouts")
    
    # 通用配置 (高亮 BGCT，每5个点采一个样，排除 Debug 列)
    base_cfg = {
        'highlight': 'BGCT', 
        'mark_step': 5, 
        'exclude': ['Debug_Info']
    }
    
    print(">>> 开始绘制所有布局...")

    # -----------------------------------------------------------
    # 1. Single (1x1)
    # -----------------------------------------------------------
    print("   [1/5] Generating Single Layout (1x1)...")
    tasks_1 = [
        {'file': 'data_mock/throughput.csv', 'y_col': 'throughput', 'xlabel': 'Tags', **base_cfg}
    ]
    plotter.draw_scientific_figure(tasks_1, layout_type='single', filename='Layout_01_Single')

    # -----------------------------------------------------------
    # 2. Double (1x2)
    # -----------------------------------------------------------
    print("   [2/5] Generating Double Layout (1x2)...")
    tasks_2 = [
        {'file': 'data_mock/throughput.csv', 'y_col': 'throughput',     'xlabel': 'Tags', **base_cfg},
        {'file': 'data_mock/collision.csv',  'y_col': 'collision_rate', 'xlabel': 'Tags', **base_cfg}
    ]
    plotter.draw_scientific_figure(tasks_2, layout_type='double', filename='Layout_02_Double')

    # -----------------------------------------------------------
    # 3. Triple (1x3)
    # -----------------------------------------------------------
    print("   [3/5] Generating Triple Layout (1x3)...")
    tasks_3 = [
        {'file': 'data_mock/throughput.csv', 'y_col': 'throughput',     'xlabel': 'Tags', **base_cfg},
        {'file': 'data_mock/collision.csv',  'y_col': 'collision_rate', 'xlabel': 'Tags', **base_cfg},
        {'file': 'data_mock/throughput.csv', 'y_col': 'total_time_ms',  'xlabel': 'Tags', **base_cfg}
    ]
    plotter.draw_scientific_figure(tasks_3, layout_type='triple', filename='Layout_03_Triple')

    plotter.draw_scientific_figure(tasks_3, layout_type='triple_row', filename='Layout_03_Triple_Row')

    # -----------------------------------------------------------
    # 4. Quad (2x2 Grid)
    # -----------------------------------------------------------
    print("   [4/5] Generating Quad Layout (2x2 Grid)...")
    # 凑够 4 个任务
    tasks_4 = [
        {'file': 'data_mock/throughput.csv', 'y_col': 'throughput',       'xlabel': 'Tags', **base_cfg},
        {'file': 'data_mock/collision.csv',  'y_col': 'collision_rate',   'xlabel': 'Tags', **base_cfg},
        {'file': 'data_mock/throughput.csv', 'y_col': 'total_time_ms',    'xlabel': 'Tags', **base_cfg},
        {'file': 'data_mock/throughput.csv', 'y_col': 'reader_energy_mj', 'xlabel': 'Tags', **base_cfg}
    ]
    plotter.draw_scientific_figure(tasks_4, layout_type='quad', filename='Layout_04_Quad_Grid')

    # -----------------------------------------------------------
    # 5. Quad Row (1x4 Row)
    # -----------------------------------------------------------
    print("   [5/5] Generating Quad Row Layout (1x4 Flat)...")
    # 复用 tasks_4 即可，只是排布方式变了
    plotter.draw_scientific_figure(tasks_4, layout_type='quad_row', filename='Layout_05_Quad_Row')

if __name__ == "__main__":
    create_dummy_data()
    run_all_layouts()
    print("\n✅ 所有类型的图表绘制完成！请查看 figures_all_layouts/ 文件夹。")