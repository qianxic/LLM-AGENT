import os
from openai import OpenAI
import datetime
import requests # pip install requests
import json

# --- 配置 ---
MODEL = "qwen-plus" # 使用的模型，例如 "qwen-plus", "qwen-max", etc.
# 设置为 True 以尝试启用联网搜索 (需要模型和API支持, 可能需要调整参数传递方式)
ENABLE_WEB_SEARCH = False
# 如果需要JSON输出，取消注释此行并确保模型支持
# RESPONSE_FORMAT = {"type": "json_object"}
RESPONSE_FORMAT = None # 默认不强制特定格式

# --- 初始化 OpenAI 客户端 ---
# 确保设置了环境变量 DASHSCOPE_API_KEY 或直接提供 api_key
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    # 尝试简单调用以验证凭据
    client.models.list()
    print("OpenAI 客户端初始化成功。")
except Exception as e:
    print(f"错误：无法初始化 OpenAI 客户端。请检查 API Key 和网络连接。")
    print(f"详细错误: {e}")
    exit()


# --- 定义可用工具 ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当你想知道现在的时间时非常有用。",
            "parameters": {}
        }
    },
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
                "required": ["location"]
            }
        }
    },
    # --- 新增工具：查询城市位置 ---
    {
        "type": "function",
        "function": {
            "name": "query_city_location",
            "description": "查询指定城市的大致地理坐标（经纬度），用于在地图上定位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "需要查询位置的城市名称，例如 '北京市', '上海市' 等。"
                    }
                },
                "required": ["city_name"]
            }
        }
    }
    # --- 工具列表结束 ---
]

