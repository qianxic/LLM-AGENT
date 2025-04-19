import sqlite3
import os

# --- 配置 --- #
# SQLite数据库文件路径
DB_FILE = r"D:\代码\ESRI\ture_small\dataes\table_total.db"
# --- 配置结束 --- #

def print_table_structure(db_path):
    """连接到SQLite数据库并打印所有表的结构"""
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()

        if not tables:
            print(f"数据库 '{os.path.basename(db_path)}' 中没有找到任何表。")
            return

        print(f"--- 数据库: {os.path.basename(db_path)} 表结构 ---")

        # 2. 遍历每个表并获取结构
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            # 跳过SQLite内部表
            if table_name.startswith('sqlite_'):
                continue
                
            print(f"\n=== 表: {table_name} ===")

            # 使用 PRAGMA 获取表信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            if not columns:
                print("  (无法获取列信息或表为空)")
                continue

            # 打印表头
            print(f"  {'列名':<25} {'类型':<15} {'允许NULL':<10} {'默认值':<15} {'主键':<5}")
            print("  " + "-"*75)

            # 打印每一列的信息
            for col in columns:
                col_id, name, dtype, notnull, dflt_value, pk = col
                # 格式化输出
                is_nullable = "NO" if notnull else "YES"
                is_pk = "YES" if pk > 0 else "NO"
                default_val_str = str(dflt_value) if dflt_value is not None else "NULL"
                
                print(f"  {name:<25} {dtype:<15} {is_nullable:<10} {default_val_str:<15} {is_pk:<5}")
            
            # (可选) 打印索引信息
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            if indexes:
                print("\n  --- 索引 ---")
                for index in indexes:
                    index_seq, index_name, unique, origin, partial = index
                    # 获取索引包含的列
                    cursor.execute(f"PRAGMA index_info('{index_name}')")
                    index_cols_info = cursor.fetchall()
                    index_cols = ", ".join([info[2] for info in index_cols_info])
                    unique_str = "UNIQUE" if unique else ""
                    print(f"    {index_name:<25} ({index_cols}) {unique_str}")
                    
            # (可选) 打印外键信息
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                print("\n  --- 外键 ---")
                for fk in foreign_keys:
                    fk_id, seq, table, fk_from, fk_to, on_update, on_delete, match = fk
                    print(f"    列 '{fk_from}' 参照表 '{table}' 的列 '{fk_to}'")

    except sqlite3.Error as e:
        print(f"访问数据库时出错: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    finally:
        if conn:
            conn.close()
            print("\n数据库连接已关闭。")

# --- 主程序入口 --- #
if __name__ == "__main__":
    print_table_structure(DB_FILE) 