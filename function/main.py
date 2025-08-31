import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
import json
import os
import datetime
import requests # Added for Directions API call
from openai import OpenAI
import asyncio
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI
from fastapi.responses import FileResponse

# 定义项目根目录，便于后续路径操作
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()
'''
http://localhost:8081/api/docs swagerUI文档
http://localhost:8081/api/redoc redoc文档


'''
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Construct the absolute path to favicon.ico relative to this script file
    favicon_path = os.path.join(BASE_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type='image/vnd.microsoft.icon') # Specify media type
    else:
        # Log or raise a more specific error if needed, but returning 404 is standard
        logger.error(f"Favicon file not found at expected path: {favicon_path}")
        try:
            # Try returning the response, FileResponse handles non-existence
            return FileResponse(favicon_path, media_type='image/vnd.microsoft.icon')
        except Exception as e:
             # This catch is broad, ideally FileResponse handles 404 internally
             # If it reaches here, something else might be wrong.
             logger.error(f"Error serving favicon from {favicon_path}: {e}")
             raise HTTPException(status_code=404, detail="Favicon not found")

# 导入数据库工具函数
from database_utils import (
    query_hospitals_by_city, 
    query_doctors_by_specialty_or_expertise, 
    query_medicines, 
    check_medicine_existence,
    get_doctor_details # 导入新函数
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 新的高德API密钥 (Web服务)
GAODE_API_KEY = "da1189d364f23db3328471cb0ec61f5d"
# 注意：后端调用 Web 服务 API (如地理编码) 通常仅需要 API Key。
# 安全密钥 (jscode) 主要用于前端 JS API 通过代理验证。
# 如果您的 Key 在高德控制台开启了 "WebService IP白名单" 或 "数字签名" 验证，
# 则可能需要额外配置 IP 或实现签名逻辑 (当前代码未实现签名)。

# 创建FastAPI应用并添加描述
main = FastAPI(
    title="地理信息智能助手服务",
    description="""
    # 地理信息智能助手 API
    
    这是一个结合了大语言模型和地理信息的智能助手服务。通过自然语言对话方式，用户可以获取城市位置、医院信息、当前时间以及驾车路线等信息。
    
    ## 功能特点
    
    * 自然语言查询地理信息
    * 城市位置查询和地图可视化
    * 医院信息查询和地图标记
    * 驾车路线规划和地图显示
    * 多轮对话支持
    
    ## 使用方法
    
    1. 访问根路径 `/` 获取地图交互界面
    2. 通过 `/api/chat` 端点发送聊天请求
    """,
    version="1.1.0", # Version bump
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# 添加CORS中间件，允许前端跨域访问
main.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，也可以指定特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 城市位置数据库(更详细)
CITY_LOCATIONS = {
    "北京": {"latitude": 39.9042, "longitude": 116.4074},
    "上海": {"latitude": 31.2304, "longitude": 121.4737},
    "广州": {"latitude": 23.1291, "longitude": 113.2644},
    "深圳": {"latitude": 22.5431, "longitude": 114.0579},
    "杭州": {"latitude": 30.2741, "longitude": 120.1551},
    "成都": {"latitude": 30.6571, "longitude": 104.0655},
    "重庆": {"latitude": 29.5628, "longitude": 106.5528},
    "西安": {"latitude": 34.3416, "longitude": 108.9398},
    "武汉": {"latitude": 30.5928, "longitude": 114.3052},
    "南京": {"latitude": 32.0584, "longitude": 118.7965},
}


# LLM客户端 - 从环境变量读取API密钥
try:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        logger.error("API密钥未设置，请设置环境变量 DASHSCOPE_API_KEY")
        client = None
    else:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        logger.info("OpenAI 客户端初始化成功")
except Exception as e:
    logger.error(f"OpenAI 客户端初始化失败: {e}")
    client = None

# --- Geocoding Helper --- #
def _get_coords(location_name, city="成都"):
    """Helper function to get coordinates using Gaode Geocoding API."""
    # Check simple city locations first
    clean_city_name = location_name.replace("市", "").replace("省", "")
    if clean_city_name in CITY_LOCATIONS:
        return CITY_LOCATIONS[clean_city_name]
        
    # Fallback to Geocoding API
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": GAODE_API_KEY,
        "address": location_name,
        "city": city,
        "output": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data["status"] == "1" and int(data["count"]) > 0:
            location = data["geocodes"][0]["location"]
            longitude, latitude = map(float, location.split(","))
            return {"latitude": latitude, "longitude": longitude}
        else:
            logger.warning(f"Geocoding failed for '{location_name}' in {city}: {data.get('info', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding API request failed for '{location_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing geocoding response for '{location_name}': {e}")
        return None

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_city_location",
            "description": "查询城市的地理坐标（经纬度），可以定位到指定城市。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "需要查询的城市名称，如北京、上海、成都等"
                    }
                },
                "required": ["city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hospitals",
            "description": "查询指定城市的医院信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "需要查询医院的城市名称"
                    }
                },
                "required": ["city_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的系统时间",
            "parameters": {}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_frontend_route_planning",
            "description": "当用户询问两个地点之间的路线时，调用此函数并将提取的起点和终点关键字返回给前端进行路线规划和显示。",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_keyword": {
                        "type": "string",
                        "description": "用户指定的出发地名称或关键字，例如 '春熙路' 或 '四川大学华西医院'"
                    },
                    "destination_keyword": {
                        "type": "string",
                        "description": "用户指定的目的地名称或关键字，例如 '成都东站' 或 '天府广场'"
                    }
                },
                "required": ["origin_keyword", "destination_keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_doctors",
            "description": "根据用户描述的症状、疾病、医生姓名或指定的科室名称，初步查找相关的医生列表（包含医生ID）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用户的症状描述、疾病名称、医生姓名或科室名称，例如 '心脏难受', '糖尿病', '张三', '心血管内科'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_medicine_info",
            "description": "根据药品名称或相关关键词查询药品信息，可以指定查询中药、西药或全部。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "药品名称或关键词，例如 '阿司匹林', '感冒清热颗粒'"
                    },
                    "medicine_type": {
                        "type": "string",
                        "enum": ["chinese", "western", "all"],
                        "description": "查询的药品类型：'chinese' (中药), 'western' (西药), 'all' (全部)。默认为 'all'。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_medicine_listing",
            "description": "查询指定的药品名称是否存在于医保相关药品数据库中。",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {
                        "type": "string",
                        "description": "需要查询的准确药品名称，例如 '柴胡口服液'"
                    }
                },
                "required": ["medicine_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_details",
            "description": "根据医生ID获取该医生的详细信息，包括教育背景、专长、简介、所属医院等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {
                        "type": "integer",
                        "description": "需要查询详情的医生ID"
                    }
                },
                "required": ["doctor_id"]
            }
        }
    },
]

