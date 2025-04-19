import os
import json
import glob
from datetime import datetime

# 配置路径
BASE_DIR = "D:\\代码\\ESRI\\ture_small\\dataes\\yisheng"
DATA_CHUNYU_DIR = os.path.join(BASE_DIR, "data_chunyu")
DATA_WEIYI_DIR = os.path.join(BASE_DIR, "data_weiyi")
OUTPUT_DIR = BASE_DIR
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"merged_hospital_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

def load_json_file(file_path):
    """加载JSON文件，处理可能的异常"""
    try:
        if os.path.getsize(file_path) == 0:
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 如果数据是空列表，直接返回
        if not data or (isinstance(data, list) and len(data) == 0):
            return []
            
        # 确保数据是列表格式
        if not isinstance(data, list):
            data = [data]
            
        return data
    except Exception as e:
        print(f"加载文件 {file_path} 时出错: {str(e)}")
        return []

def normalize_doctor_data(doctor, hospital_name=None):
    """规范化医生数据，确保所有字段存在"""
    # 通用字段
    standard_fields = {
        "name": "",
        "hospital_name": "",
        "department": "",
        "focused_diseases": "",
        "expertise": "",
        "introduction": "",
        "education": "",
        "title": "",
        "likes": 0,
        "source": ""  # 添加来源字段，标识数据来自哪个平台
    }
    
    # 创建标准化的医生数据
    normalized_doctor = standard_fields.copy()
    
    # 更新数据
    for key, value in doctor.items():
        if key in normalized_doctor:
            normalized_doctor[key] = value
    
    # 如果没有医院名称，使用文件名中的医院名称
    if not normalized_doctor["hospital_name"] and hospital_name:
        normalized_doctor["hospital_name"] = hospital_name
        
    return normalized_doctor

def extract_hospital_name_from_path(file_path):
    """从文件路径中提取医院名称"""
    filename = os.path.basename(file_path)
    hospital_name = os.path.splitext(filename)[0]
    return hospital_name

def process_directory(directory, source_name):
    """处理目录中的所有JSON文件，返回合并后的数据"""
    all_doctors = []
    
    # 获取目录中的所有JSON文件
    json_files = glob.glob(os.path.join(directory, "*.json"))
    print(f"在 {directory} 中找到 {len(json_files)} 个JSON文件")
    
    for file_path in json_files:
        hospital_name = extract_hospital_name_from_path(file_path)
        print(f"处理医院: {hospital_name}")
        
        # 加载数据
        doctors = load_json_file(file_path)
        
        if not doctors:
            print(f"跳过空文件或无医生数据: {file_path}")
            continue
        
        # 规范化并添加来源
        for doctor in doctors:
            normalized_doctor = normalize_doctor_data(doctor, hospital_name)
            normalized_doctor["source"] = source_name
            all_doctors.append(normalized_doctor)
            
        print(f"从 {hospital_name} 添加了 {len(doctors)} 位医生")
        
    return all_doctors

def merge_all_data():
    """合并所有数据源的医生信息"""
    merged_data = []
    
    # 处理春雨医生数据
    chunyu_doctors = process_directory(DATA_CHUNYU_DIR, "春雨医生")
    print(f"从春雨医生获取了 {len(chunyu_doctors)} 位医生信息")
    merged_data.extend(chunyu_doctors)
    
    # 处理微医数据
    weiyi_doctors = process_directory(DATA_WEIYI_DIR, "微医")
    print(f"从微医获取了 {len(weiyi_doctors)} 位医生信息")
    merged_data.extend(weiyi_doctors)
    
    return merged_data

def save_merged_data(data):
    """保存合并后的数据到文件"""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"合并数据已保存到: {OUTPUT_FILE}")
        print(f"共有 {len(data)} 位医生信息")
        return True
    except Exception as e:
        print(f"保存数据时出错: {str(e)}")
        return False

def main():
    print("开始合并医院医生数据...")
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 合并数据
    merged_data = merge_all_data()
    
    # 删除重复数据 (根据医生姓名和医院去重)
    unique_doctors = {}
    for doctor in merged_data:
        key = f"{doctor['name']}_{doctor['hospital_name']}"
        
        # 如果已存在，优先保留信息更丰富的记录
        if key in unique_doctors:
            existing_doctor = unique_doctors[key]
            # 计算非空字段数量
            existing_non_empty = sum(1 for k, v in existing_doctor.items() if v)
            current_non_empty = sum(1 for k, v in doctor.items() if v)
            
            # 保留信息更丰富的记录
            if current_non_empty > existing_non_empty:
                unique_doctors[key] = doctor
        else:
            unique_doctors[key] = doctor
    
    # 转换回列表
    deduplicated_data = list(unique_doctors.values())
    
    print(f"去重后共有 {len(deduplicated_data)} 位医生信息")
    
    # 保存数据
    save_merged_data(deduplicated_data)
    
    print("数据合并完成!")

if __name__ == "__main__":
    main() 