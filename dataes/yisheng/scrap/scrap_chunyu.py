import os
import json
import time
import logging
import traceback
import random  # 添加random模块用于随机延迟
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chunyu_scraping.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置保存路径
# 注意：路径从 'data' 改为 'dataes' 以匹配您的项目结构
BASE_DIR = "D:\\代码\\ESRI\\ture_small\\dataes\\yisheng" 
DATA_DIR = os.path.join(BASE_DIR, "data_chunyu")
os.makedirs(DATA_DIR, exist_ok=True)

# 抓取配置
# 增加延迟设置以应对429错误
MIN_PAGE_DELAY = 3  # 页面之间的最小延迟（秒）
MAX_PAGE_DELAY = 7  # 页面之间的最大延迟（秒）
MIN_DOCTOR_DELAY = 2  # 医生详情页之间的最小延迟（秒）
MAX_DOCTOR_DELAY = 5  # 医生详情页之间的最大延迟（秒）
MAX_RETRIES = 3  # 遇到429错误时的最大重试次数
RETRY_DELAY = 60  # 遇到429错误时的等待时间（秒）

# 配置医院列表 (使用您提供的列表)
HOSPITALS = [
    "成都市新都区中医医院",
    "成都市新都区第二人民医院",
    "成都市新都区妇幼保健院",
    "成都市新都区人民医院",
    "成都市新都区新都街道龙虎社区卫生服务中心",
    "成都市新都区新繁街道社区卫生服务中心",
    "成都市新都区石板滩街道木兰社区卫生服务中心",
    "成都市新都区桂湖街道城东社区卫生服务中心",
    "成都市新都区清流镇卫生院",
    "成都市新都区石板滩街道社区卫生服务中心",
    "成都市新都区第三人民医院",
    "成都市新都区新繁街道龙桥社区卫生服务中心",
    "成都市新都区三河街道社区卫生服务中心",
    "成都市新都区军屯镇中心卫生院",
    "成都市新都区斑竹园街道社区卫生服务中心",
    "成都市新都区桂湖街道城西社区卫生服务中心",
    "成都市新都区新都街道蜀都社区卫生服务中心",
    "成都市新都区大丰街道太平社区卫生服务中心",
    "成都市新都区大丰街道丰安社区卫生服务中心"
]

