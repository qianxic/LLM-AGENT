'''
网页HTML提取工具
功能：提取微医网页的完整HTML并保存到本地

使用示例：
https://www.wedoctor.com/search/expert?q=[参数名]#写一个即可，网页参数应该都是一样的
https://www.wedoctor.com/expert/a74ae927-de95-48f3-b979-eb5dd929568e000?hospDeptId=6175adaa-a60a-4b01-8855-4918c26006b3000&hospitalId=0f755e70-5114-4223-a0b3-11aafb90804a000
这个是从第一个页面中提出来的链接，你获取这个医生详情界面的完整html
'''

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import json

# 存储路径
SAVE_PATH = r"D:\代码\ESRI\ture_small\dataes\yisheng\html1"

# 确保存储目录存在
os.makedirs(SAVE_PATH, exist_ok=True)

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
    
    # 减少警告信息
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def save_html(url, filename):
    """获取并保存HTML内容"""
    driver = setup_webdriver()
    
    try:
        print(f"正在访问URL: {url}")
        driver.get(url)
        
        # 等待页面完全加载
        time.sleep(5)
        
        # 获取页面源码
        html_content = driver.page_source
        
        # 使用BeautifulSoup美化HTML结构
        soup = BeautifulSoup(html_content, 'html.parser')
        pretty_html = soup.prettify()
        
        # 保存HTML文件
        file_path = os.path.join(SAVE_PATH, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(pretty_html)
        
        print(f"HTML已保存至: {file_path}")
        
        # 同时保存页面截图
        screenshot_path = os.path.join(SAVE_PATH, f"{os.path.splitext(filename)[0]}.png")
        driver.save_screenshot(screenshot_path)
        print(f"页面截图已保存至: {screenshot_path}")
        
        return True
    
    except Exception as e:
        print(f"保存HTML时出错: {str(e)}")
        return False
    
    finally:
        driver.quit()

def save_search_page_html(hospital_name):
    """保存搜索结果页面的HTML"""
    url = f"https://www.chunyuyisheng.com/pc/search/?query=成都市新都区中医医院"
    filename = f"search_{hospital_name}.html"
    return save_html(url, filename)

def save_doctor_page_html(doctor_url, doctor_name):
    """保存医生详情页面的HTML"""
    filename = f"doctor_{doctor_name}.html"
    return save_html(doctor_url, filename)

def extract_doctor_links_from_html(html_file):
    """从保存的HTML文件中提取医生链接"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    doctor_links = []
    
    # 查找所有医生链接
    doctor_elements = soup.select("a.cover-bg.seo-anchor-text")
    
    for doctor in doctor_elements:
        name = doctor.text.strip()
        url = doctor.get('href')
        doctor_links.append({
            'name': name,
            'url': url
        })
    
    return doctor_links

def save_example_pages():
    """保存示例页面的HTML"""
    # 保存搜索结果页
    hospital_name = "成都市新都区中医医院"
    save_search_page_html(hospital_name)
    
    # 保存医生详情页
    doctor_url = "https://www.chunyuyisheng.com/pc/doctor/clinic_web_c4fe1a9c49e62ef3/"
    doctor_name = "example_doctor"
    save_doctor_page_html(doctor_url, doctor_name)

def main():
    """主函数 - 直接保存示例页面"""
    # 导入日志设置
    import logging
    logging.getLogger('selenium').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    
    print("开始执行：保存示例页面HTML...")
    save_example_pages()
    print("示例页面HTML保存完成。")

if __name__ == "__main__":
    main()