# --- 工具函数实现 ---
def get_current_time():
    """获取当前日期和时间"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def get_current_weather(arguments):
    """获取指定城市的天气 (模拟实现)"""
    location = arguments.get("location")
    if not location:
        return json.dumps({"error": "需要提供城市名称"}, ensure_ascii=False)

    # --- 这里是调用真实天气API的地方 ---
    # 这是一个模拟实现，实际使用时请替换为真实API调用
    print(f"[工具执行] 模拟获取 {location} 的天气...")
    # 示例 (需要安装 requests: pip install requests):
    # try:
    #     # 需要替换为你的天气API Key和正确的URL
    #     # api_key = "YOUR_WEATHER_API_KEY"
    #     # url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric&lang=zh_cn"
    #     # response = requests.get(url)
    #     # response.raise_for_status() # 检查请求是否成功
    #     # weather_data = response.json()
    #     # # 提取需要的信息
    #     # main_weather = weather_data.get('weather', [{}])[0].get('description', '未知')
    #     # temp = weather_data.get('main', {}).get('temp', '未知')
    #     # return json.dumps({"location": location, "temperature": f"{temp}°C", "condition": main_weather}, ensure_ascii=False)
    # except requests.exceptions.RequestException as e:
    #     print(f"错误: 调用天气API失败 - {e}")
    #     return json.dumps({"error": f"获取天气API失败: {e}"}, ensure_ascii=False)
    # except Exception as e:
    #     print(f"错误: 处理天气数据时出错 - {e}")
    #     return json.dumps({"error": f"处理天气数据失败: {e}"}, ensure_ascii=False)

    # 模拟返回
    return json.dumps({"location": location, "temperature": "模拟25°C", "condition": "模拟晴朗"}, ensure_ascii=False)
    # --- 真实API调用代码结束 ---

# --- 新增工具函数实现：查询城市位置 (模拟) ---
def query_city_location(arguments):
    """获取指定城市的大致经纬度 (模拟实现)"""
    city_name = arguments.get("city_name")
    if not city_name:
        return json.dumps({"error": "需要提供城市名称"}, ensure_ascii=False)

    print(f"[工具执行] 模拟查询 {city_name} 的位置...")

    # 预设一些常见城市的模拟坐标
    mock_locations = {
        "北京": {"latitude": 39.9042, "longitude": 116.4074},
        "北京市": {"latitude": 39.9042, "longitude": 116.4074},
        "上海": {"latitude": 31.2304, "longitude": 121.4737},
        "上海市": {"latitude": 31.2304, "longitude": 121.4737},
        "广州": {"latitude": 23.1291, "longitude": 113.2644},
        "广州市": {"latitude": 23.1291, "longitude": 113.2644},
        "深圳": {"latitude": 22.5431, "longitude": 114.0579},
        "深圳市": {"latitude": 22.5431, "longitude": 114.0579},
        "杭州": {"latitude": 30.2741, "longitude": 120.1551},
        "杭州市": {"latitude": 30.2741, "longitude": 120.1551},
    }

    # 查找城市，进行模糊匹配 (去掉'市')
    # 更健壮的方式是处理各种后缀，这里简化
    normalized_city = city_name.replace('市', '').replace('省', '')
    location_data = mock_locations.get(normalized_city)

    if location_data:
        result = {
            "city": city_name,
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"],
            "message": "获取到城市坐标，请在地图上渲染此位置。" # 给前端的提示
        }
        return json.dumps(result, ensure_ascii=False)
    else:
        # 如果找不到，返回一个提示信息
        return json.dumps({"error": f"未找到城市 '{city_name}' 的模拟坐标。"}, ensure_ascii=False)
# --- 查询城市位置函数结束 ---


# --- 函数映射表 ---
function_mapper = {
    "get_current_weather": get_current_weather,
    "get_current_time": get_current_time,
    "query_city_location": query_city_location # 添加新工具到映射表
}

# --- 主对话循环 ---
messages = []
conversation_idx = 1

print("\n欢迎使用集成LLM Agent!")
print(f"模型: {MODEL}, 联网搜索: {'启用 (尝试)' if ENABLE_WEB_SEARCH else '禁用'}, JSON输出: {'启用' if RESPONSE_FORMAT else '禁用'}")
print(f"已加载工具: {list(function_mapper.keys())}")
print("输入 'exit' 或 'quit' 结束对话。")

while True:
    print("\n"+"="*20+f"第{conversation_idx}轮对话"+"="*20)
    user_input = input("你: ")
    if user_input.lower() in ['exit', 'quit']:
        print("再见！")
        break

    messages.append({"role": "user", "content": user_input})

    tool_info = []          # 重置本轮收集的工具调用信息(原始格式)
    reasoning_content = ""  # 重置思考过程
    accumulated_response = "" # 存储第一次调用可能产生的回复片段
    finish_reason_first_call = None # 存储第一次调用的结束原因

    # --- 步骤 1 & 2: 发送请求给LLM，让其决策是否调用工具 ---
    print("\n" + "=" * 20 + "LLM思考中..." + "=" * 20)
    try:
        completion_params = {
            "model": MODEL,
            "messages": messages,
            "tools": tools,
            "parallel_tool_calls": True, # 允许多个工具并行调用
            "stream": True,
            # "stream_options": {"include_usage": True} # 可选
        }

        if ENABLE_WEB_SEARCH:
             # completion_params['extra_body'] = {'enable_search': True} # 视API支持情况添加
             print("[配置] 尝试启用联网搜索 (注意: 兼容模式下的支持可能有限或需要特定参数)")

        completion = client.chat.completions.create(**completion_params)

        current_tool_calls = {} # 存储流式接收的工具调用信息

        print("--- LLM Stream ---")
        for chunk in completion:
            if not chunk.choices and hasattr(chunk, 'usage') and chunk.usage:
                print(f"\n--- Usage (Initial Call): {chunk.usage} ---")
                continue
            if not chunk.choices: continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason
            if finish_reason: # 记录第一次调用的结束原因
                finish_reason_first_call = finish_reason

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                print(delta.reasoning_content, end="", flush=True)
                reasoning_content += delta.reasoning_content

            if delta and delta.content:
                print(delta.content, end="", flush=True)
                accumulated_response += delta.content

            if delta and delta.tool_calls:
                for tool_call_chunk in delta.tool_calls:
                    index = tool_call_chunk.index
                    if index not in current_tool_calls:
                        current_tool_calls[index] = {"id": "", "name": "", "arguments": ""}
                    if tool_call_chunk.id:
                        current_tool_calls[index]['id'] += tool_call_chunk.id
                    if tool_call_chunk.function and tool_call_chunk.function.name:
                         current_tool_calls[index]['name'] += tool_call_chunk.function.name
                    if tool_call_chunk.function and tool_call_chunk.function.arguments:
                         current_tool_calls[index]['arguments'] += tool_call_chunk.function.arguments

        print("\n--- Stream End ---")

        # 整理收集到的工具信息(原始格式)
        if finish_reason_first_call == "tool_calls":
            tool_info = [call for index, call in sorted(current_tool_calls.items())]

        # ★★★ 修改点1 开始 ★★★
        # 如果模型决定调用工具，或者即使没有调用工具但有回复，
        # 都需要将 assistant 的思考或回复（可能附带工具调用）添加到 messages
        if finish_reason_first_call == "tool_calls":
            # 准备 API 要求的 tool_calls 格式
            api_tool_calls = []
            for call in tool_info:
                api_tool_calls.append({
                    "id": call.get('id', ''), # 使用 .get 以防万一
                    "type": "function",
                    "function": {
                        "name": call.get('name', ''),
                        "arguments": call.get('arguments', '')
                    }
                })
            # 添加包含 tool_calls 的 assistant 消息
            messages.append({
                "role": "assistant",
                "content": accumulated_response or None, # 如果有想法/文字就放进去
                "tool_calls": api_tool_calls
            })
        elif accumulated_response: # 如果没有工具调用，但有回复内容
            messages.append({"role": "assistant", "content": accumulated_response})
        # 如果既没有工具调用也没有回复内容，则不添加助手消息

        # ★★★ 修改点1 结束 ★★★

    except Exception as e:
        print(f"\n发生错误 (LLM 初步调用): {e}")
        if messages and messages[-1]["role"] == "user":
             messages.pop() # 移除刚才添加的用户消息
        continue # 跳过本轮对话

    # --- 步骤 3 & 4: 如果有工具调用，执行工具函数 ---
    if tool_info: # tool_info 是在第一次调用结束时整理的
        print("\n"+"="*20+"执行工具函数"+"="*20)
        tool_outputs = [] # 存储工具执行结果以备后用

        for call_info in tool_info: # 使用第一次调用收集的原始 tool_info
            function_name = call_info.get('name')
            arguments_string = call_info.get('arguments')
            tool_call_id = call_info.get('id')

            if not function_name or arguments_string is None or not tool_call_id:
                print(f"警告：工具调用信息不完整，跳过: Name={function_name}, Args={arguments_string}, ID={tool_call_id}")
                tool_outputs.append({
                    "tool_call_id": tool_call_id or f"missing_id_{function_name}",
                    "role": "tool",
                    "content": json.dumps({"error": "Incomplete tool call information from LLM."}, ensure_ascii=False)
                })
                continue

            print(f"准备执行: {function_name}")
            try:
                arguments = json.loads(arguments_string)
            except json.JSONDecodeError as e:
                print(f"错误：解析工具 '{function_name}' 参数失败: {e}")
                print(f"原始参数字符串: {arguments_string}")
                function_output = json.dumps({"error": f"Invalid arguments format received: {e}"}, ensure_ascii=False)
            else:
                function_to_call = function_mapper.get(function_name)
                if function_to_call:
                    try:
                        if function_name == "get_current_time":
                            function_output = function_to_call()
                        else:
                            function_output = function_to_call(arguments)
                        if not isinstance(function_output, str):
                             function_output = json.dumps(function_output, ensure_ascii=False)
                    except Exception as e:
                        print(f"错误：执行工具函数 {function_name} 时出错: {e}")
                        function_output = json.dumps({"error": f"Function execution error: {e}"}, ensure_ascii=False)
                else:
                    print(f"错误：找不到名为 {function_name} 的工具函数。")
                    function_output = json.dumps({"error": f"Function '{function_name}' not found."}, ensure_ascii=False)

            print(f"工具输出 ({function_name}): {function_output}\n")
            # 准备要添加到 messages 的 tool role 消息
            tool_outputs.append({
                "tool_call_id": tool_call_id,
                "role": "tool",
                "content": function_output,
            })

        # --- 步骤 5: 将工具结果发回给LLM ---
        print("="*20+"LLM整合工具结果中"+"="*20)
        # 将所有工具结果作为单独的消息添加到历史中
        messages.extend(tool_outputs)

        try:
            final_completion_params = {
                "model": MODEL,
                "messages": messages,
                "stream": True,
            }
            if RESPONSE_FORMAT:
                 final_completion_params['response_format'] = RESPONSE_FORMAT
                 print("[配置] 请求最终回复为 JSON 输出格式")

            final_completion = client.chat.completions.create(**final_completion_params)

            final_answer_content = ""
            print("--- LLM Final Response Stream ---")
            final_finish_reason = None
            for chunk in final_completion:
                 if not chunk.choices and hasattr(chunk, 'usage') and chunk.usage:
                     print(f"\n--- Usage (Final Call): {chunk.usage} ---")
                     continue
                 if not chunk.choices: continue

                 delta = chunk.choices[0].delta
                 if chunk.choices[0].finish_reason:
                    final_finish_reason = chunk.choices[0].finish_reason

                 if delta and delta.content:
                     print(delta.content, end="", flush=True)
                     final_answer_content += delta.content

            print("\n--- Stream End ---")

            if final_finish_reason == "stop":
                 messages.append({"role": "assistant", "content": final_answer_content})
            else:
                # 如果最终回复不是因为 stop 结束（例如 length, content_filter 或 error）
                print(f"[警告] LLM 最终回复因 '{final_finish_reason}' 结束，而非 'stop'。可能未完全生成。")
                # 仍然尝试添加收到的内容
                messages.append({"role": "assistant", "content": final_answer_content or "[LLM未能生成最终回复]"})


        except Exception as e:
            print(f"\n发生错误 (LLM 最终调用): {e}")

            # ★★★ 修改点2 开始 ★★★
            # 清理：移除本次添加的 tool 消息和触发它们的 assistant 消息
            num_tools_added = len(tool_outputs)
            assistant_msg_index = -(num_tools_added + 1)

            if len(messages) >= abs(assistant_msg_index) and \
               messages[assistant_msg_index]["role"] == "assistant" and \
               messages[assistant_msg_index].get("tool_calls"):
                # 确认前面的消息是包含 tool_calls 的 assistant 消息
                print(f"[清理] 移除 {num_tools_added} 条 tool 消息和 1 条 assistant 消息。")
                for _ in range(num_tools_added + 1):
                     if messages: messages.pop()
            else:
                 # 如果结构不符合预期，可能只移除 tool 消息，或者不移除以供调试
                 print(f"[清理警告] 消息结构异常，只尝试移除 {num_tools_added} 条 tool 消息。")
                 for _ in range(num_tools_added):
                      if messages: messages.pop()
            # ★★★ 修改点2 结束 ★★★
            continue # 跳过本轮

    else:
        # --- 如果没有工具调用，第一次的 accumulated_response 就是最终回复 ---
        # （对应的 assistant 消息已在第一次调用后添加）
        print("\n"+"="*20+"最终回复 (无工具调用)"+"="*20)
        if accumulated_response:
             print(accumulated_response)
        else:
             # 这种情况对应第一次调用既没调用工具也没回复内容
             print("[提示] 模型没有调用工具，也没有生成回复内容。")
             # 可能需要添加一个空助手消息以维持对话轮次，或根据需要处理
             messages.append({"role": "assistant", "content": "[无回复]"})


    # 清理 messages 列表，移除 content 为 None 且没有 tool_calls 的助手消息（如果存在）
    # messages = [msg for msg in messages if not (msg["role"] == "assistant" and msg.get("content") is None and not msg.get("tool_calls"))]

    conversation_idx += 1

# --- 文件结束 ---
