LLM-AGENT/
├── function/                # 主要的应用代码目录
│   └── stat.py              # FastAPI 后端主程序
│   └── gaode.html           # 前端 HTML 界面 (假设与 app.py 在同一目录)
│   └── database_utils.py    # 数据库操作工具函数 (假设与 app.py 在同一目录)
│   └── requirements.txt     # Python 依赖文件 (假设与 app.py 在同一目录)
├── dataes/                  # 数据存储目录
│   └── table_total.db       # SQLite 数据库文件
│   └── ... (其他数据文件或子目录, 如 yiyuan/, yisheng/, yaopin/)
├── study_ali/               # 学习笔记来自官方api参考文档
│   └── ...
└── READEME.MD               # 项目说明文件

直接在function中的main.py运行即可，运行前需参考高德设置设置代理服务器，链接：https://lbs.amap.com/api/javascript-api-v2/guide/abc/jscode
默认转发端口为8080，网址主链接为：http://127.0.0.1:8080/
基于fastapi框架构建模型交互接口，api交互文档链接为：http://127.0.0.1:8080/api/docs#/


语言模型使用阿里通义千问的QWQ深度思考模型，使用相同的方式即可更换您的api，必须设置于系统变量中，

Function Calling（工具调用）
https://help.aliyun.com/zh/model-studio/qwq?spm=a2c4g.11186623.0.0.3330429eateA8a#c858c412ecx9i

API参考
https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api?spm=5176.29619931.J_0p4alxzoxDplpQPpY27Hs.2.c047521cJGOBPN 


GIThub
https://github.com/qianxic/LLM-AGENT

1. 可用工具总结 (Available Tools Summary)
   AI (LLM) 可以根据用户的意图，决定调用后端定义的一系列工具（函数）来获取信息或执行特定操作。这些工具及其对应的后端处理逻辑如下：

   - **`get_city_location`**: 获取指定城市的经纬度坐标。
   - **`search_hospitals`**: 查询指定城市的医院列表信息。
   - **`get_current_time`**: 获取当前的系统时间。
   - **`trigger_frontend_route_planning`**: 触发前端进行路线规划和显示（后端不计算路径）。
   - **`find_doctors`**: 根据症状、疾病、科室等初步查找相关医生。
   - **`find_medicine_info`**: 查询药品的通用信息。
   - **`check_medicine_listing`**: 查询特定药品名称是否存在于医保相关数据库中。
   - **`get_doctor_details`**: 获取指定 ID 的医生的详细信息。

2.意图到功能映射 (AI Intent -> Backend Tool -> Action)
   - **位置查询**: 用户询问 "查询[城市名]的位置" -> AI 识别意图 -> 调用后端 `get_city_location` 工具 -> 后端执行 `get_city_location` 函数获取坐标 -> 返回 `{command: "locate_city"}` -> 前端 `handleToolResults` 调用 `locateCity` 函数在地图上标记。
   - **医院查询**: 用户询问 "[城市名]有哪些医院" -> AI 识别意图 -> 调用后端 `search_hospitals` 工具 -> 后端执行 `search_hospitals` 函数查询数据库 -> 返回 `{command: "show_hospitals"}` -> 前端 `handleToolResults` 调用 `showHospitals` 函数在地图上标记。
   - **路线规划**: 用户询问 "从[地点A]到[地点B]怎么走" -> AI 识别意图 -> 调用后端 `trigger_frontend_route_planning` 工具 -> 后端执行 `trigger_frontend_route_planning` 函数提取起终点 -> 返回 `{command: "plan_route_on_frontend"}` -> 前端 `handleToolResults` 调用高德地图 JS API 的 `driving.search` 进行路线规划和绘制。
   - **药品医保查询**: 用户询问 "[药品名]是否为医保药物" 或类似问题 -> AI 识别意图 -> 调用后端 `check_medicine_listing` 工具 -> 后端执行 `check_medicine_listing_tool` 函数查询数据库（通常进行精确匹配）-> LLM 根据查询结果和系统指令生成回复。
   - **药品信息查询**: 用户询问 "查询[药品名]的信息" -> AI 识别意图 -> 调用后端 `find_medicine_info` 工具 -> 后端执行 `find_medicine_info_tool` 函数查询数据库 -> LLM 根据查询结果生成回复。
   - **医生推荐**: 用户描述症状、疾病或科室 -> AI 分析并推断关键词 -> 调用后端 `find_doctors` 工具 -> 后端执行 `find_doctors_tool` 函数查询数据库 -> LLM 根据查询结果生成推荐列表。
   - **医生详情**: 用户选择或询问特定医生详情 (通常需要先通过 `find_doctors` 获取医生ID) -> AI 识别意图 -> 调用后端 `get_doctor_details` 工具 (传入医生ID) -> 后端执行 `get_doctor_details_tool` 函数查询数据库 -> LLM 根据详细信息和系统指令生成回复。
   - **获取当前时间**: 用户询问 "现在几点了" 或类似问题 -> AI 识别意图 -> 调用后端 `get_current_time` 工具 -> 后端执行 `get_current_time` 函数 -> LLM 根据结果生成回复。

3. 后端AI处理
位置：后端app.py文件（tools_demo/demo/app.py）
利用fastapi，定义为get接口，@app.get("/", response_class=HTMLResponse, tags=["前端"],位置于app.py的772行。


