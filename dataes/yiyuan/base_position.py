import pandas as pd
import requests
import time
import json
import os

# 高德API密钥
API_KEY = "9eff5d4edc50e9f9993ff751428fa8ed"

# 读取CSV文件
def load_hospitals_data(csv_path):
    try:
        # 修改为使用逗号分隔符，与实际CSV格式匹配
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"成功读取 {len(df)} 条医院数据")
        # 检查并规范列名
        if '序号' in df.columns and '机构名称' in df.columns:
            print("CSV列名格式正确")
        else:
            print("警告: CSV列名可能不匹配预期格式，请检查CSV文件")
        return df
    except Exception as e:
        print(f"读取CSV文件出错: {e}")
        return None

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
def build_search_address(address, name):
    """
    智能构建用于地理编码的地址字符串，避免重复的城市前缀
    """
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

# 主函数
def process_hospitals():
    # 读取CSV文件
    df = load_hospitals_data("ture_small/data/base.csv")
    if df is None:
        return
    
    # 确保列名正确，如果有列名但不存在，给出警告
    if '机构名称' not in df.columns:
        print("错误: CSV中缺少'机构名称'列，无法继续")
        return
    if '地址' not in df.columns:
        print("错误: CSV中缺少'地址'列，无法继续")
        return
        
    # 检查是否已有经纬度列
    has_coords = 'longitude' in df.columns and 'latitude' in df.columns
    if has_coords:
        print("CSV已包含经纬度列，将只更新缺失值")
    else:
        # 添加经纬度列
        df["longitude"] = None
        df["latitude"] = None
    
    # 添加其他列（如果不存在）
    if "formatted_address" not in df.columns:
        df["formatted_address"] = None
    if "match_level" not in df.columns:
        df["match_level"] = None
    
    # 遍历每个医院获取经纬度
    for index, row in df.iterrows():
        name = row["机构名称"]
        address = row["地址"]
        
        # 检查是否已有经纬度且不为空
        if has_coords and pd.notna(row["longitude"]) and pd.notna(row["latitude"]):
            print(f"跳过: {name} - 已有坐标: ({row['longitude']}, {row['latitude']})")
            continue
        
        print(f"正在处理: {name}")
        
        # 智能构建搜索地址
        full_address = build_search_address(address, name)
        
        # 构建名称搜索地址
        if name.startswith("成都市"):
            name_search = f"四川省{name}"
        else:
            name_search = f"四川省成都市{name}"
        
        print(f"  搜索地址: {full_address}")
        result = get_geocode(full_address)
        
        if result:
            df.at[index, "longitude"] = result["longitude"]
            df.at[index, "latitude"] = result["latitude"]
            df.at[index, "formatted_address"] = result["formatted_address"]
            df.at[index, "match_level"] = result["level"]
            print(f"  已获取坐标: ({result['longitude']}, {result['latitude']}), 匹配级别: {result['level']}")
        else:
            # 如果使用完整地址失败，尝试仅使用医院名称
            print(f"  尝试使用医院名称: {name_search}")
            result = get_geocode(name_search)
            if result:
                df.at[index, "longitude"] = result["longitude"]
                df.at[index, "latitude"] = result["latitude"]
                df.at[index, "formatted_address"] = result["formatted_address"]
                df.at[index, "match_level"] = result["level"]
                print(f"  使用医院名称获取坐标: ({result['longitude']}, {result['latitude']}), 匹配级别: {result['level']}")
            else:
                # 如果两种方法都失败，尝试直接使用不带前缀的地址
                print(f"  尝试直接使用地址: {address}")
                result = get_geocode(address)
                if result:
                    df.at[index, "longitude"] = result["longitude"]
                    df.at[index, "latitude"] = result["latitude"]
                    df.at[index, "formatted_address"] = result["formatted_address"]
                    df.at[index, "match_level"] = result["level"]
                    print(f"  使用原始地址获取坐标: ({result['longitude']}, {result['latitude']}), 匹配级别: {result['level']}")
                else:
                    print(f"  所有方法均未能获取坐标")
        
        # 添加延时，避免API请求过于频繁
        time.sleep(0.3)
    
    # 保存结果到CSV文件
    output_dir = "ture_small/data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = f"{output_dir}/hospitals_with_geocode.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"处理完成，数据已保存到: {output_path}")
    
    # 生成数据库插入SQL语句
    generate_sql_insert(df, f"{output_dir}/hospitals_insert.sql")

# 生成SQL插入语句
def generate_sql_insert(df, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-- 医院数据插入SQL语句\n\n")
        
        for index, row in df.iterrows():
            # 跳过没有获取到坐标的记录
            if pd.isna(row["longitude"]) or pd.isna(row["latitude"]):
                continue
                
            # 判断医院类型和等级
            hospital_type = "社区卫生服务中心" if "社区卫生服务中心" in row["机构名称"] else \
                            "卫生院" if "卫生院" in row["机构名称"] else \
                            "中医医院" if "中医" in row["机构名称"] else \
                            "妇幼保健院" if "妇幼" in row["机构名称"] else \
                            "综合医院"
                            
            hospital_level = "三级甲等" if "第一人民医院" in row["机构名称"] else \
                             "三级乙等" if "第二人民医院" in row["机构名称"] else \
                             "二级甲等" if "第三人民医院" in row["机构名称"] else \
                             "基层医疗机构" if ("社区卫生服务中心" in row["机构名称"] or "卫生院" in row["机构名称"]) else \
                             "三级甲等" if "人民医院" in row["机构名称"] and not any(x in row["机构名称"] for x in ["第二", "第三"]) else \
                             ""
            
            # 替换单引号，避免SQL语法错误
            name = str(row["机构名称"]).replace("'", "''")
            address = str(row["地址"]).replace("'", "''") if not pd.isna(row["地址"]) else ""
            
            # 处理电话号码 - 有些可能是连在一起的多个号码
            phone = str(row["电话号码"]).replace("'", "''") if not pd.isna(row["电话号码"]) else ""
            # 尝试将连在一起的电话号码分开，如果长度超过12位
            if len(phone) > 12 and phone.isdigit():
                # 尝试按照常见的固定电话长度(8位)分割
                phones = []
                for i in range(0, len(phone), 11):
                    if i + 11 <= len(phone):
                        phones.append(phone[i:i+11])
                    else:
                        phones.append(phone[i:])
                phone = ",".join(phones)
            
            # 生成INSERT语句
            sql = f"""INSERT INTO hospitals (name, address, latitude, longitude, level, type, contact_phone, is_insurance_designated)
VALUES ('{name}', '{address}', {row['latitude']}, {row['longitude']}, '{hospital_level}', '{hospital_type}', '{phone}', 1);
"""
            f.write(sql)
        
        print(f"SQL插入语句已生成到: {output_file}")

if __name__ == "__main__":
    process_hospitals()