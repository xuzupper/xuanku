from openai import OpenAI
import os
import base64

#  读取本地文件，并编码为 Base64 格式
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# 将xxxx/test.png替换为您本地图像的绝对路径
base64_image = encode_image(r"D:\学习专用\BANK\202506\screenshot-20250705-213419.png")
client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-vl-ocr-latest",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    # 需要注意，传入Base64，图像格式（即image/{format}）需要与支持的图片列表中的Content Type保持一致。"f"是字符串格式化的方法。
                    # PNG图像：  f"data:image/png;base64,{base64_image}"
                    # JPEG图像： f"data:image/jpeg;base64,{base64_image}"
                    # WEBP图像： f"data:image/webp;base64,{base64_image}"
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    # 输入图像的最小像素阈值，小于该值图像会按原比例放大，直到总像素大于min_pixels
                    "min_pixels": 28 * 28 * 4,
                    # 输入图像的最大像素阈值，超过该值图像会按原比例缩小，直到总像素低于max_pixels
                    "max_pixels": 28 * 28 * 8192
                },
                 # qwen-vl-ocr-latest支持在以下text字段中传入Prompt，若未传入，则会使用默认的Prompt：Please output only the text content from the image without any additional descriptions or formatting.
                 # 如调用qwen-vl-ocr-1028，模型会使用固定Prompt：Read all the text in the image.，不支持用户在text中传入自定义Prompt
                {"type": "text", "text": "请提取流水图像中的记账日期、记账时间、金额、余额、交易名称、附言、对方账户名数据。要求准确无误的提取上述关键信息、不要遗漏和捏造虚假信息，模糊或者强光遮挡的单个文字可以用英文问号?代替。返回数据格式以json方式输出，格式为：{'记账日期'：'xxx', '记账金额'：'xxx', '金额'：'xxx', '余额'：'xxx', '交易名称'：'xxx', '附言'：'xxx', '对方账户名'：'xxx'"},

            ],
        }
    ],
)
print(completion.choices[0].message.content)

message1 = completion.choices[-1].message.content


# completion = client.chat.completions.create(
#     model="qwen-coder-plus",
#     messages=[
#         {'role': 'system', 'content': '你是一个mysql数据库专家'},
#         {'role': 'user', 'content': f'请将{message1}中的JSON部分转化成insert语句输出。不要输出非代码的内容。'}],
#     )

# print(completion.choices[0].message.content)

# message2 = completion.choices[0].message.content

import re
pattern = re.compile(r"```json(.*?)```", re.DOTALL) 
match = pattern.search(message1)

if match: 
    json_statement = match.group(1).strip() 
    #print(json_statement) 
else: print("未找到 json 语句")

import json
import pymysql
import uuid


def generate_uuid_id():
    return str(uuid.uuid4())


# 数据清洗函数
def clean_amount(value):
    return float(value.replace(',', ''))

#list4 = json.loads(json_statement)

