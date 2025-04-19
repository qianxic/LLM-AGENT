import os
import json
import sqlite3
from datetime import datetime

# 配置路径
BASE_DIR = "D:\\代码\\ESRI\\ture_small\\dataes\\yisheng"
JSON_FILE = os.path.join(BASE_DIR, "yisheng.json")
DB_FILE = "D:\\代码\\ESRI\\ture_small\\dataes\\table_total.db"

def load_json_data(json_file):
    """加载JSON数据文件"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"已加载 {len(data)} 条医生记录")
        return data
    except Exception as e:
        print(f"加载JSON数据时出错: {e}")
        return []

def ensure_hospitals_exist(conn, doctors_data):
    """确保所有医院都存在于hospitals表中"""
    cursor = conn.cursor()
    
    # 获取医生数据中的所有医院
    hospitals = set()
    for doctor in doctors_data:
        if doctor.get("hospital_name"):
            hospitals.add(doctor["hospital_name"])
    
    hospital_id_map = {}  # 用于存储医院名称到ID的映射
    
    for hospital_name in hospitals:
        # 查询医院是否已存在
        cursor.execute("SELECT id FROM hospitals WHERE name = ?", (hospital_name,))
        result = cursor.fetchone()
        
        if result:
            # 医院已存在，记录ID
            hospital_id = result[0]
            hospital_id_map[hospital_name] = hospital_id
            print(f"医院已存在: {hospital_name} (ID: {hospital_id})")
        else:
            # 医院不存在，添加临时记录
            print(f"警告: 医院 '{hospital_name}' 在hospitals表中不存在")
            # 添加带有临时坐标的记录
            cursor.execute(
                "INSERT INTO hospitals (name, latitude, longitude) VALUES (?, 0, 0)",
                (hospital_name,)
            )
            hospital_id = cursor.lastrowid
            hospital_id_map[hospital_name] = hospital_id
            print(f"已添加临时医院记录: {hospital_name} (ID: {hospital_id})")
    
    conn.commit()
    return hospital_id_map

def import_doctors(conn, doctors_data, hospital_id_map):
    """将医生数据导入到doctors表"""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    
    for doctor in doctors_data:
        hospital_name = doctor.get("hospital_name", "")
        if not hospital_name or hospital_name not in hospital_id_map:
            print(f"跳过: {doctor.get('name', 'Unknown')} - 无法找到医院ID")
            skipped += 1
            continue
        
        hospital_id = hospital_id_map[hospital_name]
        
        try:
            # 检查医生是否已存在
            cursor.execute(
                "SELECT id FROM doctors WHERE name = ? AND hospital_id = ?", 
                (doctor["name"], hospital_id)
            )
            
            if cursor.fetchone():
                # 更新现有记录
                cursor.execute('''
                UPDATE doctors SET 
                    department = ?,
                    focused_diseases = ?,
                    expertise = ?,
                    introduction = ?,
                    education = ?,
                    title = ?,
                    likes = ?,
                    source = ?
                WHERE name = ? AND hospital_id = ?
                ''', (
                    doctor.get("department", ""),
                    doctor.get("focused_diseases", ""),
                    doctor.get("expertise", ""),
                    doctor.get("introduction", ""),
                    doctor.get("education", ""),
                    doctor.get("title", ""),
                    doctor.get("likes", 0),
                    doctor.get("source", ""),
                    doctor["name"],
                    hospital_id
                ))
            else:
                # 插入新记录
                cursor.execute('''
                INSERT INTO doctors (
                    name, hospital_id, department, focused_diseases,
                    expertise, introduction, education, title, likes, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    doctor["name"],
                    hospital_id,
                    doctor.get("department", ""),
                    doctor.get("focused_diseases", ""),
                    doctor.get("expertise", ""),
                    doctor.get("introduction", ""),
                    doctor.get("education", ""),
                    doctor.get("title", ""),
                    doctor.get("likes", 0),
                    doctor.get("source", "")
                ))
                inserted += 1
            
            # 每500条记录提交一次
            if inserted % 500 == 0:
                conn.commit()
                print(f"已处理 {inserted} 条记录...")
                
        except Exception as e:
            print(f"处理医生 '{doctor.get('name', 'Unknown')}' 数据时出错: {e}")
            skipped += 1
    
    conn.commit()
    return inserted, skipped

def main():
    print(f"开始将数据从 {JSON_FILE} 导入到 {DB_FILE}")
    
    # 检查文件是否存在
    if not os.path.exists(JSON_FILE):
        print(f"错误: JSON文件不存在 - {JSON_FILE}")
        return
    
    try:
        # 加载JSON数据
        doctors_data = load_json_data(JSON_FILE)
        if not doctors_data:
            print("没有可导入的数据")
            return
        
        # 连接数据库
        conn = sqlite3.connect(DB_FILE)
        
        # 检查doctors表是否存在
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='doctors'")
        if not cursor.fetchone():
            print("错误: 数据库中不存在doctors表")
            conn.close()
            return
        
        # 确保所有医院存在，并获取医院ID映射
        print("\n确保医院数据存在...")
        hospital_id_map = ensure_hospitals_exist(conn, doctors_data)
        
        # 导入医生数据
        print("\n开始导入医生数据...")
        inserted, skipped = import_doctors(conn, doctors_data, hospital_id_map)
        
        print(f"\n导入完成: 成功导入 {inserted} 条记录, 跳过 {skipped} 条记录")
        
        # 关闭连接
        conn.close()
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")

if __name__ == "__main__":
    main() 