import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# 设置学术期刊风格
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10

def draw_frame_comparison():
    """
    绘制物理帧结构对比图：传统时隙 ALOHA vs. LODS-MTI
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    # 定义颜色
    color_preamble = '#d9d9d9'  # 灰色
    color_guard = '#ff9999'     # 浅红色
    color_data_a = '#a6cee3'    # 浅蓝色
    color_data_b = '#b2df8a'    # 浅绿色
    color_data_c = '#fdbf6f'    # 浅橙色
    color_header = '#cab2d6'    # 浅紫色

    # --- 子图 1: Traditional Slotted ALOHA (Type I) ---
    ax1.set_title('(a) Traditional Slotted ALOHA (Type I)', loc='left', pad=15)
    ax1.set_yticks([])
    ax1.set_xlim(0, 18)
    ax1.set_ylim(0, 2)
    ax1.spines['left'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)

    # 绘制三个时隙
    slot_width = 5.5
    gap = 0.5
    start_x = 0.5

    for i, tag_color in enumerate([color_data_a, color_data_b, color_data_c]):
        x = start_x + i * (slot_width + gap)
        
        # Preamble (1 unit)
        rect_pre = patches.Rectangle((x, 0.5), 1, 1, linewidth=1, edgecolor='black', facecolor=color_preamble)
        ax1.add_patch(rect_pre)
        ax1.text(x + 0.5, 1, 'Preamble', ha='center', va='center', fontsize=9)

        # Data Payload (3 units)
        rect_data = patches.Rectangle((x + 1, 0.5), 3, 1, linewidth=1, edgecolor='black', facecolor=tag_color)
        ax1.add_patch(rect_data)
        ax1.text(x + 2.5, 1, f'Tag {chr(65+i)} Response', ha='center', va='center', fontsize=9, fontweight='bold')

        # Guard Time (1.5 units)
        rect_guard = patches.Rectangle((x + 4, 0.5), 1.5, 1, linewidth=1, edgecolor='red', facecolor=color_guard, hatch='//')
        ax1.add_patch(rect_guard)
        ax1.text(x + 4.75, 1, 'Guard', ha='center', va='center', fontsize=9, color='red')
        
        # Slot 标注
        ax1.annotate("", xy=(x, 0.2), xytext=(x + slot_width, 0.2),
                     arrowprops=dict(arrowstyle="<->", lw=1))
        ax1.text(x + slot_width/2, 0.05, f'Time Slot {i+1}', ha='center', va='top')

    # 标注 Wasted Overhead
    ax1.annotate('Significant Overhead\n(Preamble + Guard)', xy=(5, 1.8), xytext=(5, 2.5),
                 ha='center', va='bottom', fontsize=10, color='red',
                 arrowprops=dict(arrowstyle="-[, widthB=4.5, lengthB=0.5", lw=1.5, color='red'))
    ax1.annotate('', xy=(11, 1.8), xytext=(11, 2.5),
                 arrowprops=dict(arrowstyle="-[, widthB=4.5, lengthB=0.5", lw=1.5, color='red'))
    ax1.annotate('', xy=(17, 1.8), xytext=(17, 2.5),
                 arrowprops=dict(arrowstyle="-[, widthB=4.5, lengthB=0.5", lw=1.5, color='red'))


    # --- 子图 2: Proposed LODS-MTI ---
    ax2.set_title('(b) Proposed LODS-MTI (Continuous Bitstream)', loc='left', pad=15)
    ax2.set_yticks([])
    ax2.set_xlim(0, 18)
    ax2.set_ylim(0, 2)
    ax2.spines['left'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.set_xlabel('Time (normalized units)', fontsize=12)

    start_x_lods = 0.5
    
    # Header (2 units)
    rect_header = patches.Rectangle((start_x_lods, 0.5), 2, 1, linewidth=1, edgecolor='black', facecolor=color_header)
    ax2.add_patch(rect_header)
    ax2.text(start_x_lods + 1, 1, 'Frame\nHeader', ha='center', va='center', fontsize=9)

    # Continuous Bitstream (12 units - 密集的位)
    # 假设 Tag A, B, C 以及其他 Tag 的位被映射在这里
    bitstream_start = start_x_lods + 2
    
    # Tag A bits (例如 2 bits)
    rect_bits_a = patches.Rectangle((bitstream_start, 0.5), 2, 1, linewidth=1, edgecolor='black', facecolor=color_data_a)
    ax2.add_patch(rect_bits_a)
    ax2.text(bitstream_start + 1, 1, 'Tag A\nBits', ha='center', va='center', fontsize=8)
    
    # Tag C bits (例如 2 bits, 顺序不一定)
    rect_bits_c = patches.Rectangle((bitstream_start + 2, 0.5), 2, 1, linewidth=1, edgecolor='black', facecolor=color_data_c)
    ax2.add_patch(rect_bits_c)
    ax2.text(bitstream_start + 3, 1, 'Tag C\nBits', ha='center', va='center', fontsize=8)

    # Other Tag bits (4 bits)
    rect_bits_other = patches.Rectangle((bitstream_start + 4, 0.5), 4, 1, linewidth=1, edgecolor='black', facecolor='#e0e0e0')
    ax2.add_patch(rect_bits_other)
    ax2.text(bitstream_start + 6, 1, 'Other Tags Bits\n(Mapped via Perfect Hashing)', ha='center', va='center', fontsize=8, fontstyle='italic')

    # Tag B bits (2 bits)
    rect_bits_b = patches.Rectangle((bitstream_start + 8, 0.5), 2, 1, linewidth=1, edgecolor='black', facecolor=color_data_b)
    ax2.add_patch(rect_bits_b)
    ax2.text(bitstream_start + 9, 1, 'Tag B\nBits', ha='center', va='center', fontsize=8)

    # CRC (1 unit)
    rect_crc = patches.Rectangle((bitstream_start + 10, 0.5), 1, 1, linewidth=1, edgecolor='black', facecolor=color_preamble)
    ax2.add_patch(rect_crc)
    ax2.text(bitstream_start + 10.5, 1, 'CRC', ha='center', va='center', fontsize=9)

    # Frame 标注
    total_len = 2 + 10 + 1
    ax2.annotate("", xy=(start_x_lods, 0.2), xytext=(start_x_lods + total_len, 0.2),
                 arrowprops=dict(arrowstyle="<->", lw=1))
    ax2.text(start_x_lods + total_len/2, 0.05, 'Single Continuous Physical Frame', ha='center', va='top', fontweight='bold')

    # 效率提升标注
    ax2.annotate('Dense, Gapless\nBitstream', xy=(bitstream_start + 5, 1.6), xytext=(bitstream_start + 5, 2.3),
                 ha='center', va='bottom', fontsize=10, color='green', fontweight='bold',
                 arrowprops=dict(arrowstyle="-[, widthB=10, lengthB=0.3", lw=1.5, color='green'))

    plt.tight_layout()
    # plt.savefig('frame_structure_comparison.pdf', bbox_inches='tight') # 取消注释以保存为PDF
    plt.show()

if __name__ == "__main__":
    draw_frame_comparison()