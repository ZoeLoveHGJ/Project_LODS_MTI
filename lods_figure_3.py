import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ==========================================
# V3.2 配置：出版级高清优化 (High Visibility)
# ==========================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['mathtext.fontset'] = 'cm' 

# --- 配色方案 (去灰色，高对比) ---
C_SIG     = "#0072BD"    # 信号蓝
C_SILENCE = "#FFFFFF"    # 静默白
C_NOISE   = "#D95319"    # 错误红
C_FALSE   = "#EDB120"    # 虚警金
C_VALID   = "#77AC30"    # 成功绿
C_MISSING = "#7E2F8E"    # 缺失紫
C_TEXT    = "#000000"    # 纯黑文本 (替代灰色)
C_LABEL   = "#000000"    # 纯黑标签 (替代灰色)
C_ARROW   = "#000000"    # 纯黑箭头
C_CHANNEL_BG = "#F8F9FA" # 信道背景保持淡灰，以示区分
C_CHANNEL_EC = "#000000" # 信道边框改为纯黑，增强对比

def draw_lods_mechanism_final():
    # 调整画布比例
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 7))
    plt.subplots_adjust(wspace=0.15, left=0.02, right=0.98, top=0.92, bottom=0.05)

    # ------------------------------------------------------------------
    # 绘图辅助
    # ------------------------------------------------------------------
    def draw_bit_sequence(ax, x_start, y, bits, colors, labels=None, is_dashed=False):
        w, h = 1.0, 1.4  
        gap = 0.15
        
        for i, val in enumerate(bits):
            bx = x_start + i * (w + gap)
            
            # 阴影
            shadow = patches.FancyBboxPatch((bx + 0.05, y - 0.05), w, h, 
                                            boxstyle="round,pad=0.0",
                                            fc='#AAAAAA', alpha=0.3, zorder=1)
            ax.add_patch(shadow)
            
            # 主方块
            ls = '--' if is_dashed else '-'
            # [修改4] 增强虚线边框可视度
            lw = 2.5 if is_dashed else 2.0 
            ec = 'black' # 统一用黑色边框，不再用灰色
            
            rect = patches.Rectangle((bx, y), w, h, fc=colors[i], ec=ec, lw=lw, linestyle=ls, zorder=2)
            ax.add_patch(rect)
            
            # 填充文字 (加大字号)
            txt_color = 'white' if colors[i] not in [C_SILENCE] else 'black' # Silence文字改黑
            ax.text(bx + w/2, y + h/2, r"$\mathbf{"+str(val)+"}$", ha='center', va='center', 
                    fontsize=18, color=txt_color, zorder=3, fontweight='bold')
            
            # 底部标签
            if labels and i < len(labels) and labels[i]:
                 ax.text(bx + w/2, y - 0.35, labels[i], ha='center', va='top', 
                         fontsize=13, color=C_TEXT, fontweight='bold', zorder=4)

    # ------------------------------------------------------------------
    # 核心绘图逻辑
    # ------------------------------------------------------------------
    def draw_scenario(ax, title, is_present_case):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 13) 
        ax.axis('off')
        
        # 标题 (加大)
        ax.text(5, 12.6, title, ha='center', va='center', fontsize=16, fontweight='bold', color='black')

        # === Layer 1: Transmitter ===
        tx_y = 10.5
        ax.text(0.2, tx_y + 0.9, "Transmitter", fontsize=15, fontweight='bold', color=C_TEXT, ha='left')
        # [修改3] 去灰：字体改黑，去掉 italic
        ax.text(0.2, tx_y + 0.4, "(Tag Sent)", fontsize=13, color=C_TEXT, ha='left')
        
        if is_present_case:
            draw_bit_sequence(ax, 3.0, tx_y, [1,1,1,1], [C_SIG]*4)
            ax.text(8.0, tx_y + 0.7, r"Tag Sends $\rho=4$", fontsize=14, color=C_TEXT, fontweight='bold')
        else:
            draw_bit_sequence(ax, 3.0, tx_y, [0,0,0,0], [C_SILENCE]*4, is_dashed=True)
            ax.text(8.0, tx_y + 0.7, r"Silence (Ideal)", fontsize=14, color=C_TEXT, fontweight='bold')

        # === Layer 2: Noisy Channel (高可视度版) ===
        chan_y = 8.2
        # [修改4] 边框加粗，改纯黑
        chan_box = FancyBboxPatch((0.5, chan_y), 9.0, 1.4,
                                   boxstyle="round,pad=0.1,rounding_size=0.2",
                                   fc=C_CHANNEL_BG, ec='black', 
                                   lw=2.5, linestyle='--', zorder=0)
        ax.add_patch(chan_box)
        
        # [修改3] 文字改黑
        ax.text(9.3, chan_y + 0.7, "Noisy Channel", va='center', ha='right',
                fontsize=13, fontweight='bold', color='black')

        # 穿透箭头
        for i in range(4):
            x_center = 3.0 + i*1.15 + 0.5
            ax.add_patch(FancyArrowPatch((x_center, tx_y), (x_center, chan_y + 1.4), 
                                         arrowstyle='-', color=C_ARROW, lw=2.0))
            ax.plot([x_center, x_center], [chan_y + 1.4, chan_y], color=C_ARROW, lw=1.5, ls=':')
            ax.add_patch(FancyArrowPatch((x_center, chan_y), (x_center, chan_y - 0.8), 
                                         arrowstyle='-|>', mutation_scale=20, color=C_ARROW, lw=2.0))
        
        # 干扰事件标记
        if is_present_case:
            err_x = 3.0 + 1*1.15 + 0.5
            ax.text(err_x + 0.3, chan_y + 0.7, "Fade/Loss", color=C_NOISE, fontsize=14, fontweight='bold', ha='left', va='center')
            ax.text(err_x, chan_y + 0.7, "X", color=C_NOISE, fontsize=24, ha='center', va='center', fontweight='bold', zorder=5)
        else:
            err_x = 3.0 + 3*1.15 + 0.5
            ax.text(err_x - 0.3, chan_y + 0.7, "Noise Spike", color=C_FALSE, fontsize=14, fontweight='bold', ha='right', va='center')
            ax.text(err_x, chan_y + 0.7, "!", color=C_FALSE, fontsize=26, ha='center', va='center', fontweight='bold', zorder=5)

        # === Layer 3: Receiver ===
        rx_y = 5.5
        ax.text(0.2, rx_y + 0.9, "Receiver", fontsize=15, fontweight='bold', color=C_TEXT, ha='left')
        ax.text(0.2, rx_y + 0.4, "(Reader)", fontsize=13, color=C_TEXT, ha='left')
        
        if is_present_case:
            draw_bit_sequence(ax, 3.0, rx_y, [1,0,1,1], [C_SIG, C_NOISE, C_SIG, C_SIG], ["", "Bit Error", "", ""])
            sum_val = 3
            res_color = C_VALID
            res_title = "PRESENT"
            res_desc = "Robust to 1 Error"
            check_math = r"$\mathbf{3} \geq \mathbf{3}$"
            check_res = "(Pass)"
            check_color = C_VALID
        else:
            draw_bit_sequence(ax, 3.0, rx_y, [0,0,0,1], [C_SILENCE, C_SILENCE, C_SILENCE, C_FALSE], ["", "", "", "False Alarm"])
            sum_val = 1
            res_color = "#444444" 
            res_title = "MISSING"
            res_desc = "Noise Filtered"
            check_math = r"$\mathbf{1} < \mathbf{3}$"
            check_res = "(Reject)"
            check_color = C_NOISE

        # === Layer 4: Voting Engine (压缩版) ===
        center_x = 5.3
        # 连接线
        ax.plot([center_x, center_x], [rx_y - 0.5, 4], color=C_ARROW, lw=2.0, ls='-')
        ax.add_patch(FancyArrowPatch((center_x, 4), (center_x, 3.7), arrowstyle='-|>', mutation_scale=20, color=C_ARROW, lw=2.0))
        
        # [修改5] 压缩高度: 从 3.3 -> 2.5
        box_y = 0.7
        box_h = 2.5
        
        rect_logic = FancyBboxPatch((2.0, box_y), 6.5, box_h, boxstyle="round,pad=0.2,rounding_size=0.3", 
                                    fc='white', ec='black', lw=2.0, zorder=1)
        ax.add_patch(rect_logic)
        
        # 紧凑化内部文字布局
        # 标题栏
        ax.text(center_x, box_y + 2.1, "Majority Voting Logic", ha='center', fontsize=14, fontweight='bold')
        ax.plot([2.2, 8.3], [box_y + 1.9, box_y + 1.9], color='black', lw=1.5) 
        
        # 算式 (行间距压缩)
        ax.text(2.4, box_y + 1.4, r"Threshold: $\theta = \lfloor 4/2 \rfloor + 1 = \mathbf{3}$", fontsize=14, color='black')
        ax.text(2.4, box_y + 0.9, r"Vote Sum: $\Sigma = \mathbf{" + str(sum_val) + r"}$", fontsize=14, color='black')
        ax.text(2.4, box_y + 0.4, r"Check: " + check_math + r" $\rightarrow$ " + check_res, fontsize=14, fontweight='bold', color=check_color)

        # === Final Decision Stamp ===
        # 印章位置调整适应新高度
        stamp_rect = FancyBboxPatch((6.14, box_y + 0.2), 2.2, 1.0, 
                                    boxstyle="round,pad=0.1,rounding_size=0.2",
                                    fc=res_color, ec=res_color, alpha=1.0, zorder=10)
        ax.add_patch(stamp_rect)
        
        ax.text(7.1, box_y + 1.0, res_title, color='white', 
                ha='center', va='center', fontweight='bold', fontsize=15, zorder=15)
        ax.text(7.1, box_y + 0.6, f"({res_desc})", color='white', 
                ha='center', va='center', fontsize=11, fontstyle='italic', zorder=15)

    # 执行绘制
    draw_scenario(ax1, "(a) Scenario A: Tag Present", True)
    draw_scenario(ax2, "(b) Scenario B: Tag Missing", False)

    plt.tight_layout()
    
    # [修改1] 保存为 PDF
    filename_base = 'Paper_Figures/LODS_MTI_Vote'
    plt.savefig(f'{filename_base}.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(f'{filename_base}.png', bbox_inches='tight', dpi=300) # 同时生成预览
    print(f"File saved as {filename_base}.pdf and {filename_base}.png")
    # plt.show() 

if __name__ == "__main__":
    draw_lods_mechanism_final()