# --- 工具函数实现 --- #
def get_city_location(arguments):
    """获取城市的经纬度坐标"""
    city_name = arguments.get("city_name", "")
    location = _get_coords(city_name) # Use helper
    
    if location:
        result = {
            "city": city_name.replace("市", "").replace("省", ""),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "command": "locate_city",
            "message": f"已找到{city_name}的位置"
        }
        return json.dumps(result, ensure_ascii=False)
    else:
        return json.dumps({"error": f"未找到城市 '{city_name}' 的位置信息"}, ensure_ascii=False)

def search_hospitals(arguments):
    """查询指定城市的医院信息 - 改为从数据库查询"""
    city_name = arguments.get("city_name", "")
    # 清理城市名称，虽然我们现在通过地址匹配
    cleaned_city_name = city_name.replace("市", "").replace("省", "") 
    
    logger.info(f"Querying hospitals for city: {cleaned_city_name}")
    hospitals = query_hospitals_by_city(cleaned_city_name)
    
    if hospitals:
        logger.info(f"Found {len(hospitals)} hospitals in DB for city: {cleaned_city_name}")
        result = {
            "city": cleaned_city_name,
            "hospitals": hospitals,
            "count": len(hospitals),
            "command": "show_hospitals",
            "message": f"找到{cleaned_city_name}的{len(hospitals)}家医院信息"
        }
        return json.dumps(result, ensure_ascii=False)
    else:
        logger.warning(f"No hospitals found in DB for city: {cleaned_city_name}")
        return json.dumps({"error": f"在数据库中未找到{cleaned_city_name}的医院信息"}, ensure_ascii=False)

