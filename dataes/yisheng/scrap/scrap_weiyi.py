'''
需求：
1进入网址https://www.wedoctor.com/search/expert?q=[医院名称]，[]指代的是医院名称
需要循环进入网站提取数据
以下是参数内容：
成都市新都区中医医院
成都市新都区第二人民医院
成都市新都区妇幼保健院
成都市新都区人民医院
成都市新都区新都街道龙虎社区卫生服务中心
成都市新都区新繁街道社区卫生服务中心
成都市新都区石板滩街道木兰社区卫生服务中心
成都市新都区桂湖街道城东社区卫生服务中心
成都市新都区清流镇卫生院
成都市新都区石板滩街道社区卫生服务中心
成都市新都区第三人民医院
成都市新都区新繁街道龙桥社区卫生服务中心
成都市新都区三河街道社区卫生服务中心
成都市新都区军屯镇中心卫生院
成都市新都区斑竹园街道社区卫生服务中心
成都市新都区桂湖街道城西社区卫生服务中心
成都市新都区新都街道蜀都社区卫生服务中心
成都市新都区大丰街道太平社区卫生服务中心
成都市新都区大丰街道丰安社区卫生服务中心


2.提取<a class="cover-bg seo-anchor-text" href="https://www.wedoctor.com/expert/a74ae927-de95-48f3-b979-eb5dd929568e000?hospDeptId=6175adaa-a60a-4b01-8855-4918c26006b3000&amp;hospitalId=0f755e70-5114-4223-a0b3-11aafb90804a000" target="_blank" monitor="search_resultlist,doctor,doctor" monitor-doctor-id="a74ae927-de95-48f3-b979-eb5dd929568e000">徐洪</a>
然后获取链接href以及医生名称

3.进入链接后，提取医生信息
医生从业地址 
医生专业
医生治疗内容
医生擅长内容
医生简介

4.翻页
网站默认点击按钮进行翻页
翻页按钮为
若查询不到医生信息则跳过返回null
5.提取数据
提出的数据存储于D:\代码\ESRI\ture_small\data\yisheng\data
'''

import os
import time
import json
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 存储路径
SAVE_PATH = "D:\\代码\\ESRI\\ture_small\\dataes\\yisheng\\data"

# 确保存储目录存在
os.makedirs(SAVE_PATH, exist_ok=True)

# 医院列表
hospitals = [
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
    "成都市新都区大丰街道丰安社区卫生服务中心",
]

