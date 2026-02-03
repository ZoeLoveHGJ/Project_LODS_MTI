import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def draw_optimized_drift_visualization():
    # ==========================================
    # 1. IEEE 风格配置 (响应: 增大字体)
    # ==========================================
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman']
    plt.rcParams['font.size'] = 12  # 全局字号提升
    
    # 配色方案 (响应: 避免浅色字体，增强对比度)
    C_SAFE = "#E2F0D9"       # 浅绿 (背景)
    C_UNSAFE = "#FCE4D6"     # 浅红 (背景)
    C_BORDER = "#000000"     # 纯黑边框
    C_TEXT = "#000000"       # 纯黑文字
    C_DRIFT_LINE = "#C00000" # 深红 (漂移线)
    C_THRESHOLD = "#2F5597"  # 深蓝 (阈值线)
    
    # 仿真参数模拟
    TOTAL_BITS = 16
    MAX_SAFE_BITS = 9
    
    # 稍微加大画布以容纳大字体
    fig, ax = plt.subplots(figsize=(10, 6)) 
    ax.set_xlim(-1.5, TOTAL_BITS + 1.5)
    ax.set_ylim(0, 11)
    ax.axis('off')

    # ==========================================
    # 2. 区域绘制 (背景色块)
    # ==========================================
    # Safe Zone
    rect_safe = patches.Rectangle((-0.5, 0), MAX_SAFE_BITS + 0.5, 10, 
                                  facecolor=C_SAFE, alpha=0.5, edgecolor='none')
    ax.add_patch(rect_safe)
    # 顶部状态描述
    ax.text(MAX_SAFE_BITS/2, 10.2, "Safe Operating Area (Coherent)\nData Integrity: Guaranteed", 
            ha='center', va='bottom', fontsize=12, fontweight='bold', color="#385723")

    # Unsafe Zone
    rect_unsafe = patches.Rectangle((MAX_SAFE_BITS, 0), TOTAL_BITS - MAX_SAFE_BITS + 0.5, 10, 
                                    facecolor=C_UNSAFE, alpha=0.5, edgecolor='none')
    ax.add_patch(rect_unsafe)
    # 顶部状态描述
    ax.text(MAX_SAFE_BITS + (TOTAL_BITS - MAX_SAFE_BITS)/2, 10.2, "Sync Loss Region\nData Integrity: Corrupted", 
            ha='center', va='bottom', fontsize=12, fontweight='bold', color="#833C0C")

    # 分隔线
    ax.plot([MAX_SAFE_BITS, MAX_SAFE_BITS], [0, 10], color=C_DRIFT_LINE, linestyle="--", lw=1.5)
    ax.text(MAX_SAFE_BITS, -0.8, "Coherence Limit\n(Max Safe Bits)", 
            ha='center', fontsize=11, fontweight='bold', color="#000000")

    # ==========================================
    # 3. 层级 1: 累积相位误差 (物理层)
    # ==========================================
    # 左侧层级标签
    ax.text(-1.0, 8.0, "Physical Layer:\nCumulative\nPhase Error (Δt)", 
            ha='right', va='center', fontsize=12, fontweight='bold', color=C_TEXT)
    
    x = np.linspace(0, TOTAL_BITS, 100)
    base_y = 6.5
    # 响应: 调整斜率，使其更平缓自然，避免突兀
    y_drift = base_y + (x / MAX_SAFE_BITS) * 0.8
    
    ax.plot(x, y_drift, color=C_DRIFT_LINE, lw=2.5) # 加粗线条
    
    # 阈值线
    threshold_y = base_y + 0.8
    ax.plot([0, TOTAL_BITS], [threshold_y, threshold_y], color=C_THRESHOLD, linestyle="-.", lw=1.5)
    ax.text(TOTAL_BITS + 0.5, threshold_y, "Decoding Threshold\n(0.5 * T_bit)", 
            va='center', fontsize=10, color=C_THRESHOLD, fontweight='bold')

    # 关键点标注 (Threshold Breach)
    ax.plot([MAX_SAFE_BITS], [threshold_y], marker='o', color='red', markersize=8, zorder=10)
    ax.annotate("Sync Loss Point\n(Error > Threshold)", 
                xy=(MAX_SAFE_BITS, threshold_y), 
                xytext=(MAX_SAFE_BITS + 3, threshold_y + 1.5),
                arrowprops=dict(arrowstyle="->", color='black', lw=1.5), 
                fontsize=11, fontweight='bold', 
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.8))

    # ==========================================
    # 4. 层级 2: 比特流状态 (数据层)
    # ==========================================
    ax.text(-1.0, 4.5, "Data Layer:\nReceived\nBit Stream", 
            ha='right', va='center', fontsize=12, fontweight='bold', color=C_TEXT)
    
    for i in range(TOTAL_BITS):
        is_safe = i < MAX_SAFE_BITS
        color = "white" if is_safe else "#D9D9D9" # 错误区背景加深
        edge = C_BORDER
        text_col = "black" 
        hatch = ""
        
        if not is_safe:
            hatch = "///" 
            text_col = "#C00000" # 错误数据用深红

        rect = patches.Rectangle((i, 4), 0.8, 1, facecolor=color, edgecolor=edge, hatch=hatch, lw=1.2)
        ax.add_patch(rect)
        
        # 下标
        ax.text(i + 0.4, 3.5, f"b{i}", ha='center', fontsize=10, color="black", fontweight='bold')
        
        # 比特值
        bit_val = "1" if i % 3 == 0 else "0"
        if not is_safe: bit_val = "?"
        ax.text(i + 0.4, 4.5, bit_val, ha='center', va='center', fontsize=14, fontweight='bold', color=text_col)

    # ==========================================
    # 5. 层级 3: 掩码逻辑 (代码逻辑层)
    # ==========================================
    ax.text(-1.0, 1.5, "Logic Layer:\nGenerated\nNoise Mask", 
            ha='right', va='center', fontsize=12, fontweight='bold', color=C_TEXT)
    
    # 逻辑流向箭头
    ax.annotate("", xy=(MAX_SAFE_BITS, 2.8), xytext=(MAX_SAFE_BITS, 3.8), 
                arrowprops=dict(arrowstyle="->", color="black", lw=2))

    for i in range(TOTAL_BITS):
        is_safe = i < MAX_SAFE_BITS
        
        mask_val = "0" if is_safe else "1"
        bg_color = "white" if is_safe else "#F4CCCC" # 掩码激活背景
        edge_color = "black"
        
        # 错误区的框加粗
        lw = 1.2 if is_safe else 2.0
        
        rect = patches.Rectangle((i, 1), 0.8, 1, facecolor=bg_color, edgecolor=edge_color, lw=lw)
        ax.add_patch(rect)
        
        ax.text(i + 0.4, 1.5, mask_val, ha='center', va='center', fontsize=14, fontweight='bold', color="black")

    # 底部逻辑说明
    ax.text(MAX_SAFE_BITS / 2, 0.2, "Mask = 0\n(Keep Original Data)", 
            ha='center', va='bottom', fontsize=11, fontweight='bold', color="#385723")
    ax.text(MAX_SAFE_BITS + (TOTAL_BITS - MAX_SAFE_BITS)/2, 0.2, "Mask = 1\n(Force Bit Error)", 
            ha='center', va='bottom', fontsize=11, fontweight='bold', color="#C00000")

    plt.tight_layout()
    plt.savefig("framework_check_data.pdf", bbox_inches='tight', dpi=300)
    plt.savefig("framework_check_data.png", bbox_inches='tight', dpi=300)
    print("Optimization Complete. Image saved as framework_check_data_optimized.png")

if __name__ == "__main__":
    draw_optimized_drift_visualization()