def setup_driver():
    """设置并返回WebDriver"""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 暂时禁用无头模式，方便调试
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # 添加更真实的User-Agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # 禁用自动化控制特征
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    
    # 执行一些JavaScript来隐藏WebDriver的自动化特征
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def get_doctor_info(driver, doctor_url, search_department="", search_expertise=""):
    """获取医生详细信息 - 根据 doctor_example_doctor.html 调整选择器"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            # 随机延迟，模拟人类行为
            delay = random.uniform(MIN_DOCTOR_DELAY, MAX_DOCTOR_DELAY)
            logger.info(f"访问医生详情页前等待 {delay:.2f} 秒...")
            time.sleep(delay)
            
            driver.get(doctor_url)
            # 等待医生信息区域加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".doctor-wrap")) 
            )
            
            # 检查是否遇到了429错误
            if "429" in driver.title or "Too Many Requests" in driver.page_source:
                logger.warning(f"遇到 429 Too Many Requests 错误，重试 {retries+1}/{MAX_RETRIES}")
                time.sleep(RETRY_DELAY)  # 遇到429时等待更长时间
                retries += 1
                continue
            
            # 提取医生姓名
            try:
                name = driver.find_element(By.CSS_SELECTOR, ".doctor-left-wrap .detail .name").text.strip()
            except NoSuchElementException:
                name = "未知"
                logger.warning(f"无法在 {doctor_url} 找到医生姓名")
                
            # 提取医院名称
            try:
                hospital = driver.find_element(By.CSS_SELECTOR, ".doctor-left-wrap .detail .hospital").text.strip()
            except NoSuchElementException:
                hospital = "未知"
                logger.warning(f"无法在 {doctor_url} 找到医院名称")
                
            # 提取科室 (优先使用详情页的)
            try:
                department = driver.find_element(By.CSS_SELECTOR, ".doctor-left-wrap .detail .clinic").text.strip()
            except NoSuchElementException:
                department = search_department if search_department else "未知"
                logger.warning(f"无法在 {doctor_url} 找到科室，使用搜索页信息: {department}")
            
            # 提取职称
            try:
                title = driver.find_element(By.CSS_SELECTOR, ".doctor-left-wrap .detail .grade").text.strip()
            except NoSuchElementException:
                title = "未知"
                logger.warning(f"无法在 {doctor_url} 找到职称")

            # 提取医生介绍、擅长、教育背景等信息 (这些信息现在都在 .paragraph 中)
            introduction = "未提供"
            expertise_summary = search_expertise if search_expertise else "未提供" # 优先用搜索页的擅长
            education = "未提供"
            
            try:
                paragraphs = driver.find_elements(By.CSS_SELECTOR, ".paragraph .detail")
                for p in paragraphs:
                    p_text = p.text.strip()
                    if "个人简介 :" in p_text:
                        introduction = p_text.replace("个人简介 :", "").strip()
                    elif "擅长：" in p_text: # 详情页可能没有专门的擅长字段，简介里可能有
                         # 如果详情页有更详细的，可以考虑覆盖搜索页的
                         # expertise_summary = p_text.replace("擅长：", "").strip()
                         pass 
                    elif "医学教育背景介绍 :" in p_text:
                         education = p_text.replace("医学教育背景介绍 :", "").strip()

            except NoSuchElementException:
                 logger.warning(f"无法在 {doctor_url} 找到介绍段落")
            except Exception as e:
                 logger.error(f"解析介绍段落时出错 {doctor_url}: {e}")


            # doctor_data = {
            #     "doctor_name": name,
            #     "doctor_url": doctor_url,
            #     "workplace": hospital,
            #     "department": department,
            #     "title": title,
            #     "expertise": expertise_summary, # 使用从搜索页传来的或默认值
            #     "introduction": introduction,
            #     "education": education
            # }

            # 构建符合新格式的JSON对象
            doctor_data = {
                "name": name,
                "hospital_name": hospital,
                "department": department,
                "focused_diseases": "", # 根据示例，留空
                "expertise": department, # 根据示例 "expertise": "普外科", 使用科室
                "introduction": introduction,
                "education": education,
                "likes": 0 # 根据示例，默认为0
            }
            
            return doctor_data
        except TimeoutException:
            logger.warning(f"加载医生详情页超时: {doctor_url}，重试 {retries+1}/{MAX_RETRIES}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(RETRY_DELAY)  # 遇到超时也等待
            else:
                logger.error(f"多次加载超时，放弃获取医生信息: {doctor_url}")
                return None
        except WebDriverException as e:
            if "429" in str(e):
                logger.warning(f"遇到 429 Too Many Requests 错误，重试 {retries+1}/{MAX_RETRIES}")
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"多次请求被拒绝，放弃获取医生信息: {doctor_url}")
                    return None
            else:
                logger.error(f"获取医生信息时发生WebDriver错误 {doctor_url}: {str(e)}")
                logger.error(traceback.format_exc())
                return None
        except Exception as e:
            logger.error(f"获取医生信息时发生意外错误 {doctor_url}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    # 如果所有重试都失败
    logger.error(f"在尝试 {MAX_RETRIES} 次后仍无法获取医生信息: {doctor_url}")
    return None

def search_doctors_by_hospital(driver, hospital_name):
    """根据医院名称搜索医生 - 根据 search_成都市新都区中医医院.html 调整选择器"""
    doctors_data = []
    search_url = f"https://www.chunyuyisheng.com/pc/search/?query={hospital_name}"
    current_page = 1
    
    while True: # 循环处理分页
        page_url = f"{search_url}&page={current_page}" if current_page > 1 else search_url
        page_retries = 0
        
        while page_retries < MAX_RETRIES:
            try:
                # 添加随机延迟，模拟人类浏览行为
                delay = random.uniform(MIN_PAGE_DELAY, MAX_PAGE_DELAY)
                logger.info(f"访问搜索页面前等待 {delay:.2f} 秒...")
                time.sleep(delay)
                
                logger.info(f"正在访问搜索页面: {page_url} (医院: {hospital_name})")
                driver.get(page_url)
                
                # 检查是否遇到了429错误
                if "429" in driver.title or "Too Many Requests" in driver.page_source:
                    logger.warning(f"搜索页面遇到 429 Too Many Requests 错误，重试 {page_retries+1}/{MAX_RETRIES}")
                    page_retries += 1
                    if page_retries < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)  # 等待更长时间
                        continue
                    else:
                        logger.error(f"多次请求被拒绝，放弃当前医院: {hospital_name}")
                        return doctors_data  # 返回已有数据
                
                # 等待搜索结果区域加载 (医生列表或无结果提示)
                try:
                    WebDriverWait(driver, 15).until(
                       EC.presence_of_element_located((By.CSS_SELECTOR, ".doctor-list, .no-result, .result-title")) # .result-title 也可能表示有结果
                    )
                except TimeoutException:
                    logger.warning(f"搜索页面加载超时: {hospital_name} (Page {current_page})，重试 {page_retries+1}/{MAX_RETRIES}")
                    page_retries += 1
                    if page_retries < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        logger.error(f"多次加载超时，跳过当前页: {current_page}")
                        break  # 超时多次，放弃当前页

                # 检查是否有搜索结果
                try:
                    # ".no-result" 元素现在可能不存在，检查列表元素数量
                    doctor_elements = driver.find_elements(By.CSS_SELECTOR, ".doctor-list .doctor-info-item")
                    if not doctor_elements:
                       logger.info(f"医院 '{hospital_name}' 在第 {current_page} 页没有找到医生列表，搜索结束。")
                       return doctors_data  # 没有医生项，结束整个搜索
                except NoSuchElementException:
                     logger.info(f"医院 '{hospital_name}' 在第 {current_page} 页没有找到医生列表容器，搜索结束。")
                     return doctors_data  # 连列表容器都没有，结束整个搜索
                    
                logger.info(f"在第 {current_page} 页找到 {len(doctor_elements)} 名医生")
                
                # 修改后的处理逻辑：
                # 首先收集当前页面上的所有医生信息，不立即访问详情页
                current_page_doctors = []
                
                # 处理当前页的每个医生
                for doctor_index, doctor_elem in enumerate(doctor_elements, 1):
                    doctor_name = "未知" # 先设置默认值
                    try:
                        # 提取医生姓名
                        try:
                           name_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".detail .name-wrap .name")
                           doctor_name = name_elem.text.strip()
                        except NoSuchElementException:
                            logger.warning(f"在第 {doctor_index}/{len(doctor_elements)} 个医生条目中未找到姓名，跳过")
                            continue # 没有名字，跳过此条目
                        
                        # 提取医生主页URL
                        doctor_url = ""
                        try:
                            # 尝试从头像链接获取
                            doctor_url_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".avatar-wrap a")
                            doctor_url = doctor_url_elem.get_attribute("href")
                            if not doctor_url: # 如果头像链接没有href, 尝试从名字链接获取
                                 name_link_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".detail .name-wrap")
                                 doctor_url = name_link_elem.get_attribute("href")

                        except NoSuchElementException:
                            logger.warning(f"无法找到医生 {doctor_name} (第 {doctor_index}/{len(doctor_elements)}) 的主页链接，跳过")
                            continue # 没有URL，无法获取详情

                        # 提取科室 (搜索结果页的)
                        try:
                            department = doctor_elem.find_element(By.CSS_SELECTOR, ".detail .name-wrap .clinic").text.strip()
                        except NoSuchElementException:
                            department = ""
                            
                        # 提取擅长描述 (搜索结果页的)
                        expertise_summary = ""
                        try:
                            # 擅长信息在最后一个 <p class="des"> 标签中
                            des_elements = doctor_elem.find_elements(By.CSS_SELECTOR, ".detail p.des")
                            if des_elements:
                                expertise_text = des_elements[-1].text.strip()
                                if expertise_text.startswith("擅长："):
                                    expertise_summary = expertise_text.replace("擅长：", "").strip()
                                else:
                                    expertise_summary = expertise_text # 如果不以"擅长："开头，也记录下来
                        except NoSuchElementException:
                             expertise_summary = ""
                             logger.debug(f"医生 {doctor_name} 在搜索结果页未找到擅长描述")
                        except Exception as e:
                            logger.error(f"提取医生 {doctor_name} 擅长描述时出错: {e}")
                            expertise_summary = ""

                        # 收集当前医生的基本信息，保存到临时列表
                        logger.info(f"收集到医生基本信息: {doctor_name} - {department} (第 {doctor_index}/{len(doctor_elements)})")
                        current_page_doctors.append({
                            "name": doctor_name,
                            "url": doctor_url,
                            "department": department,
                            "expertise": expertise_summary
                        })
                        
                    except Exception as e:
                        logger.error(f"处理搜索结果中的医生条目时出错 (第 {doctor_index}/{len(doctor_elements)}): {str(e)}")
                        logger.error(traceback.format_exc())
                        continue # 处理单个医生出错，继续下一个
                
                # 完成当前页所有医生信息收集后，再逐个访问医生详情页
                logger.info(f"已收集 {len(current_page_doctors)} 条医生基本信息，开始逐个获取详细信息...")
                
                for doctor_index, doctor_info in enumerate(current_page_doctors, 1):
                    try:
                        logger.info(f"正在获取医生详细信息: {doctor_info['name']} (第 {doctor_index}/{len(current_page_doctors)})")
                        doctor_data = get_doctor_info(
                            driver, 
                            doctor_info['url'], 
                            doctor_info['department'], 
                            doctor_info['expertise']
                        )
                        
                        if doctor_data:
                            doctors_data.append(doctor_data)
                            logger.info(f"成功获取医生 {doctor_info['name']} 的详细信息")
                        else:
                            logger.warning(f"未能获取医生 {doctor_info['name']} 的详细信息")
                        
                        # 每处理完一个医生之后的延迟被移动到get_doctor_info函数内部
                    except Exception as e:
                        logger.error(f"获取医生 {doctor_info.get('name', '未知')} 详细信息时发生错误: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue # 继续处理下一个医生
                        
                # 成功处理完当前页面，检查是否有下一页
                try:
                    pagination_links = driver.find_elements(By.CSS_SELECTOR, ".pagination a")
                    next_page_exists = False
                    for link in pagination_links:
                        try:
                            page_num = int(link.text)
                            if page_num == current_page + 1:
                               next_page_exists = True
                               break
                        except (ValueError, NoSuchElementException):
                            # 如果链接文本不是数字，或者找不到元素，忽略
                            continue 

                    if next_page_exists:
                        logger.info(f"找到第 {current_page + 1} 页，即将访问...")
                        current_page += 1
                        break  # 退出重试循环，处理下一页
                    else:
                        logger.info(f"没有找到第 {current_page + 1} 页的链接，医院 '{hospital_name}' 搜索结束。")
                        return doctors_data  # 没有下一页了，结束整个搜索
                except NoSuchElementException:
                    logger.info(f"未找到分页元素，医院 '{hospital_name}' 搜索结束。")
                    return doctors_data  # 没有分页，结束整个搜索
                except Exception as e:
                     logger.error(f"处理分页时出错: {e}")
                     return doctors_data  # 分页出错，结束整个搜索

            except WebDriverException as e:
                if "429" in str(e):
                    logger.warning(f"遇到 429 Too Many Requests 错误，重试 {page_retries+1}/{MAX_RETRIES}")
                    page_retries += 1
                    if page_retries < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                    else:
                        logger.error(f"多次请求被拒绝，放弃当前页: {current_page}")
                        break  # 退出重试循环，尝试下一页或结束
                else:
                    logger.error(f"搜索页面遇到WebDriver错误: {str(e)}")
                    logger.error(traceback.format_exc())
                    return doctors_data  # 浏览器错误，结束整个搜索

            except Exception as e:
                logger.error(f"搜索医院 '{hospital_name}' 第 {current_page} 页时发生意外错误: {str(e)}")
                logger.error(traceback.format_exc())
                page_retries += 1
                if page_retries < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    break  # 退出重试循环，尝试下一页或结束

    return doctors_data

def save_data(hospital_name, doctors_data):
    """保存医生数据到JSON文件"""
    if not doctors_data:
        logger.warning(f"医院 '{hospital_name}' 没有抓取到有效数据，不保存文件。")
        return
        
    # 清理文件名，移除或替换不适合做文件名的字符
    safe_hospital_name = "".join(c for c in hospital_name if c.isalnum() or c in (' ', '_')).rstrip()
    safe_hospital_name = safe_hospital_name.replace(' ', '_') # 可选：替换空格为下划线
    if not safe_hospital_name: # 如果处理后名字为空，给个默认名
        safe_hospital_name = "unknown_hospital"

    filename = os.path.join(DATA_DIR, f"{safe_hospital_name}.json")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(doctors_data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已保存到 {filename}，共 {len(doctors_data)} 条记录")
    except IOError as e:
        logger.error(f"保存文件时出错 {filename}: {e}")
    except Exception as e:
        logger.error(f"保存数据时发生意外错误 {filename}: {e}")


def main():
    """主函数，协调整个抓取过程"""
    logger.info("开始抓取春雨医生网站数据 (已更新选择器)")
    driver = None # 初始化 driver
    try:
        driver = setup_driver()
        
        total_doctors = 0
        processed_hospitals = 0

        for hospital in HOSPITALS:
            logger.info(f"===== 开始处理医院: {hospital} =====")
            doctors_data = search_doctors_by_hospital(driver, hospital)
            save_data(hospital, doctors_data)
            if doctors_data:
                 total_doctors += len(doctors_data)
            processed_hospitals += 1
            logger.info(f"===== 医院 '{hospital}' 处理完成 =====")
            # 处理完一家医院后暂停时间长一点
            time.sleep(3) 
        
        logger.info(f"所有医院处理完毕。共处理 {processed_hospitals} 家医院，抓取到 {total_doctors} 条医生数据。")

    except Exception as e:
        logger.error(f"抓取过程中发生严重错误: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()
            logger.info("抓取过程结束，浏览器已关闭")
        else:
            logger.info("未能成功启动浏览器")


if __name__ == "__main__":
    main()