def setup_webdriver():
    """设置并返回WebDriver"""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 无头模式，取消注释可不显示浏览器
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    
    # 添加以下选项来减少警告信息
    chrome_options.add_argument("--log-level=3")  # 仅显示致命错误
    chrome_options.add_argument("--enable-unsafe-swiftshader")  # 解决WebGL警告
    chrome_options.add_argument("--disable-webgl")  # 禁用WebGL
    chrome_options.add_argument("--disable-webrtc")  # 禁用WebRTC，解决stun服务器连接问题
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 禁止控制台输出日志
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def get_doctor_info(driver, doctor_url, doctor_name, hospital_name):
    """访问医生页面并提取医生信息"""
    original_window = driver.current_window_handle # 记录原始窗口
    debug_save_path = os.path.join(SAVE_PATH, "debug_html") # 调试HTML保存路径
    os.makedirs(debug_save_path, exist_ok=True)
    
    try:
        # 尝试在新标签页中打开医生链接
        print(f"尝试在新标签页打开医生URL: {doctor_url}")
        driver.execute_script("window.open(arguments[0]);", doctor_url)
        time.sleep(1) # 给浏览器一点时间响应打开新窗口
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1]) # 切换到新标签页
            print("已切换到新标签页，等待页面加载...")
        else:
            print("错误：未能打开新标签页")
            return None
        
        # 等待时间设置为15秒
        wait = WebDriverWait(driver, 15)
        detail_container = None # 初始化详情容器
        
        # --- 策略: 先等容器出现，再等内部关键元素可见 --- 
        print(f"等待医生 {doctor_name} 详情页核心容器出现在DOM中 (.detail.word-break)... ")
        try:
            detail_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".detail.word-break"))
            )
            print(f"核心容器已出现，继续等待内部医院信息可见 (.hospital b)... ")
            # 在容器内等待医院名称可见
            wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".detail.word-break .hospital p:first-of-type b:nth-of-type(1)"))
            )
            print(f"医生 {doctor_name} 详情页核心信息容器及内部医院信息已加载并可见")
        except TimeoutException:
             print(f"主要策略失败: 医生 {doctor_name} 页面核心信息容器或其内部医院信息加载超时/不可见 (将在15秒后跳过)") # 更新日志
             # 保存HTML用于调试
             debug_filename = os.path.join(debug_save_path, f"debug_timeout_detail_{doctor_name}.html")
             try:
                 with open(debug_filename, "w", encoding="utf-8") as f:
                     f.write(driver.page_source)
                 print(f"已将页面源码保存至: {debug_filename}")
             except Exception as save_err:
                 print(f"保存调试HTML失败: {save_err}")
             driver.close()
             driver.switch_to.window(original_window)
             return None
        
        # --- 如果核心容器已找到，开始提取信息 --- 
        workplace, specialty, treatment, expertise, introduction = "", "", "", "", ""
        print(f"开始从核心容器提取医生 {doctor_name} 的详细信息...")
        
        # 提取医院和专业 (在 .hospital div 内)
        try:
            hospital_div = detail_container.find_element(By.CSS_SELECTOR, ".hospital")
            # 查找第一个p标签下的第一个b标签作为医院
            workplace_element = hospital_div.find_element(By.CSS_SELECTOR, "p:first-of-type b:nth-of-type(1)")
            workplace = workplace_element.text.strip()
            print(f"  - 医院: {workplace}")
            # 查找第一个p标签下的第二个b标签作为专业
            specialty_element = hospital_div.find_element(By.CSS_SELECTOR, "p:first-of-type b:nth-of-type(2)")
            specialty = specialty_element.text.strip()
            print(f"  - 专业: {specialty}")
        except NoSuchElementException:
            print(f"未能从 .hospital 提取医院或专业信息")
            # 可以尝试备用查找，比如直接在detail_container下查找b标签，但不推荐，容易出错

        # 提取擅长 (在 .goodat div 内的 span)
        try:
            goodat_div = detail_container.find_element(By.CSS_SELECTOR, ".goodat")
            expertise_span = goodat_div.find_element(By.TAG_NAME, "span") # 直接找span标签
            expertise = expertise_span.text.strip()
            # 有时候擅长内容可能在隐藏的input里，如果span为空可以尝试提取input
            if not expertise:
                 try:
                     expertise_input = goodat_div.find_element(By.TAG_NAME, "input")
                     expertise = expertise_input.get_attribute("value").strip()
                 except NoSuchElementException:
                     pass # input也没有就算了
            print(f"  - 擅长: {'已找到' if expertise else '未找到内容'}")
        except NoSuchElementException:
            expertise = ""
            print(f"未能定位到医生 {doctor_name} 的擅长信息区域 (.goodat)")
        
        # 提取简介 (在 .about div 内的 span)
        try:
            about_div = detail_container.find_element(By.CSS_SELECTOR, ".about")
            introduction_span = about_div.find_element(By.TAG_NAME, "span") # 直接找span标签
            introduction = introduction_span.text.strip()
            # 如果简介不完整 (以...结尾)，尝试读取隐藏input的完整内容
            if introduction.endswith("..."):
                try:
                    introduction_input = about_div.find_element(By.TAG_NAME, "input")
                    full_introduction = introduction_input.get_attribute("value").strip()
                    if full_introduction:
                         introduction = full_introduction
                         print("  - 简介: 已获取完整内容")
                    else:
                         print("  - 简介: 找到省略号但未找到完整内容input")
                except NoSuchElementException:
                    print("  - 简介: 找到省略号但未找到完整内容input")
                    pass # input找不到就算了，保留省略版本
            print(f"  - 简介: {'已找到' if introduction else '未找到内容'}")
        except NoSuchElementException:
            introduction = ""
            print(f"未能定位到医生 {doctor_name} 的简介信息区域 (.about)")

        # \"治疗内容\"字段仍然缺失对应HTML结构，保持为空\n        treatment = \"\" 
        
        # 组织数据 (确保字段名与数据库表一致)
        doctor_info = {
            "name": doctor_name,
            "hospital_name": hospital_name, # 保留搜索时的医院名作为主要来源
            # "workplace": workplace,        # 移除，使用 hospital_name
            "department": specialty,       # 将 specialty 重命名为 department
            "focused_diseases": "",       # 添加占位符，数据库表有此列
            "expertise": expertise,
            "introduction": introduction,
            "education": "",              # 添加占位符，数据库表有此列
            "likes": 0,                   # 添加占位符，数据库表有此列
            # "source_url": doctor_url    # 移除，数据库表无此列
        }
        
        driver.close() # 关闭当前标签页
        driver.switch_to.window(original_window) # 切换回原始窗口
        print(f"成功获取医生 {doctor_name} 信息")
        return doctor_info
        
    except Exception as e:
        print(f"获取医生 {doctor_name} 信息时发生异常: {str(e)}")
        # 保存HTML用于调试
        debug_filename = os.path.join(debug_save_path, f"debug_exception_{doctor_name}.html")
        if driver.current_window_handle != original_window:
             try:
                 with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                 print(f"异常发生，已将页面源码保存至: {debug_filename}")
             except Exception as save_err:
                 print(f"保存调试HTML失败: {save_err}")
        # 确保即使出错也关闭新标签页并切换回去
        if len(driver.window_handles) > 1 and driver.current_window_handle != original_window:
            try:
                driver.close()
            except Exception as close_err:
                print(f"关闭出错标签页时异常: {close_err}")
            # 无论关闭是否成功，都尝试切换窗口
            try:
                driver.switch_to.window(original_window)
            except Exception as switch_err:
                 print(f"切换回主窗口时异常: {switch_err}")
        return None

