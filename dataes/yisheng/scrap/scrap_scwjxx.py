import os
import json
import time
import random
import logging
import traceback
import re
import pickle
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scwjxx_scraping.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置保存路径
BASE_DIR = "D:\\代码\\ESRI\\ture_small\\dataes\\yisheng"
DATA_DIR = os.path.join(BASE_DIR, "data_scwjxx")
os.makedirs(DATA_DIR, exist_ok=True)

# 抓取配置
MIN_PAGE_DELAY = 2  # 页面之间的最小延迟（秒）
MAX_PAGE_DELAY = 5  # 页面之间的最大延迟（秒）
MIN_DOCTOR_DELAY = 1  # 医生详情页之间的最小延迟（秒）
MAX_DOCTOR_DELAY = 3  # 医生详情页之间的最大延迟（秒）
MAX_RETRIES = 3      # 最大重试次数
RETRY_DELAY = 30     # 遇到错误时的等待时间（秒）

# 固定URL - 解码后是 "复诊开方" 相关医生列表
BASE_URL = "https://jksc.scwjxx.cn/general-hospital/doctor-list"
QUERY_PARAMS = {
    "title": "复诊开方",
    "jksc_auth": "1",
    "timestamp": "1744802160"  # 这个时间戳可能需要根据实际情况更新
}

# 微信 cookie 和认证配置
COOKIES_FILE = os.path.join(BASE_DIR, "wechat_cookies.pkl")
NEED_WECHAT_AUTH = True  # 是否需要微信授权

