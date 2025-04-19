import sqlite3
import os
import json

# --- 配置数据库路径 ---
# 获取当前脚本所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 构建数据库文件的绝对路径 (根据您的实际路径调整)
# 假设 explore_db.py 与 database_utils.py 在同一目录
DATABASE_PATH = os.path.join(BASE_DIR, '..', 'dataes', 'table_total.db')
print(f"数据库路径: {DATABASE_PATH}\n")

def get_db_connection():
    """建立数据库连接"""
    conn = None
    try:
        if not os.path.exists(DATABASE_PATH):
            print(f"错误: 数据库文件未找到于 '{DATABASE_PATH}'")
            return None
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row # 返回字典式行
        print("数据库连接成功!")
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
    except Exception as e:
        print(f"连接时发生未知错误: {e}")
    return conn

def fetch_sample_data(table_name, limit=5):
    """获取指定表的前N行数据"""
    conn = get_db_connection()
    data = []
    if conn:
        try:
            cursor = conn.cursor()
            query = f"SELECT * FROM {table_name} LIMIT ?"
            print(f"执行查询: {query} (LIMIT {limit}) on table '{table_name}'")
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            # 将 sqlite3.Row 对象转换为字典列表以便打印
            data = [dict(row) for row in rows]
            print(f"成功获取 {len(data)} 行数据.")
        except sqlite3.Error as e:
            print(f"查询表 '{table_name}' 时出错: {e}")
        finally:
            conn.close()
            print("数据库连接已关闭.")
    return data

if __name__ == '__main__':
    tables_to_explore = [
        'hospitals',
        'doctors',
        'Chinese_medicine',
        'Western_medicine'
    ]

    all_sample_data = {}

    for table in tables_to_explore:
        print(f"\n--- 正在查询表: {table} ---")
        sample_data = fetch_sample_data(table, limit=5)
        all_sample_data[table] = sample_data
        
        if sample_data:
            print(f"\n--- 表 '{table}' 的前 {len(sample_data)} 行示例数据 ---")
            for i, row in enumerate(sample_data):
                # 为了更清晰地打印，将字典转换为JSON字符串（带缩进）
                print(f"  行 {i+1}:")
                print(json.dumps(row, indent=4, ensure_ascii=False))
        else:
            print(f"未能获取表 '{table}' 的示例数据.")
            
    print("\n--- 数据探索完成 --- " ) 