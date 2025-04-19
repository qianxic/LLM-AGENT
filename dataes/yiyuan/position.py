import pandas as pd
import requests
import time
import json
import os
import sqlite3

# 高德API密钥
API_KEY = "9eff5d4edc50e9f9993ff751428fa8ed"

# 数据库路径
DB_FILE = "D:\\代码\\ESRI\\ture_small\\dataes\\table_total.db"

# 通过高德地图地理编码API获取坐标
def get_geocode(address, city="成都"):
    """
    使用高德地图地理编码API获取地址的经纬度坐标
    """
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": API_KEY,
        "address": address,
        "city": city,
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and int(data["count"]) > 0:
            location = data["geocodes"][0]["location"]
            longitude, latitude = location.split(",")
            return {
                "longitude": float(longitude),
                "latitude": float(latitude),
                "level": data["geocodes"][0].get("level", ""),  # 匹配级别
                "formatted_address": data["geocodes"][0].get("formatted_address", "")
            }
        else:
            print(f"未找到地址: {address}, 返回信息: {data}")
            return None
    except Exception as e:
        print(f"API请求出错: {e}")
        return None

# 智能构建搜索地址
def build_search_address(name, address=""):
    """
    智能构建用于地理编码的地址字符串，避免重复的城市前缀
    """
    # 如果有地址信息，优先使用地址
    if address and len(address) > 2:
        # 检查地址是否已经以城市名开头
        if address.startswith("成都市"):
            # 如果已经包含"成都市"，则使用"四川省"作为前缀
            return f"四川省{address}"
        elif address.startswith("四川省"):
            # 如果已经包含"四川省"，直接使用
            return address
        else:
            # 否则添加"四川省成都市"前缀
            return f"四川省成都市{address}"
    
    # 如果没有地址信息，使用医院名称
    if name.startswith("成都市"):
        return f"四川省{name}"
    elif name.startswith("四川省"):
        return name
    else:
        return f"四川省成都市{name}"

# 从数据库读取缺少坐标的医院
def get_hospitals_missing_coords(conn):
    """从数据库中获取缺少坐标信息的医院记录"""
    cursor = conn.cursor()
    
    # 查询经纬度为0或为NULL的医院记录
    cursor.execute('''
    SELECT id, name, address 
    FROM hospitals 
    WHERE latitude IS NULL OR latitude = 0 OR longitude IS NULL OR longitude = 0
    ''')
    
    hospitals = []
    for row in cursor.fetchall():
        hospitals.append({
            "id": row[0],
            "name": row[1],
            "address": row[2] if row[2] else ""
        })
    
    print(f"找到 {len(hospitals)} 家缺少坐标信息的医院")
    return hospitals

# 更新医院坐标
def update_hospital_coords(conn, hospital_id, coords):
    """更新数据库中医院的坐标信息"""
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE hospitals 
    SET latitude = ?, longitude = ?, address = CASE WHEN address IS NULL OR address = '' THEN ? ELSE address END
    WHERE id = ?
    ''', (
        coords["latitude"], 
        coords["longitude"], 
        coords["formatted_address"], 
        hospital_id
    ))
    
    conn.commit()
    return cursor.rowcount > 0

# 主函数 - 处理数据库中缺少坐标的医院
def process_hospitals_from_db():
    print(f"从数据库 {DB_FILE} 读取缺少坐标的医院记录")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(DB_FILE)
        
        # 获取缺少坐标的医院
        hospitals = get_hospitals_missing_coords(conn)
        
        if not hospitals:
            print("没有找到缺少坐标的医院，操作完成")
            conn.close()
            return
            
        # 处理每家医院
        success_count = 0
        failed_count = 0
        
        for hospital in hospitals:
            hospital_id = hospital["id"]
            name = hospital["name"]
            address = hospital["address"]
            
            print(f"\n处理医院ID {hospital_id}: {name}")
            
            # 构建搜索地址
            search_address = build_search_address(name, address)
            print(f"  搜索地址: {search_address}")
            
            # 获取坐标
            coords = get_geocode(search_address)
            
            if coords:
                print(f"  获取到坐标: ({coords['longitude']}, {coords['latitude']})")
                print(f"  匹配地址: {coords['formatted_address']}")
                print(f"  匹配级别: {coords['level']}")
                
                # 更新数据库
                if update_hospital_coords(conn, hospital_id, coords):
                    print(f"  已更新医院坐标")
                    success_count += 1
                else:
                    print(f"  更新医院坐标失败")
                    failed_count += 1
            else:
                # 如果使用地址+名称失败，尝试仅使用医院名称
                name_search = build_search_address(name)
                print(f"  尝试仅使用医院名称: {name_search}")
                
                coords = get_geocode(name_search)
                
                if coords:
                    print(f"  使用医院名称获取到坐标: ({coords['longitude']}, {coords['latitude']})")
                    print(f"  匹配地址: {coords['formatted_address']}")
                    print(f"  匹配级别: {coords['level']}")
                    
                    # 更新数据库
                    if update_hospital_coords(conn, hospital_id, coords):
                        print(f"  已更新医院坐标")
                        success_count += 1
                    else:
                        print(f"  更新医院坐标失败")
                        failed_count += 1
                else:
                    print(f"  无法获取坐标")
                    failed_count += 1
            
            # 添加延时，避免API请求过于频繁
            time.sleep(0.5)
        
        print(f"\n处理完成: 成功更新 {success_count} 家医院坐标，失败 {failed_count} 家")
        
        # 关闭数据库连接
        conn.close()
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

# 生成医院坐标报告
def generate_hospital_coords_report():
    """生成医院坐标数据报告"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 获取医院总数
        cursor.execute("SELECT COUNT(*) FROM hospitals")
        total_hospitals = cursor.fetchone()[0]
        
        # 获取有坐标的医院数量
        cursor.execute('''
        SELECT COUNT(*) FROM hospitals 
        WHERE latitude IS NOT NULL AND latitude != 0 
          AND longitude IS NOT NULL AND longitude != 0
        ''')
        coords_hospitals = cursor.fetchone()[0]
        
        # 获取缺少坐标的医院数量
        missing_coords = total_hospitals - coords_hospitals
        
        # 输出报告
        print("\n===== 医院坐标数据报告 =====")
        print(f"医院总数: {total_hospitals}")
        print(f"有坐标医院: {coords_hospitals} ({(coords_hospitals/total_hospitals*100):.2f}%)")
        print(f"缺少坐标医院: {missing_coords} ({(missing_coords/total_hospitals*100):.2f}%)")
        
        # 随机展示5个有坐标的医院
        cursor.execute('''
        SELECT id, name, latitude, longitude 
        FROM hospitals 
        WHERE latitude IS NOT NULL AND latitude != 0 
          AND longitude IS NOT NULL AND longitude != 0
        ORDER BY RANDOM() LIMIT 5
        ''')
        
        print("\n随机展示5个有坐标的医院:")
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, 名称: {row[1]}, 坐标: ({row[3]}, {row[2]})")
        
        conn.close()
    except Exception as e:
        print(f"生成报告时出错: {e}")

if __name__ == "__main__":
    # 处理数据库中缺少坐标的医院
    process_hospitals_from_db()
    
    # 生成坐标数据报告
    generate_hospital_coords_report()