def setup_driver():
    """设置并返回一个模拟微信环境的WebDriver"""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 视情况可以启用无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=414,896")  # 模拟手机尺寸
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # 设置手机模式
    mobile_emulation = {
        "deviceMetrics": { "width": 414, "height": 896, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.20(0x18001433) NetType/WIFI Language/zh_CN"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    # 禁用自动化控制特征
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    
    # 执行一些JavaScript来隐藏WebDriver的自动化特征
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # 添加微信浏览器特有的JS对象
    wechat_js = """
    // 模拟 WeixinJSBridge 对象
    Object.defineProperty(window, 'WeixinJSBridge', {
        get: function() {
            return {
                invoke: function() {},
                call: function() {},
                on: function() {},
                publish: function() {}
            };
        }
    });
    
    // 模拟 __wxjs_environment 变量
    Object.defineProperty(window, '__wxjs_environment', {
        get: function() { return 'miniprogram'; }
    });
    
    // 模拟微信内部检测函数
    window.wx = {
        config: function() {},
        ready: function() {},
        miniProgram: {
            navigateTo: function() {},
            getEnv: function(callback) { callback({miniprogram: true}); }
        }
    };
    """
    
    try:
        driver.execute_script(wechat_js)
    except Exception as e:
        logger.warning(f"注入微信特征脚本失败: {e}")
    
    return driver

def construct_url(params=None):
    """构造完整的URL，根据需要可以添加或更新查询参数"""
    # 创建查询参数副本，以便修改它
    query_params = QUERY_PARAMS.copy()
    
    # 如果提供了自定义参数，更新或添加到查询参数
    if params:
        query_params.update(params)
        
    # 更新时间戳参数为当前时间
    query_params["timestamp"] = str(int(time.time()))
    
    # 使用urlencode正确编码参数
    query_string = urlencode(query_params)
    
    # 返回完整URL
    return f"{BASE_URL}?{query_string}"

def extract_doctor_list(driver):
    """从页面提取医生列表信息，支持滚动加载更多"""
    doctors_data = []
    
    try:
        # 等待医生列表加载
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".doctor-list, .doctor-item, .list-item, .doctor-card"))
        )
        
        # 初始化循环变量
        last_doctors_count = 0
        no_new_doctors_count = 0
        max_scroll_attempts = 20  # 最大滚动尝试次数
        scroll_count = 0
        
        # 根据页面截图和提供的样例，调整选择器以匹配真实页面结构
        doctor_selector = ".doctor-card, .list-item, .doctor"  # 尝试多个可能的选择器
        
        while scroll_count < max_scroll_attempts:
            # 获取当前页面上的所有医生元素
            doctor_elements = driver.find_elements(By.CSS_SELECTOR, doctor_selector)
            current_doctors_count = len(doctor_elements)
            
            logger.info(f"当前页面找到 {current_doctors_count} 位医生")
            
            # 如果没有新增医生，计数器加1
            if current_doctors_count == last_doctors_count:
                no_new_doctors_count += 1
                # 如果连续3次没有新医生，认为已到达底部
                if no_new_doctors_count >= 3:
                    logger.info("连续多次滚动未发现新医生，可能已到达列表底部")
                    break
            else:
                # 有新医生出现，重置计数器
                no_new_doctors_count = 0
                
            # 从上次处理的位置开始，处理新加载的医生
            for i in range(last_doctors_count, current_doctors_count):
                try:
                    doctor_elem = doctor_elements[i]
                    doctor_data = {}
                    
                    # 提取医生姓名
                    try:
                        # 根据页面截图调整选择器
                        name_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".name, .doctor-name")
                        doctor_data["name"] = name_elem.text.strip()
                    except NoSuchElementException:
                        logger.warning(f"未找到第 {i+1} 个医生的姓名")
                        doctor_data["name"] = "未知"
                    
                    # 提取医院名称 (从页面截图看是在三级甲等标签下方)
                    try:
                        hospital_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".hospital, .hospital-name")
                        doctor_data["hospital_name"] = hospital_elem.text.strip()
                    except NoSuchElementException:
                        # 尝试其他可能的选择器
                        try:
                            hospital_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".hospital-level + *")
                            doctor_data["hospital_name"] = hospital_elem.text.strip()
                        except:
                            logger.warning(f"未找到第 {i+1} 个医生的医院")
                            doctor_data["hospital_name"] = "未知"
                    
                    # 提取科室
                    try:
                        # 页面截图中科室和职称是连在一起的，例如"主治医师 | 产科门诊"
                        dept_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".department, .dept, .clinic")
                        dept_text = dept_elem.text.strip()
                        # 处理可能的格式如"主治医师 | 产科门诊"
                        if "|" in dept_text:
                            parts = dept_text.split("|")
                            if len(parts) > 1:
                                doctor_data["department"] = parts[1].strip()
                            else:
                                doctor_data["department"] = dept_text
                        else:
                            doctor_data["department"] = dept_text
                    except NoSuchElementException:
                        logger.warning(f"未找到第 {i+1} 个医生的科室")
                        doctor_data["department"] = "未知"
                    
                    # 提取职称
                    try:
                        title_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".title, .doctor-title")
                        doctor_data["title"] = title_elem.text.strip()
                    except NoSuchElementException:
                        # 尝试从科室文本中提取职称
                        if "|" in dept_text:
                            parts = dept_text.split("|")
                            doctor_data["title"] = parts[0].strip()
                        else:
                            doctor_data["title"] = "未知"
                    
                    # 提取擅长领域 (根据页面截图，擅长以"擅长："开头)
                    try:
                        expertise_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".expertise, .goodat, .skill, .description")
                        expertise_text = expertise_elem.text.strip()
                        # 处理可能的格式如"擅长：xxx"
                        if "擅长：" in expertise_text:
                            doctor_data["expertise"] = expertise_text.replace("擅长：", "").strip()
                        else:
                            doctor_data["expertise"] = expertise_text
                    except NoSuchElementException:
                        doctor_data["expertise"] = "未提供"
                    
                    # 提取接诊率和接诊量信息 (仅用于日志记录，不存入数据库)
                    try:
                        rate_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".rate, .percentage")
                        reception_rate = rate_elem.text.strip()
                        logger.info(f"医生 {doctor_data['name']} 的接诊率: {reception_rate}")
                    except NoSuchElementException:
                        pass
                        
                    try:
                        count_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".count, .reception-count")
                        reception_count = count_elem.text.strip()
                        logger.info(f"医生 {doctor_data['name']} 的接诊量: {reception_count}")
                    except NoSuchElementException:
                        pass
                    
                    # 添加其他标准字段 (根据数据库结构)
                    doctor_data["focused_diseases"] = ""  # 擅长疾病，默认为空
                    doctor_data["introduction"] = "未提供"  # 个人简介
                    doctor_data["education"] = "未提供"  # 教育背景
                    
                    # 尝试获取详情页链接
                    try:
                        # 医生卡片整体通常是一个链接
                        link_elem = doctor_elem.find_element(By.TAG_NAME, "a")
                        doctor_data["detail_url"] = link_elem.get_attribute("href")
                    except NoSuchElementException:
                        # 也可能是点击卡片某个按钮进入详情
                        try:
                            link_elem = doctor_elem.find_element(By.CSS_SELECTOR, ".detail-btn, .enter-detail")
                            doctor_data["detail_url"] = link_elem.get_attribute("href")
                        except:
                            doctor_data["detail_url"] = ""
                    
                    # 记录成功提取的医生信息
                    if doctor_data["name"] != "未知":
                        doctors_data.append(doctor_data)
                        logger.info(f"成功提取医生信息: {doctor_data['name']} - {doctor_data.get('hospital_name', '未知医院')}")
                    else:
                        logger.warning(f"第 {i+1} 个医生信息不完整，跳过")
                    
                except Exception as e:
                    logger.error(f"提取第 {i+1} 个医生信息时出错: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 更新处理过的医生数量
            last_doctors_count = current_doctors_count
            
            # 执行滚动操作，加载更多医生
            logger.info(f"执行第 {scroll_count+1} 次滚动，尝试加载更多医生...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 等待新内容加载
            time.sleep(random.uniform(1.5, 3))
            scroll_count += 1
        
        logger.info(f"共提取到 {len(doctors_data)} 位医生信息")
        return doctors_data
        
    except TimeoutException:
        logger.error("等待医生列表加载超时")
        return []
    except Exception as e:
        logger.error(f"提取医生列表时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def scrape_doctor_detail(driver, doctor):
    """访问医生详情页获取更多信息 (如果有详情页链接)"""
    # 如果没有详情页链接，则直接返回现有信息
    if not doctor.get("detail_url"):
        return doctor
    
    detail_url = doctor["detail_url"]
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            # 随机延迟
            delay = random.uniform(MIN_DOCTOR_DELAY, MAX_DOCTOR_DELAY)
            logger.info(f"访问医生详情页前等待 {delay:.2f} 秒...")
            time.sleep(delay)
            
            logger.info(f"访问医生详情页: {detail_url}")
            driver.get(detail_url)
            
            # 等待详情页加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".doctor-info, .doctor-detail, .doctor-card"))
            )
            
            # 提取更详细的简介信息 - 根据页面截图调整选择器
            try:
                # 根据示例，擅长信息可能在"擅长："开头的段落中
                intro_elems = driver.find_elements(By.CSS_SELECTOR, ".doctor-info p, .description, .skill-description")
                for elem in intro_elems:
                    text = elem.text.strip()
                    if text.startswith("擅长："):
                        doctor["expertise"] = text.replace("擅长：", "").strip()
                    elif "简介" in text or "介绍" in text:
                        doctor["introduction"] = text
                    elif "教育" in text or "学历" in text or "背景" in text:
                        doctor["education"] = text
                
                # 尝试查找可能的疾病列表 (作为focused_diseases)
                disease_elems = driver.find_elements(By.CSS_SELECTOR, ".disease-tag, .disease-item, .tag")
                if disease_elems:
                    diseases = [elem.text.strip() for elem in disease_elems]
                    doctor["focused_diseases"] = ", ".join(diseases)
            except Exception as e:
                logger.warning(f"提取医生详情页信息时出错: {str(e)}")
                    
            logger.info(f"成功获取医生 {doctor['name']} 的详细信息")
            return doctor
            
        except TimeoutException:
            logger.warning(f"医生详情页 {detail_url} 加载超时，重试 {retries+1}/{MAX_RETRIES}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"多次加载超时，放弃获取详情: {detail_url}")
                return doctor  # 返回原始信息
                
        except Exception as e:
            logger.error(f"访问医生详情页时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return doctor  # 出错时返回原始信息

def save_data(doctors_data):
    """保存医生数据到JSON文件"""
    if not doctors_data:
        logger.warning("没有数据可保存")
        return
        
    # 使用当前时间作为文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(DATA_DIR, f"doctors_{timestamp}.json")
    
    try:
        # 确保数据格式符合数据库结构
        clean_data = []
        for doctor in doctors_data:
            clean_doctor = {
                "name": doctor.get("name", "未知"),
                "hospital_name": doctor.get("hospital_name", "未知"),
                "department": doctor.get("department", ""),
                "focused_diseases": doctor.get("focused_diseases", ""),
                "expertise": doctor.get("expertise", ""),
                "introduction": doctor.get("introduction", ""),
                "education": doctor.get("education", "")
            }
            clean_data.append(clean_doctor)
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已保存到 {filename}，共 {len(clean_data)} 条记录")
    except Exception as e:
        logger.error(f"保存数据时出错: {str(e)}")
        logger.error(traceback.format_exc())

def take_screenshot(driver, name="screenshot"):
    """截图，用于调试目的"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(DATA_DIR, f"{name}_{timestamp}.png")
        driver.save_screenshot(filename)
        logger.info(f"截图已保存到 {filename}")
    except Exception as e:
        logger.error(f"截图失败: {str(e)}")

def save_cookies(driver, file_path):
    """保存当前浏览器 cookie 到文件"""
    try:
        cookies = driver.get_cookies()
        with open(file_path, 'wb') as f:
            pickle.dump(cookies, f)
        logger.info(f"Cookie 已保存到 {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存 cookie 时出错: {str(e)}")
        return False

def load_cookies(driver, file_path):
    """从文件加载 cookie 到浏览器"""
    if not os.path.exists(file_path):
        logger.warning(f"Cookie 文件不存在: {file_path}")
        return False
        
    try:
        with open(file_path, 'rb') as f:
            cookies = pickle.load(f)
        
        # 获取当前域名
        current_url = driver.current_url
        domain = urlparse(current_url).netloc
        
        # 添加 cookie
        for cookie in cookies:
            # 处理无法添加的 cookie
            if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                cookie['expiry'] = int(cookie['expiry'])
            
            try:
                # 只添加当前域名的 cookie
                if domain in cookie['domain'] or not cookie.get('domain'):
                    driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"添加 cookie 失败: {str(e)}")
                
        logger.info(f"成功从 {file_path} 加载 cookie")
        return True
    except Exception as e:
        logger.error(f"加载 cookie 时出错: {str(e)}")
        return False

def check_auth_required(driver):
    """检查页面是否需要微信授权"""
    try:
        # 检查是否有微信授权提示
        auth_elements = driver.find_elements(By.XPATH, 
            "//*[contains(text(), '请在微信客户端打开链接') or contains(text(), '请用微信扫码') or contains(text(), '微信登录')]")
        
        if auth_elements:
            logger.warning("检测到页面需要微信授权")
            return True
            
        # 检查页面是否为空或错误页面
        if "请在微信客户端中打开链接" in driver.page_source:
            logger.warning("检测到请在微信客户端中打开链接提示")
            return True
            
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
        if not body_text or "error" in body_text.lower() or "unauthorized" in body_text.lower():
            logger.warning("检测到页面内容为空或存在错误")
            return True
            
        # 尝试检查医生元素是否存在
        doctor_elements = driver.find_elements(By.CSS_SELECTOR, ".doctor-card, .list-item, .doctor")
        if not doctor_elements:
            # 再次检查页面是否有医生相关内容
            if not re.search(r'医生|医院|科室|医师', driver.page_source):
                logger.warning("页面上没有找到医生相关内容")
                return True
                
        return False
    except Exception as e:
        logger.error(f"检查授权状态时出错: {str(e)}")
        return True  # 出错时假设需要授权

def get_wechat_auth(driver, url):
    """获取微信授权 - 此函数需要用户手动操作"""
    try:
        logger.info("需要获取微信授权，请按照以下步骤操作：")
        logger.info("1. 请使用手机微信扫描即将显示的二维码")
        logger.info("2. 在微信中访问相关页面并授权")
        logger.info("3. 授权完成后，脚本将保存 Cookie 以便后续使用")
        
        # 访问URL，可能会显示二维码或授权提示
        driver.get(url)
        
        # 等待用户手动扫码并授权
        input("请完成微信扫码授权，然后按回车键继续...")
        
        # 检查是否授权成功
        if check_auth_required(driver):
            logger.error("授权失败，仍然需要微信授权")
            return False
            
        # 保存授权后的 cookie
        save_cookies(driver, COOKIES_FILE)
        
        return True
    except Exception as e:
        logger.error(f"获取微信授权时出错: {str(e)}")
        return False

def update_timestamp_in_url(url):
    """更新URL中的时间戳参数为当前时间"""
    try:
        # 解析URL
        parsed_url = urlparse(url)
        
        # 解析查询参数
        query_params = parse_qs(parsed_url.query)
        
        # 更新时间戳为当前时间
        query_params['timestamp'] = [str(int(time.time()))]
        
        # 将解析后的查询参数转换为查询字符串
        # 注意parse_qs返回的值是列表，需要取第一个元素
        new_query = urlencode({k: v[0] if isinstance(v, list) and len(v) > 0 else v 
                              for k, v in query_params.items()}, doseq=False)
        
        # 重建URL
        new_components = list(parsed_url)
        new_components[4] = new_query  # 4是query在urlparse结果中的索引
        
        # 使用urlunparse重建URL
        return urlunparse(new_components)
    except Exception as e:
        logger.error(f"更新URL时间戳时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return url  # 出错时返回原始URL

def main():
    """主函数，协调整个抓取过程"""
    logger.info("开始抓取健康四川网站的医生数据")
    driver = None
    
    try:
        # 设置WebDriver
        driver = setup_driver()
        
        # 构造要访问的URL
        url = construct_url()
        logger.info(f"访问URL: {url}")
        
        # 首先访问网站域名首页，以便后续设置cookie
        domain_url = urlparse(url).scheme + "://" + urlparse(url).netloc
        logger.info(f"首先访问域名首页: {domain_url}")
        driver.get(domain_url)
        
        # 尝试加载已保存的cookie
        cookie_loaded = False
        if os.path.exists(COOKIES_FILE):
            logger.info("尝试加载已保存的cookie")
            cookie_loaded = load_cookies(driver, COOKIES_FILE)
        
        # 访问目标URL
        logger.info("正在访问目标页面...")
        driver.get(url)
        time.sleep(3)  # 等待页面加载
        
        # 检查是否需要微信授权
        if check_auth_required(driver):
            logger.warning("检测到页面需要微信授权")
            
            if NEED_WECHAT_AUTH:
                # 如果之前加载了cookie但仍需授权，可能cookie已过期
                if cookie_loaded:
                    logger.warning("已加载cookie但仍需授权，可能cookie已过期")
                
                # 引导用户进行微信授权
                logger.info("开始微信授权流程...")
                auth_success = get_wechat_auth(driver, url)
                
                if not auth_success:
                    logger.error("微信授权失败，无法继续抓取")
                    take_screenshot(driver, "auth_failed")
                    return
                    
                # 授权成功后重新加载页面
                logger.info("授权成功，重新加载目标页面")
                driver.get(url)
                time.sleep(3)  # 等待页面加载
            else:
                logger.error("页面需要微信授权，但NEED_WECHAT_AUTH设置为False")
                take_screenshot(driver, "auth_required")
                return
        
        # 页面加载完成后截图（用于调试）
        take_screenshot(driver, "initial_page")
        
        # 提取医生列表
        doctors_data = extract_doctor_list(driver)
        
        if doctors_data:
            logger.info(f"提取到 {len(doctors_data)} 位医生的基本信息")
            
            # 获取医生详情（如果有详情页链接）
            detailed_doctors_data = []
            for i, doctor in enumerate(doctors_data):
                logger.info(f"处理第 {i+1}/{len(doctors_data)} 位医生的详细信息")
                detailed_doctor = scrape_doctor_detail(driver, doctor)
                detailed_doctors_data.append(detailed_doctor)
            
            # 保存数据
            save_data(detailed_doctors_data)
        else:
            logger.warning("未提取到任何医生信息")
            # 保存页面源代码以便分析
            with open(os.path.join(DATA_DIR, "empty_page.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info("已保存空页面源代码到 empty_page.html")
        
    except Exception as e:
        logger.error(f"抓取过程中发生严重错误: {str(e)}")
        logger.error(traceback.format_exc())
        if driver:
            take_screenshot(driver, "error_page")
    finally:
        if driver:
            driver.quit()
            logger.info("抓取过程结束，浏览器已关闭")
        else:
            logger.info("未能成功启动浏览器")

if __name__ == "__main__":
    main() 