def get_current_time():
    """获取当前日期和时间"""
    now = datetime.datetime.now()
    return json.dumps({"current_time": now.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False)

# --- 新增：前端路线规划触发函数 --- #
def trigger_frontend_route_planning(arguments):
    """将LLM提取的起点终点关键字格式化后返回给前端"""
    origin_keyword = arguments.get("origin_keyword")
    destination_keyword = arguments.get("destination_keyword")

    if not origin_keyword or not destination_keyword:
        # 理论上LLM会保证提供required参数，但也做个防御
        logger.warning("trigger_frontend_route_planning 缺少起点或终点关键字")
        return json.dumps({"error": "缺少起点或终点关键字"}, ensure_ascii=False)

    result = {
        "command": "plan_route_on_frontend",
        "origin": origin_keyword,
        "destination": destination_keyword
    }
    logger.info(f"触发前端路线规划: 从 '{origin_keyword}' 到 '{destination_keyword}'")
    return json.dumps(result, ensure_ascii=False)

# --- 修改：医生初筛工具函数 ---
def find_doctors_tool(arguments):
    """调用数据库函数进行医生初步筛选"""
    query = arguments.get("query")
    if not query:
        logger.warning("find_doctors_tool 缺少查询关键词")
        return json.dumps({"error": "缺少症状、疾病或科室查询关键词"}, ensure_ascii=False)
    
    logger.info(f"AI tool calling find_doctors with query: {query}")
    doctors_data = query_doctors_by_specialty_or_expertise(query)
    
    if doctors_data:
        # 可以考虑在这里对结果进行筛选或排序，例如只返回前几个最相关的
        # 目前直接返回查询到的所有结果（受限于LIMIT）
        result = {
            "doctors_list": doctors_data,
            "count": len(doctors_data),
            "message": f"根据 '{query}' 初步查询到 {len(doctors_data)} 位相关医生。"
        }
        logger.info(f"Found {len(doctors_data)} doctors for query '{query}'")
        return json.dumps(result, ensure_ascii=False, default=str) # 使用 default=str 处理可能的非序列化类型
    else:
        logger.warning(f"No doctors found in DB for query: {query}")
        return json.dumps({"error": f"未能找到与 '{query}' 相关的医生信息。"}, ensure_ascii=False)

# --- 新增：药品信息查询工具函数 ---
def find_medicine_info_tool(arguments):
    """调用数据库函数查询药品信息"""
    query = arguments.get("query")
    medicine_type = arguments.get("medicine_type", "all") # 默认为查询全部
    
    if not query:
        logger.warning("find_medicine_info_tool 缺少查询关键词")
        return json.dumps({"error": "缺少药品查询关键词"}, ensure_ascii=False)
        
    logger.info(f"AI tool calling find_medicine_info with query: {query}, type: {medicine_type}")
    medicines_data = query_medicines(query, medicine_type)
    
    if medicines_data:
        result = {
            "medicines_found": medicines_data,
            "count": len(medicines_data),
            "message": f"根据 '{query}' ({medicine_type}类) 查询到 {len(medicines_data)} 条药品信息。"
        }
        logger.info(f"Found {len(medicines_data)} medicines for query '{query}' (type: {medicine_type})")
        return json.dumps(result, ensure_ascii=False, default=str)
    else:
        logger.warning(f"No medicines found in DB for query: {query} (type: {medicine_type})")
        return json.dumps({"error": f"未能找到与 '{query}' ({medicine_type}类) 相关的药品信息。"}, ensure_ascii=False)

# --- 新增：检查药品是否存在工具函数 ---
def check_medicine_listing_tool(arguments):
    """调用数据库函数检查药品是否存在"""
    medicine_name = arguments.get("medicine_name")
    
    if not medicine_name:
        logger.warning("check_medicine_listing_tool 缺少药品名称")
        return json.dumps({"error": "缺少需要查询的药品名称"}, ensure_ascii=False)
        
    logger.info(f"AI tool calling check_medicine_listing for medicine: {medicine_name}")
    found_medicine_info = check_medicine_existence(medicine_name)
    
    if found_medicine_info:
        result = {
            "medicine_found": True,
            "medicine_details": found_medicine_info,
            "message": f"在数据库中查询到药品 '{medicine_name}' 的记录。"
        }
        logger.info(f"Medicine '{medicine_name}' found.")
        return json.dumps(result, ensure_ascii=False, default=str)
    else:
        result = {
            "medicine_found": False,
            "message": f"在数据库中未查询到药品 '{medicine_name}' 的记录。"
        }
        logger.info(f"Medicine '{medicine_name}' not found.")
        return json.dumps(result, ensure_ascii=False)

# --- 新增：获取医生详情工具函数 ---
def get_doctor_details_tool(arguments):
    """调用数据库函数获取指定医生的详细信息"""
    doctor_id = arguments.get("doctor_id")
    
    if doctor_id is None or not isinstance(doctor_id, int):
        logger.warning(f"get_doctor_details_tool 接收到无效的 doctor_id: {doctor_id}")
        return json.dumps({"error": "需要提供有效的医生ID (整数)"}, ensure_ascii=False)
        
    logger.info(f"AI tool calling get_doctor_details for doctor ID: {doctor_id}")
    details = get_doctor_details(doctor_id)
    
    if details:
        result = {
            "doctor_details": details,
            "message": f"获取到医生ID {doctor_id} 的详细信息。"
        }
        logger.info(f"Successfully retrieved details for doctor ID {doctor_id}.")
        return json.dumps(result, ensure_ascii=False, default=str)
    else:
        logger.warning(f"No details found in DB for doctor ID: {doctor_id}")
        return json.dumps({"error": f"未能找到医生ID {doctor_id} 的详细信息。"}, ensure_ascii=False)

# 函数映射表
function_mapper = {
    "get_city_location": get_city_location,
    "search_hospitals": search_hospitals,
    "get_current_time": get_current_time,
    "trigger_frontend_route_planning": trigger_frontend_route_planning,
    "find_doctors": find_doctors_tool,
    "find_medicine_info": find_medicine_info_tool,
    "check_medicine_listing": check_medicine_listing_tool,
    "get_doctor_details": get_doctor_details_tool,
}

# 定义模型
class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ChatRequest(BaseModel):
    """
    聊天请求模型，包含用户消息和可选的历史记录及用户位置
    """
    message: str = Field(..., description="用户发送的消息内容", example="从春熙路到成都东站怎么走？")
    history: List[Dict[str, Any]] = Field(default=[], description="可选的对话历史记录")
    user_latitude: Optional[float] = Field(None, description="用户当前的纬度 (由前端提供)")
    user_longitude: Optional[float] = Field(None, description="用户当前的经度 (由前端提供)")
    user_address: Optional[str] = Field(None, description="用户当前的地址描述 (由前端提供)")

class ToolResult(BaseModel):
    """工具执行结果模型"""
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    command: Optional[str] = None
    message: Optional[str] = None
    hospitals: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    current_time: Optional[str] = None
    polyline: Optional[str] = None
    distance: Optional[str] = None # Distance in meters
    duration: Optional[str] = None # Duration in seconds
    origin: Optional[Dict[str, Any]] = None
    destination: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str = Field(..., description="AI助手的回复内容")
    tool_results: List[Dict[str, Any]] = Field(default=[], description="工具调用结果")
    history: List[Dict[str, Any]] = Field(..., description="更新后的对话历史")

@main.post("/api/chat", response_model=ChatResponse, tags=["聊天"],
          summary="发送聊天消息并获取回复",
          description="""
          该接口接收用户消息，使用大语言模型分析用户意图，根据需要调用相应工具（如地理位置查询、医院信息查询等），
          并返回处理结果。支持多轮对话，可以通过history参数传递之前的对话历史。

          ## 使用示例

          ### 请求:
          ```json
          {
            "message": "从春熙路到成都东站怎么走？",
            "history": [],
            "user_latitude": 30.6571,
            "user_longitude": 104.0655,
            "user_address": "四川省成都市锦江区红星路三段1号"
          }
          ```

          ### 响应:
          ```json
          {
            "response": "已规划从春熙路到成都东站的驾车路线",
            "tool_results": [
              {
                "city": "成都",
                "latitude": 30.6571,
                "longitude": 104.0655,
                "command": "locate_city",
                "message": "已找到成都的位置"
              }
            ],
            "history": [
              {"role": "user", "content": "从春熙路到成都东站怎么走？"},
              {"role": "assistant", "content": "我将为您查询从春熙路到成都东站的驾车路线", "tool_calls": [...]} 
              // 其他历史消息
            ]
          }
          ```
          """)
async def chat(request: ChatRequest):
    """
    聊天接口：接收用户消息并返回AI助手的回复
    
    - **message**: 用户发送的消息内容
    - **history**: 可选的对话历史记录
    - **user_latitude**: 用户当前的纬度 (由前端提供)
    - **user_longitude**: 用户当前的经度 (由前端提供)
    - **user_address**: 用户当前的地址描述 (由前端提供)
    返回:
    - **response**: AI助手的回复内容
    - **tool_results**: 工具调用结果列表
    - **history**: 更新后的对话历史
    """
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI客户端未正确初始化")
    
    messages = request.history.copy()
    messages.append({"role": "user", "content": request.message})
    
    # --- 注入系统指令和位置上下文 ---
    # 可以在这里加入更复杂的逻辑判断是否需要此引导
    # 暂时对所有请求都加入引导，让AI自行判断是否适用
    system_guidance = {
        "role": "system",
        "content": """# Role: 医疗问诊助手系统规则制定者
## Profile
- author: qianxi
- version: 1.1  # Version bump for new logic
- language: 中文
- description: 该提示词用于为医疗问诊助手设定系统级交互规则和内容输出标准，确保其具备**智能意图识别、关键词提取、工具灵活调度**、医学判断、医生推荐、输出格式控制等完整流程能力，并确保输出信息条理清晰、专业严谨。

## Skills
- **核心能力：智能调度**
    - 深度理解用户自然语言查询，准确识别核心意图。
    - 从用户输入中智能提取关键信息，并分类（如：症状、疾病、药品、医生名、地理位置、时间、任务指令等）。
    - 基于语义和关键词分析，结合对话上下文，灵活判断是否需要调用工具、调用哪个或哪些工具。
    - 能够规划并（在单一响应中）请求调用多个工具以完成复杂任务。
    - 在信息不足或意图模糊时，能主动发起澄清式提问。
- 具备基础医疗知识并能分析用户提供的身体不适症状。
- 能根据分析结果判断对应的医学科室或疾病关键词。
- 调用医疗相关工具时具备规范的参数使用逻辑，避免模糊描述。
- 具备Markdown格式化输出的能力，确保信息清晰分点。
- 严格执行特定多轮对话（如导航）的流程控制。
- 能合理解释医生推荐依据，利用其介绍和教育背景。
- 懂得在合适情境中表达人文关怀，并保持专业沟通风格。

## Rules
- **首要规则：智能分析与决策优先**
    - **收到任何用户输入后，必须先进行意图识别和关键词提取。**
    - **基于分析结果，智能决策：**
        - **纯对话**: 如果用户只是闲聊或提问通用知识，无需调用工具，直接回答。
        - **信息查询**: 如果用户查询信息（医生、医院、药品、位置等），调用最相关的查询工具（`find_doctors`, `get_doctor_details`, `search_hospitals`, `find_medicine_info`, `check_medicine_listing`, `get_city_location`）。
        - **任务执行**: 如果用户要求执行动作（如导航），遵循特定工作流程（见Workflows）。 **特别注意：如果用户明确指定了导航目的地（如"我要去XX医院"），应直接进入导航流程，避免调用`search_hospitals`等通用搜索工具。**
        - **多意图**: 如果用户请求包含多个意图，规划并在一次响应中请求调用所有必要的工具。
        - **信息不足**: 如果执行任务所需信息不全（如导航缺少起点），必须先提问获取信息，禁止盲目调用工具或猜测。
- **导航规则**
- 所有位置经纬度信息都不可以展示给用户，只能展示给前端。
- 所有的上下文都要参考，且不能有重复信息出现
- 所有症状分析必须基于基础医学知识，分析后推导专业医学关键词。
- 导航规则：
    - 禁止在未确认用户位置信息时调用路径规划工具。
    - 禁止在未确认用户位置信息时调用路径规划工具。
    - 禁止在未确认用户位置信息时调用路径规划工具。
    - 禁止在未确认用户位置信息时调用路径规划工具。
    - 禁止在未确认用户位置信息时调用路径规划工具。
    - 禁止在未确认用户位置信息时调用路径规划工具。
- 使用`find_doctors`工具时**禁止**使用模糊症状（如"头疼"）作为参数，应先结合专业的医疗知识进行分析，然后告知用户。
- 重点信息、对话中出现的所有多项信息、建议、步骤必须使用Markdown列表格式输出。
- 重点信息，位置、医生、医院、药品、时间、路线等，必须使用Markdown的格式进行加粗显示输出。
- 标注的重点信息，必须作为你的上下文的全局记忆中的一部分。
- 医生推荐必须结合其`introduction`与`education`字段解释专业性。
- **特定流程规则优先**: 在执行明确的多步骤工作流程（如导航确认）时，必须严格遵守该流程的特定规则（例如，第3步禁止调用工具）。
- 对话流程分为4步：1) 症状分析与医生推荐；2) 医生详情提供；3) 导航确认；4) 路线规划执行。这些步骤是针对完整医疗咨询导航场景的指导，AI应根据实际对话灵活应用或跳过某些步骤。
- 在路线规划成功后，如为医疗咨询，需添加健康关怀语。
- 禁止在未确认用户位置信息时调用路径规划工具。
- 工具结果（如JSON）**不可直接展示**，需转换为自然语言确认语句。
- 建议用户就医时选择打车，并提醒尽量有人陪同。
- Emoji仅在表达积极情感或祝愿时可用，禁止用于工具展示、确认信息等严肃场景。
- 明确药品医保报销说明结构及信息来源链接[https://www.gov.cn/zhengce/zhengceku/2023-01/18/content_5737840.htm]《国家基本医疗保险、工伤保险和生育保险药品目录（2022年）》的通知医保发〔2023〕5号，链接要用超链接的形式。
- 避免如下逻辑错误：
  1. 医生专长 ≠ 症状原因，需表述为"适合诊断/治疗某症状"；
  2. 医院定位应表述为"已定位到"，非"已到达"；
  3. 输出医保信息不得超过三句话且链接可点击。

## Workflows
*说明：以下流程主要针对典型的"症状咨询 -> 医生推荐 -> 导航就医"场景，AI应结合智能调度规则，根据实际用户输入灵活应用。*

1. **初步问诊与智能响应**: 
   - 用户提出问题（可能是症状、查药、找医院等）。
   - **执行核心智能调度逻辑**：分析意图、提取关键词。
   - **决策**: 
     - 若为症状咨询，进行分析，可能追问细节，并在信息充分后考虑调用 `find_doctors`。
     - 若为查药，考虑调用 `find_medicine_info` 或 `check_medicine_listing`。
     - 若为找医院/位置，考虑调用 `search_hospitals` 或 `get_city_location`。
     - 若为其他或意图不明，进行对话或澄清。

2. **医生选择与详情（承接上一步找到医生列表后）**:
   - 用户从列表中选择医生（或AI推荐后用户接受）。
   - 调用 `get_doctor_details` 获取详情。
   - 用其`introduction`、`education`以及`expertise`字段展示医生信息，体现医生的专业性。
   - **主动询问**是否需要导航至该医生所在的医院，并明确医院名称。

3. **导航确认（严格流程）**: 
   - 用户确认需要导航。
   - **规则：此步骤绝对禁止调用任何工具 (`tool_calls`)！仅能生成文本回复！**
   - **检查系统上下文中的 `user_address`。**
   - **回复模板（必须严格二选一，仅确认起点）：**
     - **情况A：如果 `user_address` 存在且有效（不含"经度"、"纬度"等坐标关键词）**，使用此模板：
       `好的，您要去[步骤2确定的医院名称]。系统检测到您当前在[user_address]附近。如果此位置不准确，请告诉我您的修正后的位置。`
     - **情况B：如果 `user_address` 不存在或看起来像坐标**，使用此模板：
       `好的，您要去[步骤2确定的医院名称]。系统已检测到您当前的位置。如果此位置不准确，请告诉我您的修正后的位置。`
   - **必须**在回复中提及步骤2确定的**正确医院名称**。

4. **路线规划执行（严格流程）**: 
   - 用户对步骤3的确认进行回复后（例如用户说"是的"、"好的"、"开始吧"、"位置不对，我在XX路"）**:**
   - **规则：此时，你的响应必须同时包含两部分：1) 生成调用 `trigger_frontend_route_planning` 的 `tool_calls` 指令；2) 生成告知用户的文本回复。**
   - **获取起点 (`origin_keyword`) - 必须严格按以下顺序决定**: 
     - **第一顺位 (用户新地址)**：检查用户在**上一步回复**中是否提供了**新的、具体的地址文本**。如果提供了，**必须使用这个新地址**作为起点。
     - **第二顺位 (上下文地址)**：如果第一顺位不满足，则检查系统上下文中的 `user_address`, `[用户的地址信息]`。。如果 `user_address` **存在、非空且不包含** "经度"、"纬度"、"latitude"、"longitude" 等关键词，则**必须使用 `user_address`** 作为起点。
   - **获取终点 (`destination_keyword`)**: **必须**使用步骤2中确定的**医院名称**。
   - **生成文本回复**: 回复用户说明规划已启动，并确认**正确获取到**的起点和终点。例如：`好的，已为您规划从[第一/二/三顺位获取到的起点]到[步骤2确定的终点]的路线。`
   - 如是医疗话题，添加关怀语。

5. **独立查询处理**: 
   - 如果用户的请求不属于上述导航流程，而是独立的查询（如"北京协和医院在哪里？"或"布洛芬是处方药吗？"），则直接应用**核心智能调度逻辑**，判断并调用合适的工具，然后生成回复。

## OutputFormat
- 所有多项输出需用Markdown列表格式。
- 医疗导航、医生推荐等需清晰分步骤进行展示。
- 避免一次性输出太多信息，保持对话节奏自然简洁。
- 每步交互确保语言专业、条理清晰、人性关怀适度。

## Init
系统角色初始化成功：医疗问诊助手已加载**智能调度**规则。
请智能分析用户意图，灵活调用工具，并严格遵循特定流程规范和输出格式。
"""
    }
    
    # **** 新增：检查并注入位置上下文 ****
    location_context_message = None
    if request.user_latitude is not None and request.user_longitude is not None:
        address_info = f"在 {request.user_address}" if request.user_address else ""
        location_text = f"Context: User's current mainroximate location is {address_info} (latitude: {request.user_latitude:.5f}, longitude: {request.user_longitude:.5f}). Use this information if relevant to the conversation, especially for navigation or location-based queries."
        location_context_message = {"role": "system", "content": location_text}
        logger.info(f"Injecting location context: {location_text}")
    # ************************************
    
    # 将引导指令和位置上下文（如果存在）放在合适的位置
    insert_index = 0 if len(messages) == 1 else len(messages) - 1 # 插入到用户消息之前
    if location_context_message:
         messages.insert(insert_index, location_context_message)
    # 确保系统引导指令也在 (如果两个都存在，位置上下文会在引导指令之前)
    messages.insert(insert_index, system_guidance) 
    # --- 结束注入 ---
    
    logger.info(f"接收到聊天请求: {request.message}")
    logger.debug(f"传入历史记录 (含引导指令): {messages}")

    try:
        logger.info("准备第一次调用LLM，发送的消息历史:")
        for i, msg in enumerate(messages):
            logger.info(f"  [History {i}] Role: {msg.get('role', 'N/A')}, Content: {msg.get('content', '')[:100]}... Tools: {bool(msg.get('tool_calls'))}")

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=messages,
            tools=tools,
            stream=False
        )
        
        assistant_message = response.choices[0].message
        # 使用 model_dump() 转换为字典以确保持久化
        messages.append(assistant_message.model_dump(exclude_unset=True))
        logger.debug(f"LLM 第一次响应 (含工具调用决策): {assistant_message}")

        
        if assistant_message.tool_calls:
            tool_call_results_for_llm = []
            frontend_tool_results = [] # Store parsed results for frontend
            
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                tool_call_id = tool_call.id
                logger.info(f"LLM 请求调用工具: {function_name}")
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    logger.debug(f"工具参数: {arguments}")
                    
                    if function_name in function_mapper:
                        if function_name == "get_current_time":
                            function_output_str = function_mapper[function_name]()
                        else:
                            function_output_str = function_mapper[function_name](arguments)
                    else:
                        logger.warning(f"未知的工具名称: {function_name}")
                        function_output_str = json.dumps({"error": f"未知工具: {function_name}"}, ensure_ascii=False)
                        
                    logger.debug(f"工具 '{function_name}' 输出 (JSON string): {function_output_str}")
                    
                    # Prepare result for LLM (second call)
                    tool_call_results_for_llm.append({
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_output_str # LLM expects string content
                    })
                    
                    # Prepare parsed result for frontend
                    try:
                        parsed_output = json.loads(function_output_str)
                        if "error" not in parsed_output:
                            frontend_tool_results.append(parsed_output)
                        else:
                             logger.warning(f"工具 '{function_name}' 返回错误: {parsed_output['error']}")
                    except json.JSONDecodeError:
                        logger.error(f"无法解析工具 '{function_name}' 的输出为JSON: {function_output_str}")
                        # Optionally add raw string to frontend results if needed

                except json.JSONDecodeError as e:
                     logger.error(f"无法解析工具 '{function_name}' 的参数: {tool_call.function.arguments}, 错误: {e}")
                     # Add error message for this specific tool call to LLM
                     tool_call_results_for_llm.append({
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": "无法解析工具参数"}, ensure_ascii=False)
                     })
                except Exception as e:
                    logger.error(f"调用工具 '{function_name}' 时发生错误: {e}", exc_info=True)
                    tool_call_results_for_llm.append({
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": f"执行工具时出错: {str(e)}"}, ensure_ascii=False)
                    })

            
            # 将工具结果添加到消息历史中，准备第二次调用LLM
            messages.extend(tool_call_results_for_llm)
            logger.debug(f"准备第二次调用LLM，添加的工具结果: {tool_call_results_for_llm}")
            
            # 第二轮：将工具调用结果提供给LLM生成最终回复
            
            logger.info("准备第二次调用LLM（生成最终回复），发送的消息历史:")
            for i, msg in enumerate(messages):
                logger.info(f"  [History {i}] Role: {msg.get('role', 'N/A')}, Content: {msg.get('content', '')[:100]}... Tools: {bool(msg.get('tool_calls'))} Tool ID: {msg.get('tool_call_id')}")

            final_response = client.chat.completions.create(
                model="qwen-plus",
                messages=messages,
                stream=False
            )
            
            final_message = final_response.choices[0].message
            messages.append(final_message.model_dump(exclude_unset=True))
            logger.debug(f"LLM 第二次响应 (最终回复): {final_message}")
            
            # 准备最终返回给前端的数据
            result = {
                "response": final_message.content or "", # Ensure response is not None
                "tool_results": frontend_tool_results, # Use parsed results for frontend
                "history": [msg for msg in messages if msg is not None] # Filter out potential None values
            }
        else:
            # 无工具调用，直接返回回复
            logger.info("LLM 未请求调用工具")
            result = {
                "response": assistant_message.content or "",
                "tool_results": [],
                "history": [msg for msg in messages if msg is not None]
            }
        
        logger.info(f"向前端返回响应. 回复长度: {len(result['response'])}, 工具结果数量: {len(result['tool_results'])}")
        logger.debug(f"最终历史记录: {result['history']}")
        return result
    
    except Exception as e:
        logger.error(f"处理聊天请求时发生严重错误: {e}", exc_info=True)
        # Return a user-friendly error without crashing
        return ChatResponse(response=f"抱歉，处理您的请求时遇到内部错误: {str(e)}", tool_results=[], history=messages)