def search_doctors_by_hospital(driver, hospital_name):
    """搜索医院并提取医生信息"""
    base_url = f"https://www.wedoctor.com/search/expert?q={hospital_name}"
    doctors_list = []
    wait = WebDriverWait(driver, 20) # 增加等待时间
    
    try:
        # 访问搜索页
        print(f"访问搜索URL: {base_url}")
        driver.get(base_url)
        
        # --- 增加等待，确保页面主要内容加载 --- 
        try:
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".g-doctor-items")) # 等待医生列表容器出现
            )
            print("医生列表容器已加载")
        except TimeoutException:
             # 检查是否是因为没有结果
             try:
                 # 检查精确的 "抱歉，没有找到" 文本
                 no_results_xpath = "//div[contains(text(), '抱歉，没有找到')]"
                 no_results_element = driver.find_element(By.XPATH, no_results_xpath)
                 print(f"检查结果: 找到 '抱歉，没有找到'。跳过医院 {hospital_name}")
                 return []
             except NoSuchElementException:
                 # 如果精确文本未找到，再检查是否有 "抱歉~" 或 "帮您找到"
                 try:
                     # 检查 "抱歉~" 或 "为您找到了" / "帮您找到" 这类模糊匹配提示
                     fuzzy_match_xpath = "//*[contains(text(), '抱歉~ 没有找到') or contains(text(), '为您找到了') or contains(text(), '帮您找到')]"
                     fuzzy_match_elements = driver.find_elements(By.XPATH, fuzzy_match_xpath)
                     if fuzzy_match_elements:
                         print(f"检查结果: 找到 '抱歉~' 或 '为您找到了' 提示。跳过医院 {hospital_name} (非精确匹配)")
                         return []
                     else:
                         # 如果以上提示都没有，才认为是加载超时
                         print(f"搜索页 {hospital_name} 关键元素加载超时，且未找到明确的无结果提示。")
                         return [] # 加载超时也返回空列表
                 except Exception as e_fuzzy:
                      print(f"检查模糊匹配提示时出错: {e_fuzzy}。跳过医院 {hospital_name}")
                      return []

        # --- 在这里添加新的检查 ---
        print(f"检查页面是否包含 '抱歉~ 没有找到' 或 '为您找到了' / '帮您找到' 文本...")
        try:
            # 查找提示元素 (使用 find_elements 避免 NoSuchElementException)
            skip_indicator_xpath = "//*[contains(text(), '抱歉~ ') or contains(text(), '为您找到了') or contains(text(), '帮您找到')]"
            skip_indicators = driver.find_elements(By.XPATH, skip_indicator_xpath)

            if skip_indicators:
                # 获取找到的第一个提示文本用于日志
                indicator_text = skip_indicators[0].text[:50] # 最多取前50个字符
                print(f"检查结果: 在页面加载后检测到提示 '{indicator_text}...'。跳过医院 {hospital_name} (非精确匹配或无结果)")
                return [] # 如果找到提示，直接跳过该医院
            else:
                print("检查结果: 未在页面上找到明确的跳过提示。继续处理...")

        except Exception as check_err:
            print(f"检查跳过提示时发生错误: {check_err}。为安全起见，跳过医院 {hospital_name}")
            return []
        # --- 新检查结束 ---

        # --- 尝试关闭可能的登录弹窗 --- 
        try:
            # 获取总页数
            total_pages = 1
            try:
                # 查找分页元素
                pagination_container = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".g-pagination")) # 等待分页容器
                )
                # 查找所有页码链接 (<a>标签)
                page_links = pagination_container.find_elements(By.CSS_SELECTOR, ".pagers a.J_pageNum_gh")
                if page_links: # 如果存在页码链接
                    # 最后一个页码链接通常是最大页数
                    total_pages = int(page_links[-1].text)
                else:
                    # 检查是否有 "current" 标记，如果只有一页，则没有<a>页码链接
                    current_page_span = pagination_container.find_elements(By.CSS_SELECTOR, ".pagers span.current")
                    if current_page_span:
                        total_pages = 1
                    else:
                        # 另一种可能： 动态加载的分页，初始不可见，需要进一步处理
                        print(f"医院 {hospital_name}: 未能明确解析总页数，假设为1页")
                        total_pages = 1 
            except (TimeoutException, NoSuchElementException, ValueError, IndexError) as e:
                print(f"解析医院 {hospital_name} 总页数时出错或未找到分页: {str(e)}，假设为1页")
                total_pages = 1
            
            print(f"医院 {hospital_name} 共有 {total_pages} 页医生信息")
            
            # 遍历所有页面
            current_page = 1
            while current_page <= total_pages:
                print(f"-- 开始处理 {hospital_name} 第 {current_page} 页 --")
                
                # 等待当前页的医生列表加载
                try:
                    wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".g-doctor-items li.g-doctor-item")) 
                    )
                except TimeoutException:
                    print(f"第 {current_page} 页医生列表加载超时")
                    break # 超时则停止处理后续页面
                
                # 提取当前页所有医生链接和名字
                doctor_elements = driver.find_elements(By.CSS_SELECTOR, ".g-doctor-items li.g-doctor-item a.cover-bg.seo-anchor-text")
                current_page_doctors = []
                for el in doctor_elements:
                    try:
                        name = el.text.strip()
                        url = el.get_attribute("href")
                        if name and url:
                            current_page_doctors.append({"name": name, "url": url})
                    except Exception as e:
                        print(f"提取单个医生链接时出错: {e}")
                
                print(f"第 {current_page} 页找到 {len(current_page_doctors)} 个医生链接")

                # 依次处理当前页的医生
                for doc in current_page_doctors:
                    print(f"准备获取医生: {doc['name']}, URL: {doc['url']}")
                    doctor_info = get_doctor_info(driver, doc['url'], doc['name'], hospital_name)
                    if doctor_info:
                        doctors_list.append(doctor_info)
                    # 添加短暂随机延时，避免访问过于频繁
                    time.sleep(random.uniform(0.5, 1.5))
                
                # 翻页逻辑
                current_page += 1
                if current_page <= total_pages:
                    print(f"准备翻到第 {current_page} 页")
                    try:
                        # 定位"下一页"按钮
                        next_page_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".g-pagination a.next"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button) # 滚动到按钮可视
                        time.sleep(0.5)
                        next_page_button.click()
                        print(f"已点击下一页，等待第 {current_page} 页加载...")
                        # 等待下一页的标志性元素出现 (例如，等待分页器当前页码变化，但这比较复杂，暂时用延时)
                        time.sleep(random.uniform(3, 5)) # 等待页面跳转和加载
                    except TimeoutException:
                        print(f"未能找到或点击'下一页'按钮 (目标页: {current_page})，停止翻页")
                        break
                    except Exception as e:
                        print(f"点击'下一页'时发生错误: {str(e)}，停止翻页")
                        break
                else:
                    print("已到达最后一页")
            
            print(f"医院 {hospital_name} 处理完毕，共获取 {len(doctors_list)} 条医生信息")
            return doctors_list
        
        except Exception as e:
            print(f"搜索医院 {hospital_name} 过程中发生严重错误: {str(e)}")
            return [] # 返回空列表表示处理失败
    
    except Exception as e:
        print(f"搜索医院 {hospital_name} 过程中发生严重错误: {str(e)}")
        return [] # 返回空列表表示处理失败

