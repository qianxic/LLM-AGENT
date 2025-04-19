import pandas as pd
import os

# --- 配置 --- #
# 输入的Excel文件路径
INPUT_EXCEL_FILE = r"D:\代码\ESRI\ture_small\dataes\yaopin\待谈判.xlsx"
# 输出的Excel文件路径
OUTPUT_EXCEL_FILE =r"D:\代码\ESRI\ture_small\dataes\yaopin\待谈判_merge.xlsx"
# 输出文件中合并后工作表的名称
OUTPUT_SHEET_NAME = "Merged_Data"
# --- 配置结束 --- #

def merge_excel_sheets(input_path, output_path, output_sheet):
    """读取Excel文件，按顺序合并所有工作表到一个新文件"""
    print(f"开始处理文件: {input_path}")

    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        return

    try:
        # 使用 pd.ExcelFile 获取所有工作表名称（保持顺序）
        xls = pd.ExcelFile(input_path)
        sheet_names = xls.sheet_names
        print(f"找到工作表 ({len(sheet_names)}): {', '.join(sheet_names)}")

        if not sheet_names:
            print("错误: 文件中没有找到任何工作表")
            return

        # 用于存储所有工作表数据的列表
        all_dfs = []

        # 按顺序读取每个工作表
        for sheet_name in sheet_names:
            print(f"读取工作表: {sheet_name}")
            try:
                # header=0 表示第一行为表头
                df = pd.read_excel(input_path, sheet_name=sheet_name, header=0)
                if not df.empty:
                    all_dfs.append(df)
                else:
                    print(f"  工作表 '{sheet_name}' 为空，跳过")
            except Exception as e:
                print(f"读取工作表 '{sheet_name}' 时出错: {e}")

        # 检查是否有数据可合并
        if not all_dfs:
            print("没有可合并的数据")
            return

        # 合并所有数据帧
        print("\n正在合并数据...")
        # ignore_index=True 会重新生成索引，避免重复
        merged_df = pd.concat(all_dfs, ignore_index=True)
        print(f"合并完成，共 {len(merged_df)} 行数据")

        # 保存合并后的数据到新Excel文件
        print(f"正在保存到: {output_path}")
        try:
            # index=False 防止将pandas的索引写入Excel文件
            merged_df.to_excel(output_path, sheet_name=output_sheet, index=False, engine='openpyxl')
            print("文件保存成功!")
        except Exception as e:
            print(f"保存文件时出错: {e}")

    except Exception as e:
        print(f"处理Excel文件时发生错误: {e}")

# --- 主程序入口 --- #
if __name__ == "__main__":
    # 确保安装了必要的库
    try:
        import openpyxl
    except ImportError:
        print("请先安装 openpyxl 库: pip install openpyxl")
    else:
        merge_excel_sheets(INPUT_EXCEL_FILE, OUTPUT_EXCEL_FILE, OUTPUT_SHEET_NAME) 