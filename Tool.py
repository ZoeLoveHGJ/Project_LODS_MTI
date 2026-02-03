# -*- coding: utf-8 -*-
"""
Tool.py - RFID Simulation Analytics & Visualization Toolkit
版本: V7.0 (Auto Data Splitter Integrated)

【更新说明】
1. [Storage] 集成自动拆分工具。save_to_csv 现在会自动将所有计算出的指标
   分别存储为 raw_{metric_name}.csv，无需手动维护列表。
2. [Format] 拆分后的 CSV 采用 Wide Format (X轴为索引, 算法名为列)，直接对接 Science_Figure.py。
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import math
from typing import Dict, List

# 尝试设置中文字体
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'DejaVu Sans'] 
    plt.rcParams['axes.unicode_minus'] = False
except: 
    pass

class SimulationAnalytics:
    def __init__(self):
        self.raw_data = []

    def add_run_result(self, result_stats: Dict, sim_config: Dict, algo_name: str, run_id: int):
        """收集单次运行结果"""
        record = {
            'algorithm_name': algo_name,
            'run_id': run_id,
            **sim_config,
            **result_stats
        }
        self.raw_data.append(record)

    def get_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.raw_data) if self.raw_data else pd.DataFrame()

    def _calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """[计算层] 计算所有深度指标"""
        if df.empty: return df

        # --- 1. 基础物理量 ---
        if 'total_time_us' in df.columns: 
            df['total_time_ms'] = df['total_time_us'] / 1000.0
            df['total_time_s'] = df['total_time_us'] / 1e6

        tag_e_j = df['total_tag_energy_j'] if 'total_tag_energy_j' in df.columns else 0.0
        reader_e_j = df.get('total_reader_energy_j', 0.0)
        df['total_energy_j'] = reader_e_j + tag_e_j
        
        # --- 2. 深度指标 ---
        # Verification Concurrency
        if 'TOTAL_TAGS' in df.columns and 'total_slots' in df.columns:
            df['verification_concurrency'] = df.apply(
                lambda r: r['TOTAL_TAGS'] / r['total_slots'] if r['total_slots'] > 0 else 0, 
                axis=1
            )

        # Energy Cost Per Tag
        if 'TOTAL_TAGS' in df.columns:
            df['energy_per_tag_uj'] = df.apply(
                lambda r: (r['total_energy_j'] * 1e6) / r['TOTAL_TAGS'] if r['TOTAL_TAGS'] > 0 else 0,
                axis=1
            )

        # Time Efficiency Index
        t_min_ms = 0.4 
        if 'TOTAL_TAGS' in df.columns and 'total_time_ms' in df.columns:
            df['time_efficiency_index'] = df.apply(
                lambda r: (r['TOTAL_TAGS'] * t_min_ms) / r['total_time_ms'] if r['total_time_ms'] > 0 else 0,
                axis=1
            )

        # Throughput
        if 'TOTAL_TAGS' in df.columns and 'total_time_s' in df.columns:
            df['throughput'] = df.apply(
                lambda r: r['TOTAL_TAGS'] / r['total_time_s'] if r['total_time_s'] > 0 else 0, 
                axis=1
            )
            
        # EDP
        if 'total_energy_j' in df.columns and 'total_time_s' in df.columns:
            df['edp'] = df['total_energy_j'] * df['total_time_s']

        # Collision Rate
        if 'collision_slots' in df.columns and 'total_slots' in df.columns:
            df['collision_rate'] = df.apply(
                lambda r: r['collision_slots'] / r['total_slots'] if r['total_slots'] > 0 else 0,
                axis=1
            )

        return df

    def save_to_csv(self, x_axis_key: str, output_dir: str = "simulation_results"):
        """
        [存储层] 自动拆分所有指标为单独 CSV
        """
        if not self.raw_data: return
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 计算全量数据
        df = self._calculate_derived_metrics(self.get_dataframe())

        # 2. 保存总表 (备份用)
        full_path = os.path.join(output_dir, "00_Raw_Full_Data.csv")
        df.to_csv(full_path, index=False)
        print(f"✅ 全量数据备份: {full_path}")
        
        # 3. 自动识别并拆分所有指标
        # 定义不需要拆分的元数据列
        exclude_cols = [
            'algorithm_name', 
            'run_id', 
            x_axis_key, 
            'MISSING_RATE', 
            'ENABLE_NOISE', 
            'packet_error_rate',
            'ENABLE_CAPTURE_EFFECT', 
            'CAPTURE_RATIO_DB', 
            'ENABLE_ENERGY_TRACKING'
        ]
        
        # 筛选出所有数值类型的列作为待拆分指标
        numeric_cols = df.select_dtypes(include=['number']).columns
        metric_cols = [c for c in numeric_cols if c not in exclude_cols]
        
        print(f"🔄 正在自动拆分 {len(metric_cols)} 个性能指标...")

        count = 0
        for col in metric_cols:
            try:
                # 核心逻辑: 透视表 (Pivot)
                # 将多轮实验(run_id)的数据取平均值，转置为 [X轴, 算法A, 算法B...] 的宽表格式
                pivot = df.pivot_table(
                    index=x_axis_key, 
                    columns='algorithm_name', 
                    values=col, 
                    aggfunc='mean'
                )
                
                # 重置索引，让 x_axis_key 变回普通列，这对绘图脚本至关重要
                pivot.reset_index(inplace=True)
                
                # 生成规范文件名: raw_{指标名}.csv
                # 替换非法字符
                safe_name = col.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "")
                fname = f"raw_{safe_name}.csv"
                
                pivot.to_csv(os.path.join(output_dir, fname), index=False)
                count += 1
            except Exception as e:
                pass # 忽略无法聚合的列

        print(f"✅ 拆分完成，已生成 {count} 个独立指标文件 (raw_*.csv)。")

    def plot_results(self, x_axis_key: str, algorithm_library: Dict, save_path: str = None): 
        """
        [展示层] 仅绘制精选的深度指标
        """
        df = self.get_dataframe()
        if df.empty: return
        
        # 必须先计算指标
        df = self._calculate_derived_metrics(df)
        
        # --- 核心配置：展示哪些指标 (KPI Map) ---
        # Key: 图表标题
        # Value: DataFrame 中的列名
        

        kpi_map = {
            # 1. 性能绝对值 (必选)
            'Total Execution Time (ms)': 'total_time_ms',
            
            # 2. MTI 核心效率 (替代 ID Efficiency)
            # 展示算法利用冲突的能力，值越大越好 (通常 > 1.0)
            'Verification Concurrency (tags/slot)': 'verification_concurrency', 
            
            # 3. 归一化能耗 (替代 Total Energy)
            # 展示单标签开销，值越低越好
            'Energy Cost per Tag (uJ)': 'energy_per_tag_uj',
            
            # 4. 理论逼近度 (可选，展示算法水平)
            'Normalized Time Efficiency (η)': 'time_efficiency_index',
            
            # 5. 系统吞吐量 (保留作为工程参考)
            'System Throughput (tags/s)': 'throughput',
            
            # 6. 综合权衡
            'Energy-Delay Product (J·s)': 'edp'
        }

        # 过滤掉数据中不存在的列
        valid_kpis = {k: v for k, v in kpi_map.items() if v in df.columns}
        if not valid_kpis: return

        # 自动布局
        n = len(valid_kpis)
        cols = 2  # 改为双列布局，更适合论文排版
        rows = math.ceil(n / cols)
        
        fig, axes = plt.subplots(rows, cols, figsize=(6*cols, 4*rows))
        if n == 1: axes = [axes]
        else: axes = axes.flatten()
        
        algos = sorted(df['algorithm_name'].unique())

        for idx, (title, col) in enumerate(valid_kpis.items()):
            ax = axes[idx]
            for algo in algos:
                # 获取样式配置 (如果存在)
                style_kwargs = {'marker': 'o', 'linestyle': '-', 'linewidth': 1.5, 'markersize': 6}
                if algo in algorithm_library:
                    conf = algorithm_library[algo]
                    # 尝试读取 Algorithm_Config 中的样式 ID
                    # 这里做简单映射，保持代码独立性
                    style_id = conf.get('style_id', 0)
                    # 简易颜色轮
                    colors = ['#D62728', 'black', '#1F77B4', '#2CA02C', '#9467BD', '#FF7F0E', '#17BECF', '#8C564B']
                    markers = ['*', 'o', 's', '^', 'd', 'P', 'X', 'p']
                    
                    style_kwargs['color'] = colors[style_id % len(colors)]
                    style_kwargs['marker'] = markers[style_id % len(markers)]
                    if style_id == 0: # 突出显示 Ours
                        style_kwargs['linewidth'] = 2.5
                        style_kwargs['markersize'] = 9
                        style_kwargs['zorder'] = 10
                    
                subset = df[df['algorithm_name'] == algo]
                # 按 X 轴分组求均值
                grouped = subset.groupby(x_axis_key)[col].mean().sort_index()
                
                # 绘图
                ax.plot(grouped.index, grouped.values, label=algo, **style_kwargs)
            
            ax.set_title(title, fontsize=11, fontweight='bold')
            ax.set_xlabel(x_axis_key)
            ax.set_ylabel(title.split('(')[-1].strip(')')) # 简单提取单位作为 Y 轴
            ax.grid(True, linestyle='--', alpha=0.5)
            
            # 图例仅在第一个图显示
            if idx == 0: 
                ax.legend(loc='best', fontsize='small', framealpha=0.8)

        # 移除多余子图
        for i in range(n, len(axes)):
            fig.delaxes(axes[i])

        plt.tight_layout()
        if save_path: 
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 图表已保存至: {save_path}")
        
        # 注意：在某些服务器环境可能需要注释掉 show
        plt.show()