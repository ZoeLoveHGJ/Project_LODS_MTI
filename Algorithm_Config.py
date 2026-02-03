# -*- coding: utf-8 -*-
"""
Algorithm_Config.py

【修改说明】
1. 重构 PLOT_STYLE_PALETTE, 定义了 6 种符合 IEEE 学术标准的区分度极高的样式。
2. LODS-MTI (Ours) 独占 Style 0 (红色实线+五角星)，视觉层级最高。
3. 其他对比算法 (CR_MTI, CTMTI等) 分配了蓝/绿/紫等冷色调及虚线样式。
"""

# import Improve_Algorithm
# from Improve_Algorithm import Improve_Algorithm
# from Improve_Two_Algo import Improve_Two_Algorithm
from ISMTI_Algo import ISMTI_Algorithm
# from Improve_One_Algo_Exp import Improve_One_Algorithm
from lods_mti_algo import LODS_MTI_Algorithm
from cpt_algo import CPT_Algorithm
from cr_mti_algo import CR_MTI_Algorithm
from ctmti_algo import CTMTI_Algorithm
from ecumi_algo import ECUMI_Algorithm

# =========================================================
# 绘图样式库 (Look-up Table)
# =========================================================
PLOT_STYLE_PALETTE = [
    # Style 0: [Hero - LODS-MTI (Ours)] 红色实心五角星 + 实线
    {
        "color": "#D62728",          # 砖红色 (IEEE标准红)
        "linestyle": "-",            # 实线 !
        "linewidth": 1,            # 加粗
        "marker": "*",
        "markersize": 15,
        "markerfacecolor": "#D62728",# 实心
        "markeredgecolor": "black",  # 黑边增加对比
        "markeredgewidth": 0.8,
        "zorder": 100,
        "label": "Proposed"
    },
    
    # Style 1: [Competitor 1] 蓝色空心圆 + 虚线
    {
        "color": "#1F77B4",          # 蓝色
        "linestyle": "--",           # 虚线 (Dashed) !
        "linewidth": 1,
        "alpha": 0.8,
        "marker": "o",
        "markersize": 10,
        "markerfacecolor": "white",  # 空心
        "markeredgecolor": "#1F77B4",
        "markeredgewidth": 1.5,
        "zorder": 90
    },
    
    # Style 2: [Competitor 2] 绿色空心方块 + 点划线
    {
        "color": "#2CA02C",          # 绿色
        "linestyle": "-.",           # 点划线 (Dash-dot) !
        "linewidth": 1,
        "alpha": 0.8,
        "marker": "s",
        "markersize": 10,
        "markerfacecolor": "white",  # 空心
        "markeredgecolor": "#2CA02C",
        "markeredgewidth": 1.5,
        "zorder": 80
    },
    
    # Style 3: [Competitor 3] 紫色空心三角 + 点线
    {
        "color": "#9467BD",          # 紫色
        "linestyle": ":",            # 点线 (Dotted) !
        "linewidth": 1,            # 点线稍粗一点才看得清
        "alpha": 0.8,
        "marker": "^",
        "markersize": 10,
        "markerfacecolor": "white",  # 空心
        "markeredgecolor": "#9467BD",
        "markeredgewidth": 1.5,
        "zorder": 70
    },
    
    # Style 4: [Competitor 4] 橙色空心菱形 + 长虚线
    {
        "color": "#FF7F0E",          # 橙色
        "linestyle": "--",           # 虚线
        "linewidth": 1,
        "alpha": 0.8,
        "marker": "D",
        "markersize": 10,
        "markerfacecolor": "white",
        "markeredgecolor": "#FF7F0E",
        "markeredgewidth": 1.5,
        "zorder": 60
    },
    
    # Style 5: [Competitor 5] 青色空心倒三角 + 点划线
    {
        "color": "#17BECF",
        "linestyle": "-.",
        "linewidth": 1,
        "alpha": 0.8,
        "marker": "v",
        "markersize": 10,
        "markerfacecolor": "white",
        "markeredgecolor": "#17BECF",
        "markeredgewidth": 1.5,
        "zorder": 50
    },

    # --- 新增 4 种 ---
    # Style 6: [Pink Hexagon] 粉色 + 实线 + 六边形
    {
        "color": "#E377C2", "linestyle": "-", "linewidth": 1.5, "alpha": 0.9,
        "marker": "h", "markersize": 9, "markerfacecolor": "white",
        "markeredgecolor": "#E377C2", "markeredgewidth": 1.5, "zorder": 45
    },
    # Style 7: [Gray Pentagon] 灰色 + 虚线 + 五边形
    {
        "color": "#7F7F7F", "linestyle": "--", "linewidth": 1.5, "alpha": 0.9,
        "marker": "p", "markersize": 9, "markerfacecolor": "white",
        "markeredgecolor": "#7F7F7F", "markeredgewidth": 1.5, "zorder": 40
    },
    # Style 8: [Olive X] 橄榄色 + 点划线 + 粗叉号
    {
        "color": "#BCBD22", "linestyle": "-.", "linewidth": 1.5, "alpha": 0.9,
        "marker": "X", "markersize": 8, "markerfacecolor": "white",
        "markeredgecolor": "#BCBD22", "markeredgewidth": 1.5, "zorder": 35
    },
    # Style 9: [Brown Thin Diamond] 棕色 + 点线 + 细菱形
    {
        "color": "#8C564B", "linestyle": ":", "linewidth": 1.8, "alpha": 0.9,
        "marker": "d", "markersize": 8, "markerfacecolor": "white",
        "markeredgecolor": "#8C564B", "markeredgewidth": 1.5, "zorder": 30
    },
    {
        "color": "#8C564B",          # 砖红色 (IEEE标准红)
        "linestyle": "-",            # 实线 !
        "linewidth": 1,            # 加粗
        "marker": "*",
        "markersize": 14,
        "markerfacecolor": "white",# 实心
        "markeredgecolor": "#8C564B",  # 黑边增加对比
        "markeredgewidth": 1.5,
        "zorder": 100,
        "label": "128b"
    },
]