# 假设 completion.choices[0].message.content 是一个列表
if isinstance(json_statement, str):
        try:
            # 解析 JSON 字符串
            data = json.loads(json_statement)
            # print(data)
            # 在这里可以对解析后的 JSON 数据进行其他操作
            # JSON 数据
            json_data = data
            
              # 数据库连接配置
            conn = pymysql.connect(
                host='192.168.126.129',
                user='root',
                password='123456',
                database='mysql',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
# 数据清洗
            for item  in json_data:
                 #for key, value in item.items():    
                    cleaned_data = {
                        "id": generate_uuid_id(),
                        "记账日期": item["记账日期"],
                        "记账时间": item["记账时间"],
                        "金额": clean_amount(item["金额"]),
                        "余额": clean_amount(item["余额"]),
                        "交易名称": item["交易名称"],
                        "附言": item["附言"],
                        "对方账户名": item["对方账户名"],
                        "对方卡号账号": item["对方卡号/账号"],
                        "对方开户行": item["对方开户行"]
                    }
                    print(cleaned_data)

                    try:
                        with conn.cursor() as cursor:
                            # 构建 SQL 插入语句（包含 id 字段）

                            sql = """
                            INSERT INTO `bankflow` 
                            (`id`, `记账日期`, `记账时间`, `金额`, `余额`, `交易名称`, `附言`, `对方账户名`, `对方卡号账号`, `对方开户行`)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            values = (
                                cleaned_data["id"],
                                cleaned_data["记账日期"],
                                cleaned_data["记账时间"],
                                cleaned_data["金额"],
                                cleaned_data["余额"],
                                cleaned_data["交易名称"],
                                cleaned_data["附言"],
                                cleaned_data["对方账户名"],
                                cleaned_data["对方卡号账号"],
                                cleaned_data["对方开户行"]
                            )
                            print("SQL 插入语句：", sql,values)
                            cursor.execute(sql, values)
                            conn.commit()
                            print("数据插入成功！")
                    except Exception as e:
                        print(f"插入失败：{e}")
                        conn.rollback()

            conn.close()
            print("数据插入完成！数据库连接关闭")
        except json.JSONDecodeError:
            print(f"无法解析 JSON 字符串: {json_statement}")
else:
    print("completion.choices[0].message.content 不是列表")




# import os
# from pathlib import Path
# from openai import OpenAI,APIError  

# client = OpenAI(
#     api_key=os.getenv("DASHSCOPE_API_KEY"),  # 如果您没有配置环境变量，请在此处替换您的API-KEY
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope服务base_url
# )
# #将文件通过OpenAI兼容接口上传到阿里云百炼平台，保存至平台安全存储空间后获取文件ID。
# file_path = Path(r"D:\学习专用\BANK\202506\screenshot-20250705-213419.png")

# if file_path.exists():
#     file_object = client.files.create(file=file_path, purpose="file-extract")
#     print(file_object.id)
# else:
#     print(f"文件 {file_path} 不存在，请检查文件路径和文件名。")


# #将文件ID传入System Message中且数量不超过 100 个，并在User Message中输入问题

# try:
#     # 初始化messages列表
#     completion = client.chat.completions.create(
#         model="qwen-long",
#         messages=[
#             {'role': 'system', 'content': '你是一个专业的图片识别助手.'},
#             # 请将 'file-fe-xxx'替换为您实际对话场景所使用的 fileid。
#             {'role': 'system', 'content': f'file-extract:{file_object.id}'},
#             {'role': 'user', 'content': '请将图片中的记账日期、记账时间、金额、余额、交易名称、附言、对方账户名数据以JSON格式输出'}
#         ],
#         # 所有代码示例均采用流式输出，以清晰和直观地展示模型输出过程。如果您希望查看非流式输出的案例，请参见https://help.aliyun.com/zh/model-studio/text-generation
#         stream=True,
#         stream_options={"include_usage": True}
#     )

#     full_content = ""
#     for chunk in completion:
#         if chunk.choices and chunk.choices[0].delta.content:
#             # 拼接输出内容
#             full_content += chunk.choices[0].delta.content
#             print(chunk.model_dump())

#     print(full_content)

# except APIError  as e:
#     print(f"错误信息：{e}")
#     print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")

# # MySQL数据库连接配置
# # db_config = {
# #     'user': 'root',
# #     'password': '123456',
# #     'host': '192.168.126.200',
# #     'port': 3306,
# #     'database': 'your_database'
# # }

# # def process_image(image_path):
# #     """
# #     处理图片并提取结构化数据
# #     """
# #     # 读取图片
# #     img = cv2.imread(image_path)
    
# #     # 调用Qwen-Long模型提取数据
# #     result = qwen_model.understand(
# #         image=image_path,
# #         tasks=['ocr', 'object_detection']
# #     )
    
# #     return result

# # def insert_to_mysql(data, table_name):
# #     """
# #     将结构化数据插入MySQL
# #     """
# #     try:
# #         connection = pymysql.connect(**db_config)
# #         cursor = connection.cursor()
# #         
# #         # 构建插入语句
# #         columns = ', '.join(data.keys())
# #         values = ', '.join(['%s'] * len(data))
# #         sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
# #         
# #         # 执行插入
# #         cursor.execute(sql, tuple(data.values()))
# #         connection.commit()
# #         print(f"成功插入数据到{table_name}")
# #         
# #     except Error as e:
# #         print(f"数据库错误: {e}")
# #     finally:
# #         if connection:
# #             connection.close()

# # if __name__ == "__main__":
# #     # 示例用法
# #     image_path = "D:\\学习专用\\BANK\\202506\\screenshot-20250705-213419.jpg"
# #     extracted_data = process_image(image_path)
# #     print(extracted_data)
# #     # insert_to_mysql(extracted_data, "your_table")