import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

# 获取当前脚本所在的目录，然后构建数据库的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, '..', 'dataes', 'table_total.db') # 调整路径以匹配 D:\\代码\\ESRI\\tools_demo\\dataes\\table_total.db

logger.info(f"Database path determined as: {DATABASE_PATH}")

def get_db_connection():
    """建立并返回数据库连接"""
    conn = None
    try:
        if not os.path.exists(DATABASE_PATH):
             logger.error(f"Database file not found at path: {DATABASE_PATH}")
             raise FileNotFoundError(f"Database file not found at path: {DATABASE_PATH}")
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row # 让查询结果可以像字典一样访问列
        logger.info(f"Successfully connected to database: {DATABASE_PATH}")
    except sqlite3.Error as e:
        logger.error(f"Database connection error to {DATABASE_PATH}: {e}")
    except FileNotFoundError as e:
         logger.error(e) # Log specific file not found error
    except Exception as e:
        logger.error(f"An unexpected error occurred during DB connection: {e}")
    return conn

def query_hospitals_by_city(city_name: str):
    """根据城市名称查询医院信息"""
    conn = get_db_connection()
    hospitals = []
    if conn:
        try:
            cursor = conn.cursor()
            # 注意：假设 hospitals 表中有一个 city 列用于匹配，如果没有，需要调整SQL
            # 根据您提供的表结构，hospitals 表似乎没有 city 列。
            # 我们需要一种方法来关联城市。
            # 暂时假设所有医院都在一个城市，或者需要更复杂的查询逻辑。
            # 这里先查询所有医院作为示例，您需要根据实际情况调整。
            # TODO: Adjust SQL based on how city is associated with hospitals.
            #       Maybe query by address like '%成都%'? Or need a separate city table?
            #       For now, fetching all as a placeholder.
            #       Let's try filtering by address as an example.
            query = "SELECT name, address, latitude, longitude, level, type FROM hospitals WHERE address LIKE ?"
            logger.info(f"Executing SQL: {query} with city: {city_name}")
            # 使用 % 通配符进行模糊匹配
            cursor.execute(query, (f'%{city_name}%',))
            rows = cursor.fetchall()
            hospitals = [dict(row) for row in rows]
            logger.info(f"Found {len(hospitals)} hospitals for city like '{city_name}'")
        except sqlite3.Error as e:
            logger.error(f"Error querying hospitals for city {city_name}: {e}")
        finally:
            conn.close()
    else:
         logger.error("Failed to get database connection for querying hospitals.")
    return hospitals

def query_doctors_by_specialty_or_expertise(query: str, limit=5):
    """(初筛) 根据科室关键词查询医生及其医院信息，返回简要列表。"""
    conn = get_db_connection()
    doctors_with_hospitals = []
    if conn:
        try:
            cursor = conn.cursor()
            # 查询 doctors 表，并通过 hospital_id 连接 hospitals 表
            # 仅在 department 列中进行模糊匹配，并返回基本信息
            sql = """
            SELECT 
                d.id AS doctor_id, 
                d.name AS doctor_name,
                d.department,
                d.title,
                h.name AS hospital_name
            FROM doctors d
            JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.department LIKE ?
            LIMIT ?
            """
            search_term = f'%{query}%'
            logger.info(f"Executing SQL for doctors by department: {query} (LIMIT {limit})")
            cursor.execute(sql, (search_term, limit))
            rows = cursor.fetchall()
            doctors_with_hospitals = [dict(row) for row in rows]
            logger.info(f"Found {len(doctors_with_hospitals)} doctors matching department '{query}'")
        except sqlite3.Error as e:
            logger.error(f"Error querying doctors by department '{query}': {e}")
        finally:
            conn.close()
    else:
         logger.error("Failed to get database connection for querying doctors.")
    return doctors_with_hospitals

def get_doctor_details(doctor_id: int):
    """根据医生ID查询医生的详细信息及其医院信息"""
    conn = get_db_connection()
    doctor_details = None
    if conn:
        try:
            cursor = conn.cursor()
            sql = """
            SELECT 
                d.id AS doctor_id,
                d.name AS doctor_name,
                d.department,
                d.focused_diseases,
                d.expertise,
                d.introduction,
                d.education,
                d.title,
                d.likes,
                h.id AS hospital_id,
                h.name AS hospital_name,
                h.address AS hospital_address,
                h.latitude AS hospital_latitude,
                h.longitude AS hospital_longitude,
                h.level AS hospital_level,
                h.type AS hospital_type
            FROM doctors d
            JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.id = ?
            """
            logger.info(f"Executing SQL for doctor details with ID: {doctor_id}")
            cursor.execute(sql, (doctor_id,))
            row = cursor.fetchone()
            if row:
                doctor_details = dict(row)
                logger.info(f"Found details for doctor ID {doctor_id}")
            else:
                 logger.warning(f"No doctor found with ID {doctor_id}")
        except sqlite3.Error as e:
            logger.error(f"Error querying details for doctor ID {doctor_id}: {e}")
        finally:
            conn.close()
    else:
         logger.error("Failed to get database connection for querying doctor details.")
    return doctor_details # 返回包含详细信息的字典，或 None

