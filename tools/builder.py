import base64


"""
    工作空间为项目的目录
"""

# 目标路径
toScriptFile = 'source/images.py'

# 资源路径及其对应的变量名
data = [
    {'from': 'source/icon.jpg', 'to': 'BIcon'}
]

# 清空文件中的内容
with open(toScriptFile, 'w') as f:
    pass

# 写入数据
for i in data:
    with open(i['from'], 'rb') as f:
        tmp = base64.b64encode(f.read())

    with open(toScriptFile, 'w+') as f:
        f.write(f"{i['to']} = {tmp}\n")
