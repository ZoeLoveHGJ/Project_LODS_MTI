import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_optimized_architecture():
    # ==========================================
    # 1. 全局配置 (字体加大，画布变紧凑)
    # ==========================================
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman']
    
    # 配色方案 (保持高雅的学术风)
    C_ALGO = "#F0F0F0"       # 浅灰
    C_PHY_CALC = "#DAE8FC"   # 浅蓝
    C_ENGINE = "#FFF2CC"     # 浅黄
    C_IMPAIR = "#F8CECC"     # 浅红 (核心)
    C_BORDER = "#000000"     # 纯黑边框，增强对比度
    
    # 【优化点1】画布尺寸缩小，内容会自动显得更紧凑
    fig, ax = plt.subplots(figsize=(6, 7.5)) 
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # ==========================================
    # 2. 增强版绘图函数
    # ==========================================
    def draw_process_box(x, y, w, h, title, subtitle=None, color="white", 
                         title_size=12, sub_size=10):
        # 【优化点2】pad减小，减少内部留白
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", 
                                     linewidth=1.5, edgecolor=C_BORDER, facecolor=color, zorder=10)
        ax.add_patch(box)
        
        # 标题 (加粗，字号加大)
        cy = y + h/2 + (1.2 if subtitle else 0)
        ax.text(x + w/2, cy, title, ha='center', va='center', 
                fontsize=title_size, fontweight='bold', color='black', zorder=11)
        
        # 副标题
        if subtitle:
            ax.text(x + w/2, cy - 2.8, subtitle, ha='center', va='center', 
                    fontsize=sub_size, style='italic', color='#333333', zorder=11)
        
        return (x + w/2, y) # 返回底部中心点

    def draw_thick_arrow(x, y_start, y_end, label=None):
        # 【优化点3】线条加粗 (lw=2.0), 箭头变大
        ax.annotate("", xy=(x, y_end), xytext=(x, y_start),
                    arrowprops=dict(arrowstyle="-|>", lw=2.0, color="black", 
                                    mutation_scale=15), zorder=5)
        if label:
            # 标签加背景遮挡线条
            t = ax.text(x + 2, (y_start + y_end)/2, label, fontsize=10, va='center', 
                        fontweight='bold', color='#444444', zorder=12)
            t.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='none', pad=0))

    # ==========================================
    # 3. 绘制流程 (坐标重算，更加紧凑)
    # ==========================================
    
    # 中心轴 X
    CX = 50
    # 统一框宽 (稍微变窄，让文字撑满)
    W_BOX = 54 

    # --- A. MAC Layer ---
    ax.text(12, 96, "Layer 1: MAC Logic", fontsize=11, fontweight='bold', color="#0066CC")
    
    # Box 1
    y1, h1 = 87, 8
    draw_process_box(CX - W_BOX/2, y1, W_BOX, h1, 
                     "1. Reader Command Gen.", "(Payload & Protocol Logic)", color=C_ALGO)

    # --- B. PHY Layer ---
    # 间距缩短
    draw_thick_arrow(CX, y1, 78)
    
    # Box 2
    y2, h2 = 70, 8
    draw_process_box(CX - W_BOX/2, y2, W_BOX, h2, 
                     "2. Downlink Overhead", "(T_pre + Payload Duration)", color=C_PHY_CALC)

    # --- C. Physics Engine (Container) ---
    draw_thick_arrow(CX, y2, 63)
    
    # 容器框 (更贴合内部元素)
    cont_y, cont_h = 18, 45
    container = patches.FancyBboxPatch((8, cont_y), 84, cont_h, boxstyle="round,pad=0.2", 
                                       linewidth=1.5, edgecolor="#B85450", facecolor="none", 
                                       linestyle='--', zorder=1)
    ax.add_patch(container)
    ax.text(12, cont_y + cont_h + 1, "Layer 2: High-Fidelity Physics Engine", 
            fontsize=11, fontweight='bold', color="#B85450")

    # Box 3 (Arbitration)
    y3, h3 = 54, 8
    draw_process_box(CX - W_BOX/2, y3, W_BOX, h3, 
                     "3. Response Arbitration", "(RSSI Check & Capture Effect)", color=C_ENGINE)
    
    draw_thick_arrow(CX, y3, 46, "Raw Signal")

    # Box 4 (Impairment - The Core)
    y4, h4 = 25, 21 # 高度增加以容纳大字
    # 稍微宽一点以突出
    W_IMPAIR = 64
    box_impair = patches.FancyBboxPatch((CX - W_IMPAIR/2, y4), W_IMPAIR, h4, boxstyle="round,pad=0.1", 
                                        linewidth=2, edgecolor="#B85450", facecolor=C_IMPAIR, zorder=10)
    ax.add_patch(box_impair)
    
    # Impairment Title
    ax.text(CX, y4 + 17, "4. Bit-Level Impairment Injection", ha='center', 
            fontsize=12, fontweight='bold', zorder=11)
    
    # Sub-modules (左右布局，字体加大)
    ax.text(CX - 15, y4 + 11, "Clock Drift", ha='center', fontsize=11, fontweight='bold', zorder=11)
    ax.text(CX - 15, y4 + 7, "(Coherence Limit)", ha='center', fontsize=10, style='italic', zorder=11)
    
    # 分隔线
    ax.plot([CX, CX], [y4 + 4, y4 + 14], color="#B85450", linestyle=":", lw=1.5, zorder=11)
    
    ax.text(CX + 15, y4 + 11, "Channel Noise", ha='center', fontsize=11, fontweight='bold', zorder=11)
    ax.text(CX + 15, y4 + 7, "(Random Bit Flips)", ha='center', fontsize=10, style='italic', zorder=11)

    # Output text
    ax.text(CX, y4 + 2.5, "Output: Channel Noise Mask", ha='center', 
            fontsize=10, fontweight='bold', color="#993333", zorder=11)

    # --- D. Feedback ---
    draw_thick_arrow(CX, y4, 15)
    
    # Box 5
    y5, h5 = 7, 8
    draw_process_box(CX - W_BOX/2, y5, W_BOX, h5, 
                     "5. Result Feedback Loop", "(Return Status + Bit Mask)", color=C_PHY_CALC)

    # --- E. Feedback Arrow (Left Side) ---
    # 线条加粗，贴得更近
    ax.plot([15, 15], [y5 + h5/2, 91], color="black", lw=2.0, zorder=0) # Vertical Up
    ax.plot([15, CX - W_BOX/2], [y5 + h5/2, y5 + h5/2], color="black", lw=2.0, zorder=0) # Horizontal Bottom
    
    # Top Arrow
    ax.annotate("", xy=(CX - W_BOX/2, 91), xytext=(15, 91),
                arrowprops=dict(arrowstyle="-|>", lw=2.0, color="black", mutation_scale=15), zorder=5)
    
    ax.text(13, 50, "Next Time Slot", rotation=90, va='center', fontsize=11, 
            fontweight='bold', backgroundcolor='white', zorder=20)

    # Title
    # ax.text(CX, 102, "Fig. A1: Architecture of the High-Fidelity Simulation Framework", 
    #         ha='center', fontsize=13, fontweight='bold')

    plt.tight_layout()
    # 保存时裁剪掉多余白边
    plt.savefig("framework_architecture.pdf", bbox_inches='tight', dpi=300)
    plt.savefig("framework_architecture.png", bbox_inches='tight', dpi=300)
    print("Optimized Architecture Chart Generated.")

if __name__ == "__main__":
    draw_optimized_architecture()