def query_medicines(query: str, medicine_type: str = 'all', limit=10):
    """根据名称或关键词查询药品信息 (中药/西药/全部)"""
    conn = get_db_connection()
    medicines = []
    if conn:
        try:
            cursor = conn.cursor()
            search_term = f'%{query}%'
            sql_queries = []
            params = []
            
            # 根据类型构建查询
            if medicine_type in ['chinese', 'all']: # 注意表名大小写
                sql_queries.append("SELECT '中药' as type, drug_name, dosage_form, remarks FROM Chinese_medicine WHERE drug_name LIKE ?")
                params.append(search_term)
            if medicine_type in ['western', 'all']: # 注意表名大小写
                sql_queries.append("SELECT '西药' as type, drug_name, dosage_form, remarks FROM Western_medicine WHERE drug_name LIKE ?")
                params.append(search_term)
                
            if not sql_queries:
                 logger.warning(f"Invalid medicine type specified: {medicine_type}")
                 return []
                 
            # 合并查询结果 (如果需要查询所有类型)
            full_query = " UNION ALL ".join(sql_queries)
            full_query += " LIMIT ?"
            params.append(limit)
            
            logger.info(f"Executing SQL for medicines with query: {query}, type: {medicine_type} (LIMIT {limit})")
            cursor.execute(full_query, tuple(params))
            rows = cursor.fetchall()
            medicines = [dict(row) for row in rows]
            logger.info(f"Found {len(medicines)} medicines matching '{query}' (type: {medicine_type})")
            
        except sqlite3.Error as e:
            logger.error(f"Error querying medicines for '{query}': {e}")
        finally:
            conn.close()
    else:
         logger.error("Failed to get database connection for querying medicines.")
    return medicines

def check_medicine_existence(medicine_name: str):
    """(模糊)查询指定药品名称是否存在于中药或西药数据库中"""
    conn = get_db_connection()
    found_medicine = None
    if conn:
        try:
            cursor = conn.cursor()
            # 修改为模糊匹配
            search_term = f'%{medicine_name}%'
            sql = """
            SELECT '中药' as type, drug_name, dosage_form, remarks 
            FROM Chinese_medicine 
            WHERE drug_name LIKE ?
            UNION ALL
            SELECT '西药' as type, drug_name, dosage_form, remarks 
            FROM Western_medicine 
            WHERE drug_name LIKE ?
            LIMIT 1
            """
            logger.info(f"Executing SQL to check existence (fuzzy) for medicine: {medicine_name}")
            cursor.execute(sql, (search_term, search_term))
            row = cursor.fetchone()
            if row:
                found_medicine = dict(row)
                logger.info(f"Medicine like '{medicine_name}' found in the database.")
            else:
                 logger.info(f"Medicine like '{medicine_name}' not found in the database.")
        except sqlite3.Error as e:
            logger.error(f"Error checking existence (fuzzy) for medicine '{medicine_name}': {e}")
        finally:
            conn.close()
    else:
         logger.error("Failed to get database connection for checking medicine existence.")
    return found_medicine # 返回找到的药品信息字典，或 None

# 可以根据需要添加更多查询函数，例如：
# def query_doctors_by_hospital(hospital_name: str): ...
# def query_medicine_by_name(medicine_name: str): ...

if __name__ == '__main__':
    # 测试连接和查询
    print(f"Attempting to connect to DB at: {DATABASE_PATH}")
    if not os.path.exists(DATABASE_PATH):
        print(f"ERROR: Database file does not exist at the path: {DATABASE_PATH}")
    else:
        print("Database file found.")
        connection = get_db_connection()
        if connection:
            print("Database connection successful.")
            connection.close()
            
            print("\nTesting hospital query for '成都':")
            test_hospitals = query_hospitals_by_city('成都')
            if test_hospitals:
                print(f"Found {len(test_hospitals)} hospitals:")
                for hospital in test_hospitals[:2]: # Print first 2 results
                     print(f"  - {hospital['name']} ({hospital['level']}) at {hospital['address']}")
            else:
                 print("No hospitals found for '成都'. Check query logic or data.")
        else:
            print("Database connection failed.") 