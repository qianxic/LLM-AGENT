import os
import json
import glob

# --- 配置 ---
# JSON 文件所在的目录 (请确保路径正确)
JSON_DIR = r"D:\代码\ESRI\ture_small\dataes\yisheng\data"
# 要检查的字符
CITY_MARKER = "市"
DISTRICT_MARKER = "区"
# 要保留的特定城市/区域字符串
KEEP_CITY = "成都市"
KEEP_DISTRICT = "新都区"
# --- 配置结束 ---

print(f"开始清理目录中的JSON文件: {JSON_DIR}")

# 查找所有 .json 文件
json_files = glob.glob(os.path.join(JSON_DIR, "*.json"))

if not json_files:
    print("错误：在指定目录下未找到任何 .json 文件。请检查路径。")
else:
    print(f"找到 {len(json_files)} 个 JSON 文件，开始处理...")

modified_files_count = 0

for filepath in json_files:
    filename = os.path.basename(filepath)
    # print(f"  处理文件: {filename}") # 简化输出，只在移除时打印
    needs_update = False
    original_doctors = []
    kept_doctors = []

    try:
        # 读取原始JSON数据
        with open(filepath, 'r', encoding='utf-8') as f:
            original_doctors = json.load(f)

        if not isinstance(original_doctors, list):
            print(f"    警告: 文件 {filename} 格式不正确，不是列表，已跳过。")
            continue

        # 遍历医生列表进行筛选
        for doctor in original_doctors:
            expertise = doctor.get("expertise", "") # 安全获取expertise字段
            remove_doctor = False
            reason = ""

            # 检查条件
            if isinstance(expertise, str):
                expertise_stripped = expertise.strip()
                # 条件1: 包含"市"但不包含"成都市"
                if CITY_MARKER in expertise_stripped and KEEP_CITY not in expertise_stripped:
                    remove_doctor = True
                    reason = f"包含'{CITY_MARKER}'但不是'{KEEP_CITY}'"
                # 条件2: 包含"区"但不包含"新都区" (如果条件1不满足才检查条件2)
                elif DISTRICT_MARKER in expertise_stripped and KEEP_DISTRICT not in expertise_stripped:
                    remove_doctor = True
                    reason = f"包含'{DISTRICT_MARKER}'但不是'{KEEP_DISTRICT}'"

            if remove_doctor:
                if not needs_update: # 只在第一次移除时打印文件名
                    print(f"  处理文件: {filename}")
                print(f"      - 移除医生 '{doctor.get('name')}' (原因: {reason}, expertise='{expertise[:50]}...')")
                needs_update = True # 标记此文件需要被重写
            else:
                # 保留该医生记录
                kept_doctors.append(doctor)

        # 如果有记录被移除，则重写文件
        if needs_update:
            original_count = len(original_doctors)
            new_count = len(kept_doctors)
            print(f"    文件 {filename} 需要更新。移除 {original_count - new_count} 条记录。")
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(kept_doctors, f, ensure_ascii=False, indent=4)
                # print(f"      已更新文件: {filename}") # 简化输出
                modified_files_count += 1
            except Exception as write_err:
                print(f"      错误: 写入文件 {filename} 失败: {write_err}")
        # else:
            # print(f"    文件 {filename} 无需更新。") # 简化输出

    except json.JSONDecodeError:
        print(f"    错误: 文件 {filename} 不是有效的JSON格式，已跳过。")
    except Exception as e:
        print(f"    处理文件 {filename} 时发生意外错误: {e}")

print(f"\n处理完成。共修改了 {modified_files_count} 个文件。") 