@main.get("/", response_class=HTMLResponse, tags=["前端"],
         summary="获取地图交互界面",
         description="返回智能地图助手的交互界面HTML页面。用户可以通过此界面与系统进行交互，查询地理信息并在地图上查看结果。")
async def read_root():
    """
    返回地图交互界面的HTML页面
    
    该页面集成了聊天功能和地图显示功能，用户可以:
    - 通过自然语言查询城市位置
    - 查询特定城市的医院信息
    - 查询当前时间
    - 在地图上查看查询结果
    """
    # 使用相对路径，基于当前脚本文件的目录
    file_path = os.path.join(BASE_DIR, "gaode.html")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"找不到 gaode.html 文件，尝试路径: {file_path}")
        raise HTTPException(status_code=404, detail=f"找不到 gaode.html 文件: {file_path}")
        
    logger.info(f"找到HTML文件: {file_path}")
    return FileResponse(file_path)

# 挂载静态文件目录(确保路径相对于脚本目录)
# 将挂载点指向脚本所在的目录，这样 gaode.html 也能通过 /static/gaode.html 访问（虽然我们直接在根目录提供）
main.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

@main.get("/api", tags=["文档"],
         summary="API信息",
         description="返回API基本信息和文档链接")
async def api_info():
    """
    返回API基本信息和文档链接
    """
    return {
        "name": "地理信息智能助手API",
        "version": "1.1.0",
        "description": "集成LLM与地理信息查询、路线规划功能的智能助手服务",
        "documentation": "/api/docs",
        "redoc": "/api/redoc",
        "main_interface": "/"
    }

if __name__ == "__main__":
    uvicorn.run("main:main", host="127.0.0.1", port=8081, reload=True)
