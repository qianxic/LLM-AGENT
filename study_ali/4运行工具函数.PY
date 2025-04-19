import os
from openai import OpenAI
import datetime
import requests # 可能需要安装 requests: pip install requests
import json

# 初始化OpenAI客户端，配置阿里云DashScope服务
client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),  # 从环境变量读取API密钥
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 定义可用工具列表
tools = [
    # 工具1 获取当前时刻的时间
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当你想知道现在的时间时非常有用。",
            "parameters": {}  # 无需参数
        }
    },  
    # 工具2 获取指定城市的天气
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "当你想查询指定城市的天气时非常有用。",
            "parameters": {  
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市或县区，比如北京市、杭州市、余杭区等。"
                    }
                },
                "required": ["location"]  # 必填参数
            }
        }
    }
]

# 定义问题，请不要设置 System Message
messages = [{"role": "user", "content": input("请输入问题：")}]
completion = client.chat.completions.create(
    model="qwq-plus",  # 此处以qwq-plus为例，可更换为其它qwq模型
    messages=messages,
    tools=tools,
    parallel_tool_calls=True,
    stream=True,
    # 解除注释后，可以获取到token消耗信息
    # stream_options={
    #     "include_usage": True
    # }
)



reasoning_content = ""  # 定义完整思考过程
answer_content = ""     # 定义完整回复
tool_info = []          # 存储工具调用信息
is_answering = False   # 判断是否结束思考过程并开始回复
print("="*20+"思考过程"+"="*20)
for chunk in completion:
    if not chunk.choices:
        # 处理用量统计信息
        print("\n"+"="*20+"Usage"+"="*20)
        print(chunk.usage)
    else:
        delta = chunk.choices[0].delta
        # 处理AI的思考过程（链式推理）
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
            reasoning_content += delta.reasoning_content
            print(delta.reasoning_content,end="",flush=True)  # 实时输出思考过程
            
        # 处理最终回复内容
        else:
            if not is_answering:  # 首次进入回复阶段时打印标题
                is_answering = True
                print("\n"+"="*20+"回复内容"+"="*20)
            if delta.content is not None:
                answer_content += delta.content
                print(delta.content,end="",flush=True)  # 流式输出回复内容
            
            # 处理工具调用信息（支持并行工具调用）
            if delta.tool_calls is not None:
                for tool_call in delta.tool_calls:
                    index = tool_call.index  # 工具调用索引，用于并行调用
                    
                    # 动态扩展工具信息存储列表
                    while len(tool_info) <= index:
                        tool_info.append({})
                    
                    # 收集工具调用ID（用于后续函数调用）
                    if tool_call.id:
                        tool_info[index]['id'] = tool_info[index].get('id', '') + tool_call.id
                    
                    # 收集函数名称（用于后续路由到具体函数）
                    if tool_call.function and tool_call.function.name:
                        tool_info[index]['name'] = tool_info[index].get('name', '') + tool_call.function.name
                    
                    # 收集函数参数（JSON字符串格式，需要后续解析）
                    if tool_call.function and tool_call.function.arguments:
                        tool_info[index]['arguments'] = tool_info[index].get('arguments', '') + tool_call.function.arguments
            
print(f"\n"+"="*19+"工具调用信息"+"="*19)
if not tool_info:
    print("没有工具调用")
else:
    print(tool_info)

# 步骤5:运行工具函数
# 请将以下代码粘贴到步骤4 代码后

# 工具函数：获取当前时间
def get_current_time():
    """获取当前日期和时间"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

# 工具函数：获取天气 (示例，需要替换为实际的天气API调用)
def get_current_weather(arguments):
    """获取指定城市的天气"""
    location = arguments.get("location")
    if not location:
        return json.dumps({"error": "需要提供城市名称"})
    
    # --- 这里需要替换为调用真实天气API的代码 ---
    # 这是一个伪代码示例，你需要找一个天气服务API并替换掉这部分
    try:
        # 假设你有一个天气API的URL和需要API Key
        # api_key = "YOUR_WEATHER_API_KEY" 
        # url = f"https://api.weatherprovider.com/current?city={location}&appid={api_key}&units=metric"
        # response = requests.get(url)
        # response.raise_for_status() # 如果请求失败则抛出异常
        # weather_data = response.json()
        # return json.dumps(weather_data) # 返回JSON格式的天气数据
        
        # 临时占位符回复
        print(f"模拟获取 {location} 的天气...")
        return json.dumps({"location": location, "temperature": "25°C", "condition": "晴朗"}) 
        
    except Exception as e:
        return json.dumps({"error": f"获取天气失败: {e}"})
    # --- 真实API调用代码结束 ---

def function_calling():
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=messages,
        tools=tools,
        stream=True
    )
    for chunk in completion:
        print(chunk.model_dump_json())

function_calling()

# 创建一个函数映射表
function_mapper = {
    "get_current_weather": get_current_weather,
    "get_current_time": get_current_time
}

print("正在执行工具函数...")
# --- 修改开始 ---
# 检查是否有工具需要调用
if tool_info:
    # 遍历收集到的工具调用信息
    for call_info in tool_info:
        # 获取函数名称和参数字符串
        function_name = call_info.get('name')
        arguments_string = call_info.get('arguments')
        tool_call_id = call_info.get('id') # 获取 tool_call_id，后续步骤会用到

        if not function_name or not arguments_string or not tool_call_id:
            print(f"警告：工具调用信息不完整，跳过执行: {call_info}")
            continue

        print(f"\n准备执行工具: {function_name}")
        print(f"参数字符串: {arguments_string}")
        print(f"调用 ID: {tool_call_id}")

        # 使用json模块解析参数字符串
        try:
            arguments = json.loads(arguments_string)
        except json.JSONDecodeError as e:
            print(f"错误：解析工具参数失败: {e}")
            print(f"原始参数字符串: {arguments_string}")
            # 可以选择将错误信息作为结果，或者跳过
            function_output = json.dumps({"error": f"Invalid arguments format: {e}"})
            # continue # 如果希望跳过，取消注释这行
        else:
            # 获取函数实体
            function_to_call = function_mapper.get(function_name)

            if function_to_call:
                try:
                    # 调用函数
                    # 注意：检查函数是否需要参数
                    if function_name == "get_current_time": # get_current_time 不需要参数
                         function_output = function_to_call()
                    else: # 其他函数（如 get_current_weather）需要参数
                         function_output = function_to_call(arguments)
                except Exception as e:
                    print(f"错误：执行工具函数 {function_name} 时出错: {e}")
                    function_output = json.dumps({"error": f"Function execution error: {e}"})
            else:
                print(f"错误：找不到名为 {function_name} 的工具函数。")
                function_output = json.dumps({"error": f"Function '{function_name}' not found."})

        # 打印工具的输出
        print(f"工具函数输出：{function_output}\n")

        # 重要：将工具调用的结果添加到messages列表中，以便进行下一步对话
        # 这里我们暂时只打印，完整的实现需要将结果添加到 messages 列表中
        # 例如: messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": function_output})
        # 然后再进行一次 client.chat.completions.create 调用

else:
    print("没有检测到需要执行的工具函数。")
# --- 修改结束 ---