import os
import dashscope

messages = [
    {'role': 'user', 'content': '哪吒2的票房'}
]

response = dashscope.Generation.call(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwq-plus",  # 此处以qwq-plus为例，可按需更换模型名称
    messages=messages,
    enable_search = True, # 开启联网搜索的参数
    search_options = {
        "forced_search": True, # 强制开启联网搜索
        "enable_source": True, # 使返回结果包含搜索来源的信息，OpenAI 兼容方式暂不支持返回
        "enable_citation": True, # 开启角标标注功能
        "citation_format": "[ref_<number>]", # 角标形式为[ref_i]
        "search_strategy": "pro" # 模型将搜索10条互联网信息
    },
    # QwQ 模型仅支持流式输出方式调用
    stream=True,
)

# 定义完整思考过程
reasoning_content = ""
# 定义完整回复
answer_content = ""
# 判断是否结束思考过程并开始回复
is_answering = False
# 判断是否为第一个chunk，便于打印搜索信息
is_first_chunk = True

print("=" * 20 + "搜索信息" + "=" * 20)

for chunk in response:
    if is_first_chunk:
        search_results = chunk.output.search_info["search_results"]
        for web in search_results:
            print(f"[{web['index']}]: [{web['title']}]({web['url']})")
        print("=" * 20 + "思考过程" + "=" * 20)
        reasoning_content += chunk.output.choices[0].message.reasoning_content
        print(chunk.output.choices[0].message.reasoning_content,end="",flush=True)
        is_first_chunk = False
    else:
        # 如果思考过程与回复皆为空，则忽略
        if (chunk.output.choices[0].message.content == "" and 
            chunk.output.choices[0].message.reasoning_content == ""):
            pass
        else:
            # 如果当前为思考过程
            if (chunk.output.choices[0].message.reasoning_content != "" and 
                chunk.output.choices[0].message.content == ""):
                print(chunk.output.choices[0].message.reasoning_content, end="",flush=True)
                reasoning_content += chunk.output.choices[0].message.reasoning_content
            # 如果当前为回复
            elif chunk.output.choices[0].message.content != "":
                if not is_answering:
                    print("\n" + "=" * 20 + "完整回复" + "=" * 20)
                    is_answering = True
                print(chunk.output.choices[0].message.content, end="",flush=True)
                answer_content += chunk.output.choices[0].message.content

# 如果您需要打印完整思考过程与完整回复，请将以下代码解除注释后运行
# print("=" * 20 + "完整思考过程" + "=" * 20 + "\n")
# print(f"{reasoning_content}")
# print("=" * 20 + "完整回复" + "=" * 20 + "\n")
# print(f"{answer_content}")
# 如果您需要打印本次请求的 Token 消耗，请将以下代码解除注释后运行
# print("\n"+"="*20+"Token 消耗"+"="*20)
# print(chunk.usage)