import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.path as mpath

def draw_professional_lods_figure():
    # 1. 全局样式设置 (Global Style)
    plt.rcParams['font.family'] = 'sans-serif'
    # 优先使用学术常用字体
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica'] 
    plt.rcParams['mathtext.fontset'] = 'cm' # 使用 Computer Modern 数学字体
    
    fig = plt.figure(figsize=(12, 5.5), dpi=300) # 宽幅设计，适合双栏论文顶栏
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # 2. 现代学术配色方案 (Academic Palette)
    colors = {
        'blue_stroke': '#1565C0', 'blue_fill': '#E3F2FD', 
        'red_stroke': '#C62828',  'red_fill': '#FFEBEE',
        'green_stroke': '#2E7D32', 'green_fill': '#E8F5E9',
        'gray_stroke': '#616161', 'gray_fill': '#F5F5F5',
        'purple_stroke': '#7B1FA2', 'purple_text': '#4A148C'
    }

    # 辅助函数：绘制带阴影的圆角矩形
    def draw_styled_box(x, y, w, h, fill_c, stroke_c, title, subtitle=None, z=1):
        # 绘制阴影 (Shadow)
        shadow = patches.FancyBboxPatch((x+0.08, y-0.08), w, h, boxstyle="round,pad=0.1", 
                                       ec="none", fc="#000000", alpha=0.15, zorder=z-1)
        ax.add_patch(shadow)
        # 绘制实体 (Body)
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", 
                                     ec=stroke_c, fc=fill_c, lw=1.5, alpha=1.0, zorder=z)
        ax.add_patch(box)
        
        # 标题
        ax.text(x + w/2, y + h*0.65, title, ha='center', va='center', 
                fontsize=11, fontweight='bold', color=stroke_c, zorder=z+1)
        # 副标题/内容
        if subtitle:
            ax.text(x + w/2, y + h*0.35, subtitle, ha='center', va='center', 
                    fontsize=9, color='#424242', zorder=z+1)
        return box

    # =========================================================================
    # Part 1: Input Sets (左侧输入分区)
    # =========================================================================
    ax.text(1.5, 5.6, "Tag Input Partitioning", ha='center', fontsize=12, fontweight='bold', color='#212121')
    
    # 使用堆叠效果绘制三个集合
    draw_styled_box(0.5, 4.2, 2.0, 1.0, colors['blue_fill'], colors['blue_stroke'], 
                    r"Set $\mathcal{T}_1$", "$N_1$ tags")
    draw_styled_box(0.5, 2.8, 2.0, 1.0, colors['red_fill'], colors['red_stroke'], 
                    r"Set $\mathcal{T}_2$", "$N_2$ tags")
    draw_styled_box(0.5, 1.4, 2.0, 1.0, colors['green_fill'], colors['green_stroke'], 
                    r"Set $\mathcal{T}_3$", "$N_3$ tags")

    # =========================================================================
    # Part 2: Deterministic Engine (中间处理引擎)
    # =========================================================================
    engine_x, engine_y = 4.0, 1.0
    engine_w, engine_h = 3.8, 4.5
    
    # 引擎外框 (Engine Frame)
    ax.add_patch(patches.FancyBboxPatch((engine_x, engine_y), engine_w, engine_h, 
                                        boxstyle="round,pad=0.2", ec=colors['gray_stroke'], 
                                        fc='#FAFAFA', lw=2, zorder=0))
    ax.text(engine_x + engine_w/2, 5.8, "LODS Deterministic Engine", 
            ha='center', fontsize=12, fontweight='bold', color='#212121')
    
    # 绘制内部逻辑通道
    # Channel 1 (Blue)
    ax.text(4.2, 4.8, r"Hash $\Phi_1(\cdot)$", fontsize=10, fontweight='bold', color=colors['blue_stroke'])
    ax.text(4.2, 4.4, r"$idx = (ID \oplus S_1) \% L_1$", fontsize=9, family='serif', color='#333')
    
    # Channel 2 (Red)
    ax.text(4.2, 3.4, r"Hash $\Phi_2(\cdot)$", fontsize=10, fontweight='bold', color=colors['red_stroke'])
    ax.text(4.2, 3.0, r"$idx = (ID \oplus S_2) \% L_2$", fontsize=9, family='serif', color='#333')
    
    # Channel 3 (Green)
    ax.text(4.2, 2.0, r"Hash $\Phi_3(\cdot)$", fontsize=10, fontweight='bold', color=colors['green_stroke'])
    ax.text(4.2, 1.6, r"$idx = (ID \oplus S_3) \% L_3$", fontsize=9, family='serif', color='#333')

    # 参数注入点 (Parameter Injection)
    for y_pos in [4.9, 3.5, 2.1]:
        # 模拟一个小圆点接口
        ax.plot([engine_x + engine_w], [y_pos], marker='<', color='#757575', markersize=6, clip_on=False)
        ax.text(engine_x + engine_w - 0.2, y_pos, "$(S_k, L_k)$", ha='right', va='center', fontsize=7, color='#757575')

    # 输入箭头 (Input Arrows)
    arrow_style = dict(arrowstyle="-|>", lw=1.5, shrinkA=0, shrinkB=0)
    ax.annotate("", xy=(4.0, 4.7), xytext=(2.6, 4.7), arrowprops=dict(edgecolor=colors['blue_stroke'], **arrow_style))
    ax.annotate("", xy=(4.0, 3.3), xytext=(2.6, 3.3), arrowprops=dict(edgecolor=colors['red_stroke'], **arrow_style))
    ax.annotate("", xy=(4.0, 1.9), xytext=(2.6, 1.9), arrowprops=dict(edgecolor=colors['green_stroke'], **arrow_style))

    # =========================================================================
    # Part 3: Output Bitstream (右侧比特流)
    # =========================================================================
    stream_x = 9.0
    stream_y = 2.8
    slot_w = 0.5
    slot_h = 1.0
    
    ax.text(stream_x + 1.5, 4.5, "Aggregated Response Frame", 
            ha='center', fontsize=12, fontweight='bold', color='#212121')

    # 绘制 Slot 辅助函数
    def draw_slot_segment(start_idx, count, color, active_pos=None):
        base_x = stream_x + start_idx * slot_w
        for i in range(count):
            rect = patches.Rectangle((base_x + i*slot_w, stream_y), slot_w, slot_h, 
                                     fc='white', ec=color, lw=1)
            ax.add_patch(rect)
            # 如果是 Active Position，填充颜色
            if active_pos is not None and i == active_pos:
                rect.set_facecolor(color)
                ax.text(base_x + i*slot_w + slot_w/2, stream_y + slot_h/2, "1", 
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)
            else:
                ax.text(base_x + i*slot_w + slot_w/2, stream_y + slot_h/2, "0", 
                        ha='center', va='center', color='#EEEEEE', fontweight='bold', fontsize=9)

    # Slice 1 (Blue)
    draw_slot_segment(0, 2, colors['blue_stroke'], active_pos=1)
    ax.text(stream_x + 1.0*slot_w, stream_y + 1.2, "Slice 1", ha='center', color=colors['blue_stroke'], fontsize=8, fontweight='bold')
    
    # Slice 2 (Red)
    draw_slot_segment(2, 2, colors['red_stroke'], active_pos=0)
    ax.text(stream_x + 3.0*slot_w, stream_y + 1.2, "Slice 2", ha='center', color=colors['red_stroke'], fontsize=8, fontweight='bold')
    
    # Slice 3 (Green)
    draw_slot_segment(4, 2, colors['green_stroke'], active_pos=None)
    ax.text(stream_x + 5.0*slot_w, stream_y + 1.2, "Slice 3", ha='center', color=colors['green_stroke'], fontsize=8, fontweight='bold')

    # 分隔线 (Separators)
    ax.plot([stream_x + 2*slot_w, stream_x + 2*slot_w], [stream_y-0.2, stream_y+1.5], ls='--', color='#BDBDBD', lw=1)
    ax.plot([stream_x + 4*slot_w, stream_x + 4*slot_w], [stream_y-0.2, stream_y+1.5], ls='--', color='#BDBDBD', lw=1)

    # 输出箭头 (Engine -> Stream) - 使用贝塞尔曲线
    conn_props = dict(arrowstyle="->", lw=1.5, shrinkA=5, shrinkB=5)
    ax.annotate("", xy=(stream_x + 0.5*slot_w, stream_y + slot_h), xytext=(7.8, 4.8), 
                arrowprops=dict(connectionstyle="arc3,rad=-0.1", color=colors['blue_stroke'], **conn_props))
    ax.annotate("", xy=(stream_x + 2.5*slot_w, stream_y + slot_h), xytext=(7.8, 3.4), 
                arrowprops=dict(connectionstyle="arc3,rad=0", color=colors['red_stroke'], **conn_props))
    ax.annotate("", xy=(stream_x + 4.5*slot_w, stream_y + slot_h), xytext=(7.8, 2.0), 
                arrowprops=dict(connectionstyle="arc3,rad=0.1", color=colors['green_stroke'], **conn_props))

    # =========================================================================
    # Part 4: Feedback Loop (底部反馈回路)
    # =========================================================================
    fb_y = 0.5
    fb_text = "Adaptive Error Tolerance Control"
    
    # 反馈标签框
    ax.text(6.0, fb_y, fb_text, ha='center', va='center', fontsize=10, fontweight='bold', 
            color=colors['purple_text'], 
            bbox=dict(facecolor='white', edgecolor=colors['purple_stroke'], boxstyle='round,pad=0.4', alpha=1.0))

    # 绘制虚线路径 (Stream -> Engine)
    # 右半段箭头
    ax.annotate("", xy=(7.4, fb_y), xytext=(stream_x + 3*slot_w, stream_y - 0.2),
                arrowprops=dict(arrowstyle="-", connectionstyle="angle,angleA=0,angleB=-90,rad=5", 
                                color=colors['purple_stroke'], lw=1.5, ls='--'))
    # 左半段箭头
    ax.annotate("", xy=(5.5, 1.0), xytext=(4.6, fb_y),
                arrowprops=dict(arrowstyle="->", connectionstyle="angle,angleA=90,angleB=180,rad=5", 
                                color=colors['purple_stroke'], lw=1.5, ls='--'))

    plt.tight_layout()
    plt.savefig('LODS_Professional_Architecture.png', bbox_inches='tight', dpi=300)
    plt.show()
    print("已生成高质量科研绘图: LODS_Professional_Architecture.png")

draw_professional_lods_figure()