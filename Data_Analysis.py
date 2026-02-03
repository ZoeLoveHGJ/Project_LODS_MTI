import pandas as pd
import matplotlib.pyplot as plt
import os

# Exp2
# folder_path = r'Results_Exp2_MissingRate/'

# Exp1
# folder_path = r'Results_Exp1_Parallel/'

# Exp3
# folder_path = r'Results_Exp3_BER/'

# 设置文件夹路径 (确保路径前加 r)
folder_path = r'Results_Exp2_MissingRate/'

# 设置指定的 CSV 文件名列表
# 格式: 'CSV文件名': '表格中显示的列名(指标名)'
file_metric_map = {
    'raw_verification_concurrency.csv': 'Concurrency',
    'raw_throughput.csv': 'Throughput',
    'raw_time_efficiency_index.csv': 'Normalized Time Efficiency'
}

# Exp3
# file_metric_map = {
#     'raw_Reliability': 'Reliability.csv',
#     'raw_Goodput.csv': 'Good Throught',
#     'raw_edp.csv': 'EDP',
# }

# Exp2
# file_metric_map = {
#     'raw_verification_concurrency.csv': 'Concurrency',
#     'raw_throughput.csv': 'Throughput',
#     'raw_time_efficiency_index.csv': 'Normalized Time Efficiency'
# }

# Exp1
# file_metric_map = {
#     'raw_total_time_ms.csv': 'Time',
#     'raw_verification_concurrency.csv': 'Concurrency',
#     'raw_total_tag_energy_j.csv': 'Tag_Energy',
#     'raw_edp.csv': 'EDP'
# }

# ==========================================
# 2. 数据处理核心逻辑
# ==========================================

summary_data = []
metric_labels = [] # 这里存储的是指标名，稍后作为列名

print(f"📂 正在分析文件夹: {folder_path} ...")
print("-" * 30)

# 检查变量是否定义
if 'file_metric_map' not in locals():
    print("❌ 错误: file_metric_map 未定义，请检查代码第一部分。")
else:
    for file_name, metric_name in file_metric_map.items():
        full_path = os.path.join(folder_path, file_name)
        
        if os.path.exists(full_path):
            try:
                # 读取 CSV
                df = pd.read_csv(full_path)
                
                # iloc[:, 1:] 剔除第一列(X轴)，只取算法数据列
                algo_data = df.iloc[:, 1:]
                
                # 计算平均值
                means = algo_data.mean(numeric_only=True)
                
                # 加入列表
                summary_data.append(means)
                metric_labels.append(metric_name) 
                
                print(f"✅ [读取成功] {metric_name} <- {file_name}")
                
            except Exception as e:
                print(f"❌ [读取错误] 文件 {file_name} 出错: {e}")
        else:
            print(f"⚠️ [文件缺失] 找不到: {file_name}")

    # ==========================================
    # 3. 生成表格与保存
    # ==========================================

    if summary_data:
        # --- 核心修改点 ---
        # 1. 先构建基础 DF (此时：行是指标，列是算法)
        temp_df = pd.DataFrame(summary_data, index=metric_labels)
        
        # 2. 进行转置操作 (.T)，交换行列
        # 现在：行是算法，列是指标
        result_df = temp_df.T
        
        # 保留4位小数
        result_df = result_df.round(4)
        
        print("\n📊 汇总表格预览 (算法在行，指标在列):")
        print(result_df)

        # 获取文件夹名
        folder_name = os.path.basename(os.path.normpath(folder_path))
        base_output_name = f"{folder_name}_Data_Analysis"
        
        # 3.1 保存 CSV
        csv_path = os.path.join(folder_path, base_output_name + ".csv")
        result_df.to_csv(csv_path, encoding='utf-8-sig')
        
        # 3.2 绘制图片
        # 动态计算图表尺寸 (根据转置后的行列数调整)
        rows, cols = result_df.shape
        # 宽度：基础宽 + 每列(指标)稍微宽一点，因为指标名可能较长
        w = max(8, cols * 2.0) 
        # 高度：基础高 + 每行(算法)的高度
        h = max(3, rows * 0.6 + 1.5) 
        
        fig, ax = plt.subplots(figsize=(w, h))
        ax.axis('off')
        
        # 绘制表格
        table = ax.table(cellText=result_df.values,
                         colLabels=result_df.columns,  # 这里是指标名
                         rowLabels=result_df.index,    # 这里是算法名
                         cellLoc='center',
                         loc='center')
        
        # 美化样式
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 1.8)
        
        # 设置表头颜色
        for (row, col), cell in table.get_celld().items():
            cell.set_edgecolor('black')
            # row=0 是列头(指标名)，col=-1 是行头(算法名)
            if row == 0 or col == -1: 
                cell.set_text_props(weight='bold')
                cell.set_facecolor('#e6e6e6') 
        
        plt.title(f"Algorithm Performance Summary\n({folder_name})", 
                  pad=20, fontsize=14, weight='bold')
        
        # 保存图片和PDF
        img_path = os.path.join(folder_path, base_output_name + ".png")
        pdf_path = os.path.join(folder_path, base_output_name + ".pdf")
        
        plt.savefig(img_path, bbox_inches='tight', dpi=300)
        plt.savefig(pdf_path, bbox_inches='tight')
        
        print("-" * 30)
        print("🎉 完成！文件已保存：")
        print(f"CSV: {csv_path}")
        print(f"PNG: {img_path}")
        print(f"PDF: {pdf_path}")
        plt.show()

    else:
        print("\n⚠️ 未生成数据，请检查 'file_metric_map' 中的文件名是否真实存在于文件夹中。")