def save_data(data, hospital_name):
    """保存医生数据到JSON文件"""
    # 文件名使用医院名称
    filename = os.path.join(SAVE_PATH, f"{hospital_name}.json")
    
    # 将数据保存为JSON
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"已保存 {len(data)} 名医生信息到 {filename}")

def main():
    """主函数"""
    print("--- main 函数开始 ---") # 调试信息
    driver = setup_webdriver()
    if not driver:
        print("错误：未能初始化WebDriver，程序退出。")
        return # 如果driver是None，则退出
    print("--- WebDriver 设置完成 ---") # 调试信息
    
    try:
        # --- 暂时禁用交互式输入，强制从头开始 ---
        # continue_last = input("是否从特定医院开始爬取？(y/n): ").lower() == 'y'
        start_index = 0 
        print("--- 已设置从第一个医院开始爬取 (start_index=0) ---") # 调试信息
        
        # if continue_last:
        #     for i, hospital in enumerate(hospitals):
        #         print(f"{i+1}. {hospital}")
        #     
        #     try:
        #         start_index = int(input("请输入起始医院编号(1-19): ")) - 1
        #         if start_index < 0 or start_index >= len(hospitals):
        #             start_index = 0
        #             print("无效的编号，将从第一个医院开始爬取")
        #     except ValueError:
        #         print("无效的输入，将从第一个医院开始爬取")
        # --- 禁用结束 ---
        
        # 从指定医院开始爬取
        print(f"--- 开始遍历医院列表 (从索引 {start_index} 开始) ---") # 调试信息
        for hospital_name in hospitals[start_index:]:
            print(f"\n开始提取医院 {hospital_name} 的医生信息...")
            
            # 搜索并提取医生信息
            doctors = search_doctors_by_hospital(driver, hospital_name)
            
            # 保存数据
            if doctors:
                save_data(doctors, hospital_name)
            else:
                print(f"医院 {hospital_name} 未找到医生信息")
                # 创建空文件，表示已处理但没有数据
                save_data([], hospital_name)
                
            # 随机休息，避免被封
            time.sleep(random.uniform(3, 5))
    
    except Exception as e:
        print(f"程序主循环执行出错: {str(e)}") # 修改了错误提示
    
    finally:
        # 确保driver存在且有效再退出
        if 'driver' in locals() and driver:
             try:
                 driver.quit()
                 print("--- WebDriver 已关闭 ---") # 调试信息
             except Exception as quit_err:
                 print(f"关闭WebDriver时出错: {quit_err}")
        else:
            print("--- WebDriver 未成功初始化或已关闭 ---")
        print("程序执行完毕")

if __name__ == "__main__":
    # 屏蔽selenium日志输出
    import logging
    logging.getLogger('selenium').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    
    main()