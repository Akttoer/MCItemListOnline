import json
import os
from flask import Flask, request, jsonify, send_from_directory
import threading

print("请输入服务端口(默认5000):")
port = 5000
uport = input()
if uport == None:
    print("未输入端口，将使用默认端口")
else:
    port = uport

app = Flask(__name__)

# 指定存储STI文件的目录
STI_DIR = 'sti_files'
# 指定记录状态的json文件路径
STATUS_FILE = 'status.json'

# 检查并创建sti_files目录和status.json文件
def check_and_create_files():
    if not os.path.exists(STI_DIR):
        os.makedirs(STI_DIR)
        print(f"创建了目录：{STI_DIR}")
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'w', encoding='utf-8') as file:
            json.dump({"modified": False}, file, ensure_ascii=False, indent=4)
        print(f"创建了文件：{STATUS_FILE}")

check_and_create_files()

@app.route('/api/status', methods=['GET'])
def get_status():
    file_path = os.path.join(STATUS_FILE)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return jsonify(data)

# 列出所有STI文件
@app.route('/files', methods=['GET'])
def list_files():
    files = [f for f in os.listdir(STI_DIR) if f.endswith('.sti')]
    return jsonify(files)

# 读取特定STI文件的数据
@app.route('/data/<filename>', methods=['GET'])
def get_data(filename):
    file_path = os.path.join(STI_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return jsonify(data)

# 更新特定STI文件的数据
@app.route('/data/<filename>/<int:item_index>', methods=['PUT'])
def update_data(filename, item_index):
    file_path = os.path.join(STI_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        # 确保item_index在有效范围内
        if 0 <= item_index < len(data):
            # 更新数据
            data[item_index] = request.json

            # 修改status.json中的modified值为True
            update_status(True)

            # 设置定时器，在5秒后将modified值改回False
            timer = threading.Timer(5, update_status, args=(False,))
            timer.start()

        else:
            return jsonify({'error': 'Item not found'}), 404
        # 保存更新后的数据
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        return jsonify(data[item_index])
    except Exception as e:
        # 打印详细的错误信息
        app.logger.error(f"Error updating data: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

def update_status(modified):
    """更新status.json中的modified值"""
    with open(STATUS_FILE, 'r+') as file:
        status = json.load(file)
        status['modified'] = modified
        file.seek(0)
        json.dump(status, file, ensure_ascii=False, indent=4)
        file.truncate()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=port)