# 3. 实验激活控制
ALGORITHMS_TO_TEST = [
    # 'Improve',
#    'Improve_Two',
    'CT_MTI',            # Comm Lett '24   
    'CR_MTI',           # TMC '23 cuo           
    'CPT',    # InfoCom '22                
    'ECUMI',            # ComCom '22       
    'ISMTI',            # ComNet '25,      
    'LODS_MTI', # Ours
    'LODS_MTI_128b',
]

# 4. 算法详细配置库 (Factory Pattern)
ALGORITHM_LIBRARY = {
    'LODS_MTI': { # V9 最终
        "class": LODS_MTI_Algorithm,
        "params": {
            "max_group_size": 128,  
            "target_rho": 4,
            "is_adaptive": True,
            "max_payload_bit":256,
        },
        "style_id": 0,             # 红色实线 + 五角星 (保持高亮)
        "label": "LODS-MTI (Ours)"
    },
    'LODS_MTI_128b': { # V9 最终
        "class": LODS_MTI_Algorithm,
        "params": {
            "max_group_size": 64,  
            "target_rho": 4,
            "is_adaptive": True,
            "max_payload_bit":128,
        },
        "style_id": 10,             # 红色实线 + 五角星 (保持高亮)
        "label": "LODS-MTI (128b)"
    },
    'CR_MTI': {
        "class": CR_MTI_Algorithm,
        "params": {"lambda_factor": 15, "w_len": 34}, # 按照论文 Fig.6 调优 [cite: 454]
        "style_id": 1, 
        "label": "CR-MTI"
        # "label": "CR-MTI (TMC '23)"
    },

    'CT_MTI': {
        "class": CTMTI_Algorithm,
        "params": {
            "B": 4,        # 论文常用设置，平衡冲突与空闲
            "alpha": 0.5   # 随机因子
        },
        "style_id": 2,
        "label": "CTMTI",
        # "label": "CTMTI (CL '24)"
    },

    'ECUMI': {
            "class": ECUMI_Algorithm,
            "params": {
                "rho": 1.0  # 此参数在类内部已被论文公式 0.2341*N 覆盖，但保留以兼容接口
            },
            "style_id": 3,
            "label": "ECUMI",
            # "label": "ECUMI (ComCom '22)",
    },

    'ISMTI': {
        "class": ISMTI_Algorithm,
        "params": {
            "initial_q": 0.5  # 论文默认初始值
        },
        "style_id": 4,   # 青色倒三角
        "label": "ISMTI",
        # "label": "ISMTI (ComNet '25)",
    },

    'CPT': {
            "class": CPT_Algorithm,
            "params": {
                "pseudo_id_len": 12 # 论文仿真中常用值，平衡 Payload 与冲突
            },
            "style_id": 5, 
            "label": "CPT",
            # "label": "CPT (ToN '24)"
        },
}