import pandas as pd
import sqlite3
import os

# --- 配置 --- #
# 数据库文件路径
DB_FILE = r"D:\代码\ESRI\ture_small\dataes\table_total.db"
# 固定的数据来源信息
DATA_SOURCE_INFO = "https://www.gov.cn/zhengce/zhengceku/2023-01/18/content_5737840.htm《国家基本医疗保险、工伤保险和生育保险药品目录（2022年）》的通知医保发〔2023〕5号"

# 要处理的文件和对应的表名
FILES_TO_PROCESS = [
    {
        "input_excel": r"D:\代码\ESRI\ture_small\dataes\yaopin\中成药.xlsx",
        "table_name": "Chinese_medicine"
    },
    {
        "input_excel": r"D:\代码\ESRI\ture_small\dataes\yaopin\西药.xlsx",
        "table_name": "Western_medicine"
    }
]

# Excel列名到数据库字段的映射 (假设两个Excel文件表头结构类似)
COLUMN_MAPPING = {
    '药品分类代码': 'drug_classification_code',
    '药品分类': 'drug_classification',
    '编号': 'serial_number',
    '药品名称': 'drug_name',
    '剂型': 'dosage_form',
    '备注': 'remarks'
}
# --- 配置结束 --- #

def create_db_table(conn, table_name):
    """在数据库中为指定的表名创建表（如果不存在）"""
    cursor = conn.cursor()
    try:
        # 注意：移除了 source_sheet 列
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 自增主键
            drug_classification_code TEXT,                  -- 药品分类代码
            drug_classification TEXT,                       -- 药品分类
            serial_number TEXT,                             -- 编号
            drug_name TEXT NOT NULL,                        -- 药品名称
            dosage_form TEXT,                               -- 剂型
            remarks TEXT,                                   -- 备注
            source TEXT,                                    -- 数据来源 (固定值)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 记录创建时间
        );
        ''')
        # 检查 source 列是否存在，如果不存在则添加
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        if 'source' not in columns:
            print(f"向表 '{table_name}' 添加 'source' 列...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN source TEXT")
        
        conn.commit()
        print(f"数据库表 '{table_name}' 已准备就绪。")
    except Exception as e:
        print(f"创建/更新数据库表 '{table_name}' 时出错: {e}")
        raise

def import_excel_to_db(excel_path, db_path, table_name, data_source, column_mapping):
    """读取指定Excel所有工作表数据并插入指定的SQLite数据库表"""
    print(f"\n{'='*20} 开始处理 {'='*20}")
    print(f"Excel文件: {excel_path}")
    print(f"数据库表: {table_name}")
    print(f"数据来源: {data_source}")

    if not os.path.exists(excel_path):
        print(f"错误: Excel文件不存在: {excel_path}")
        return 0 # 返回插入的行数

    conn = None
    total_inserted_for_file = 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        create_db_table(conn, table_name) # 确保表存在

        xls = pd.ExcelFile(excel_path)
        sheet_names = xls.sheet_names
        print(f"找到工作表 ({len(sheet_names)}): {', '.join(sheet_names)}")

        for sheet_name in sheet_names:
            print(f"\n  处理工作表: {sheet_name}")
            try:
                # 假设表头在第一行 (header=0)
                df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)

                # 检查实际列名并重命名
                rename_dict = {}
                missing_cols = []
                current_excel_columns = df.columns.tolist()
                for excel_col, db_col in column_mapping.items():
                    # 尝试匹配，忽略前后空格
                    matched_col = next((col for col in current_excel_columns if str(col).strip() == excel_col), None)
                    if matched_col:
                        rename_dict[matched_col] = db_col
                    else:
                        missing_cols.append(excel_col)
                
                if missing_cols:
                    print(f"    警告: 工作表 '{sheet_name}' 中缺少以下预期列: {', '.join(missing_cols)}")
                
                df.rename(columns=rename_dict, inplace=True)

                # 筛选出数据库表实际需要的列 (基于映射后的名称)
                db_columns = list(column_mapping.values())
                df_filtered = df[[col for col in db_columns if col in df.columns]].copy()
                
                # 添加固定的数据来源
                df_filtered['source'] = data_source 

                print(f"    找到 {len(df_filtered)} 行有效数据，准备插入...")
                sheet_inserted = 0

                for _, row in df_filtered.iterrows():
                    # 跳过药品名称为空的行
                    if pd.isna(row.get('drug_name')) or str(row.get('drug_name')).strip() == '' :
                        # print(f"    跳过: 药品名称为空的行") # 可以取消注释以查看跳过的行
                        continue
                    
                    # 准备插入的数据 (只包含实际存在的列，并处理NaN)
                    row_data = {} 
                    for db_col_name in list(column_mapping.values()) + ['source']: # 包括 source 列
                        if db_col_name in row.index:
                            value = row[db_col_name]
                            row_data[db_col_name] = None if pd.isna(value) else value
                    
                    if not row_data: # 如果行完全为空或只有NaN
                        continue
                        
                    cols = ', '.join([f'`{k}`' for k in row_data.keys()]) # 给列名加反引号以防关键字冲突
                    placeholders = ', '.join(['?' for _ in row_data.keys()])
                    sql = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"
                    
                    try:
                        values = list(row_data.values())
                        cursor.execute(sql, values)
                        sheet_inserted += 1
                    except sqlite3.IntegrityError as insert_err:
                         # 可以选择记录或跳过唯一约束冲突的记录
                         print(f"    跳过 (可能重复): {row_data.get('drug_name', 'N/A')} - {insert_err}")
                    except sqlite3.Error as db_err:
                        print(f"    数据库插入错误: {db_err}, SQL: {sql}, 值: {values}")
                    except Exception as general_err:
                         print(f"    处理行数据时发生未知错误: {general_err}, 数据: {row_data}")

                conn.commit() # 每个工作表处理完后提交一次
                print(f"    工作表 '{sheet_name}' 处理完成，插入 {sheet_inserted} 行")
                total_inserted_for_file += sheet_inserted

            except Exception as e:
                print(f"  处理工作表 '{sheet_name}' 时出错: {e}")

        print(f"\n文件 '{os.path.basename(excel_path)}' 处理完成，总共插入 {total_inserted_for_file} 行数据到表 '{table_name}'")
        return total_inserted_for_file

    except Exception as e:
        print(f"处理文件 {excel_path} 过程中发生错误: {e}")
        return total_inserted_for_file # 返回已插入的行数
    finally:
        if conn:
            conn.close()
            print(f"数据库连接已关闭 (文件: {os.path.basename(excel_path)}) ")

# --- 主程序入口 --- #
if __name__ == "__main__":
    # 确保安装了必要的库
    try:
        import openpyxl
    except ImportError:
        print("请先安装 openpyxl 库: pip install openpyxl")
    else:
        grand_total_inserted = 0
        # 遍历要处理的文件列表
        for file_info in FILES_TO_PROCESS:
            inserted_count = import_excel_to_db(
                excel_path=file_info["input_excel"],
                db_path=DB_FILE,
                table_name=file_info["table_name"],
                data_source=DATA_SOURCE_INFO,
                column_mapping=COLUMN_MAPPING
            )
            grand_total_inserted += inserted_count
        
        print(f"\n{'='*20} 所有文件处理完毕 {'='*20}")
        print(f"总共插入 {grand_total_inserted} 条记录到数据库。") 