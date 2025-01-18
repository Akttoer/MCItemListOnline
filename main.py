import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import csv
import chardet
import json
import requests
import os
import configparser
import threading

def open_file():
    global online_mode
    if not prompt_to_save_if_modified():  # 检查是否有未保存的修改，并提示保存
        return  # 如果用户取消操作，则返回，不继续打开文件
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("STI files", "*.sti")])
    if file_path:
        open_file_path(file_path)
        config, config_path = load_config()
        save_config(config, config_path, file_path)
        # 重置 base_url 和其他相关状态变量
        online_mode = False
        global check_mode
        check_mode = False
    else:
        status_str_ver.set('未选择文件')


def open_last_file(config):
    global online_mode
    last_opened_file = config['DEFAULT']['last_opened_file']
    if last_opened_file and os.path.exists(last_opened_file):
        open_file_path(last_opened_file)
        online_mode = False
        global check_mode
        check_mode = False
    else:
        messagebox.showinfo("提示", "没有找到上次打开的文件")
def save_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".sti", filetypes=[("STI files", "*.sti")])
    if file_path:
        try:
            data = []
            for item in treeview.get_children():
                values = treeview.item(item, 'values')
                # 确保所有值都是字符串类型
                data.append([str(value) for value in values])
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            status_str_ver.set(f'文件成功保存 {file_path}')
            global modified
            modified = False  # 保存文件后设置为False
        except Exception as e:
            messagebox.showerror("错误", f"保存文件时出错: {e}")
            status_str_ver.set('保存文件失败')

def calculate_boxes_and_groups(quantity):
    items_per_group = 64
    groups_per_box = 27
    # 计算盒数
    total_boxes = quantity // (items_per_group * groups_per_box)
    # 计算组数
    total_groups = (quantity // items_per_group) - (total_boxes * groups_per_box)
    # 计算个数
    pieces = quantity - ((total_boxes * groups_per_box + total_groups) * items_per_group)
    return total_boxes, total_groups, pieces

def new_connection():
    messagebox.showinfo("新建连接", "新建连接功能尚未实现")

def disconnect():
    messagebox.showinfo("断开连接", "断开连接功能尚未实现")

def about():
    messagebox.showinfo("关于", "原理图材料列表查看器\n版本 1.0\n作者: SmailPang")


def on_right_click(event, filename =None, base_url = None):
    iid = treeview.identify_row(event.y)
    if iid:
        treeview.selection_set(iid)
        completion_status = treeview.item(iid, 'values')[5]
        right_click_menu.entryconfig("修改状态为进行中",
                                     command=lambda: mark_as_completed(filename, base_url, "进行中"))
        right_click_menu.entryconfig("修改状态为已完成",
                                     command=lambda: mark_as_completed(filename, base_url, "已完成"))
        right_click_menu.entryconfig("修改状态为未完成",
                                     command=lambda: mark_as_completed(filename, base_url, "未完成"))

        if completion_status == "未完成":
            right_click_menu.entryconfig("修改状态为进行中", state="normal")
            right_click_menu.entryconfig("修改状态为已完成", state="normal")
            right_click_menu.entryconfig("修改状态为未完成", state="disabled")
        elif completion_status == "进行中":
            right_click_menu.entryconfig("修改状态为进行中", state="disabled")
            right_click_menu.entryconfig("修改状态为已完成", state="normal")
            right_click_menu.entryconfig("修改状态为未完成", state="normal")
        else:
            right_click_menu.entryconfig("修改状态为进行中", state="normal")
            right_click_menu.entryconfig("修改状态为已完成", state="disabled")
            right_click_menu.entryconfig("修改状态为未完成", state="normal")

        right_click_menu.post(event.x_root, event.y_root)

def mark_as_completed(filename, base_url, target_status):
    global modified, online_mode, check_mode
    selected_item = treeview.selection()
    if selected_item:
        for iid in selected_item:
            item_index = treeview.index(iid)
            new_data = list(treeview.item(iid, 'values'))
            new_data[5] = target_status
            treeview.item(iid, values=tuple(new_data))
            if show_background_color:
                tag = 'in_progress' if target_status == "进行中" else 'completed' if target_status == "已完成" else 'not_completed'
                treeview.item(iid, tags=(tag,))
            modified = True
            status_str_ver.set('当前修改未保存')
            if base_url and not update_data_on_server(base_url, filename, item_index, new_data):
                new_data[5] = treeview.item(iid, 'values')[5]  # 恢复原状态
                treeview.item(iid, values=tuple(new_data))
                if show_background_color:
                    tag = 'in_progress' if new_data[5] == "进行中" else 'completed' if new_data[5] == "已完成" else 'not_completed'
                    treeview.item(iid, tags=(tag,))
                modified = False
                if online_mode:
                    status_str_ver.set('更新失败，数据已恢复')
        # 提交修改后，将check_mode设置为False
        check_mode = False
        # 5秒后将check_mode设置为True
        threading.Timer(5, lambda: reset_check_mode(base_url)).start()
    else:
        messagebox.showinfo("提示", "请先选择一行")

def reset_check_mode(base_url):
    global check_mode
    check_mode = True
    check_modified_status(base_url)

def on_closing():
    global check_mode
    if modified:  # 如果有修改未保存
        response = messagebox.askyesnocancel("保存", "是否保存当前修改？")
        if response is True:  # 点击“是”
            check_mode = False
            save_file()
            root.destroy()
        elif response is False:  # 点击“否”
            check_mode = False
            root.destroy()
        else:  # 点击“取消”
            pass
    else:
        check_mode = False
        root.destroy()

def prompt_to_save_if_modified():
    if modified:
        response = messagebox.askyesnocancel("保存", "当前文件有未保存的修改，是否保存？")
        if response is True:  # 点击“是”
            save_file()
        elif response is False:  # 点击“否”
            pass
        else:  # 点击“取消”
            return False  # 返回False表示操作被取消
    return True  # 返回True表示可以继续打开新文件

def clear_treeview():
    for i in treeview.get_children():
        treeview.delete(i)


def load_config():
    config = configparser.ConfigParser()
    config_path = 'config.ini'
    if not os.path.exists(config_path):
        # 如果配置文件不存在，创建一个默认的配置文件
        config['DEFAULT'] = {'last_opened_file': ''}
        with open(config_path, 'w') as configfile:
            config.write(configfile)
    else:
        # 读取配置文件
        config.read(config_path)
    return config, config_path

def save_config(config, config_path, last_opened_file):
    config['DEFAULT']['last_opened_file'] = last_opened_file
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def open_file_path(file_path):
    global current_filename
    if file_path.endswith('.sti'):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                clear_treeview()
                for item in data:
                    item_name, quantity, boxes, groups, pieces, completion_status = item
                    tag = 'completed' if completion_status == "已完成" else 'not_completed'
                    treeview.insert('', 'end', values=[item_name, quantity, boxes, groups, pieces, completion_status], tags=(tag,))
            status_str_ver.set(f'文件成功打开 {file_path}')
            global modified
            modified = False  # 打开文件后设置为False
            current_filename = os.path.basename(file_path)  # 更新当前文件名
        except Exception as e:
            messagebox.showerror("错误", f"读取文件时出错: {e}")
            status_str_ver.set('读取文件失败')
    else:
        try:
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read())
                encoding = result['encoding']
            with open(file_path, mode='r', newline='', encoding=encoding) as file:
                reader = csv.reader(file)
                next(reader)  # 跳过原始表头
                clear_treeview()
                for row in reader:
                    item_name, quantity = row[0], row[1]
                    boxes, groups, pieces = calculate_boxes_and_groups(int(quantity))
                    treeview.insert('', 'end', values=[item_name, quantity, boxes, groups, pieces, "未完成"], tags=('not_completed',))
            status_str_ver.set(f'文件成功打开 {file_path}')
            modified = False  # 打开文件后设置为False
            current_filename = os.path.basename(file_path)  # 更新当前文件名
        except Exception as e:
            messagebox.showerror("错误", f"读取文件时出错: {e}")
            status_str_ver.set('读取文件失败')


def open_settings():
    global show_background_color
    settings_window = tk.Toplevel(root)
    settings_window.title('设置')
    settings_window.geometry('300x200')

    show_background_color_var = tk.BooleanVar(value=show_background_color)

    def save_settings():
        global show_background_color
        show_background_color = show_background_color_var.get()
        update_treeview_background()
        settings_window.destroy()

    tk.Label(settings_window, text='显示背景色').pack(pady=10)
    tk.Checkbutton(settings_window, variable=show_background_color_var).pack()
    tk.Button(settings_window, text='保存', command=save_settings).pack(pady=10)


def update_treeview_background():
    for item in treeview.get_children():
        completion_status = treeview.item(item, 'values')[5]
        if show_background_color:
            tag = 'completed' if completion_status == "已完成" else 'not_completed'
        else:
            tag = ''
        treeview.item(item, tags=(tag,))

def fetch_files(base_url):
    response = requests.get(f'{base_url}/files')
    if response.status_code == 200:
        return response.json()
    else:
        messagebox.showerror("错误", "无法获取文件列表")
        return []

def fetch_data(base_url, filename):
    response = requests.get(f'{base_url}/data/{filename}')
    if response.status_code == 200:
        return response.json()
    else:
        messagebox.showerror("错误", "无法获取数据")
        return []

def add_data(item):
    response = requests.post('http://localhost:5000/data', json=item)
    if response.status_code == 201:
        return response.json()
    else:
        messagebox.showerror("错误", "无法添加数据")
        return None

'''
def update_data(base_url, filename):
    url = f'{base_url}/data/{filename}'
    response = requests.put(f'{base_url}/data/{item_id}', json=item)
    if response.status_code == 200:
        return response.json()
    else:
        messagebox.showerror("错误", "无法更新数据")
        return None
'''


def delete_data(item_id):
    response = requests.delete(f'http://localhost:5000/data/{item_id}')
    if response.status_code == 200:
        return True
    else:
        messagebox.showerror("错误", "无法删除数据")
        return False

def update_treeview_background():
    for item in treeview.get_children():
        completion_status = treeview.item(item, 'values')[5]
        if show_background_color:
            tag = 'in_progress' if completion_status == "进行中" else 'completed' if completion_status == "已完成" else 'not_completed'
        else:
            tag = ''
        treeview.item(item, tags=(tag,))

def update_data_on_server(base_url, filename, item_index, new_data):
    global online_mode
    url = f'{base_url}/data/{filename}/{item_index}'
    if online_mode == True:
        response = requests.put(url, json=new_data)
        if response.status_code == 200:
            return True
        else:
            print(f"更新失败，状态码: {response.status_code}, 响应内容: {response.text}")
            messagebox.showerror("错误", f"无法更新数据，状态码: {response.status_code}, 响应内容: {response.text}")
            return False

def initial_load_data():
    # 弹出对话框让用户输入服务器地址
    base_url = simpledialog.askstring("服务器地址", "请输入服务器地址 (例如 http://localhost:5000):", parent=root)
    if base_url:
        load_data(base_url)

def load_data(base_url, filename=None):
    global online_mode, current_filename
    online_mode = True
    if filename is None:
        files = fetch_files(base_url)
        if not files:
            online_mode = False
            return
        # 使用Combobox让用户选择文件
        selected_file = tk.StringVar()
        combobox = ttk.Combobox(root, textvariable=selected_file, values=files)
        combobox.pack(pady=10)
        combobox.set(files[0])  # 默认选中第一个文件

        def on_select():
            filename = selected_file.get()
            if filename in files:
                load_data(base_url, filename)
                combobox.pack_forget()  # 隐藏选择框
                select_button.pack_forget()  # 隐藏按钮
                update_treeview_background()  # 更新背景色
                global check_mode
                check_mode = True
                check_modified_status(base_url)
            else:
                messagebox.showinfo("提示", "文件选择无效")

        select_button = tk.Button(root, text="选择文件", command=on_select)
        select_button.pack(pady=10)
    else:
        data = fetch_data(base_url, filename)
        clear_treeview()
        for item in data:
            treeview.insert('', 'end', values=item)
        update_treeview_background()  # 更新背景色
        current_filename = filename  # 更新当前文件名
        # 绑定右键菜单，传递文件名
        treeview.bind("<Button-3>", lambda event, filename=filename: on_right_click(event, filename, base_url))

def clear_treeview():
    for i in treeview.get_children():
        treeview.delete(i)



def check_modified_status(base_url):
    """查询服务器status.json中的modified值"""
    global check_mode
    if check_mode:
        global online_mode
        if online_mode:
            try:
                response = requests.get(f'{base_url}/api/status')
                print(f'{base_url}/api/status')
                if response.status_code == 200:
                    status = response.json()
                    if status.get('modified', False) and current_filename:
                        # 直接调用load_data，并传递base_url和当前文件名
                        load_data(base_url, current_filename)
            except Exception as e:
                print(f"查询modified状态时出错: {e}")
            finally:
                # 3秒后再次查询
                threading.Timer(3, check_modified_status, args=(base_url,)).start()

root = tk.Tk()
root.title('原理图材料列表查看器')
root.geometry('800x547')

modified = False
show_background_color = True  # 默认显示背景色
online_mode = False
check_mode = False

menu = tk.Menu(root, tearoff=False)
file_menu = tk.Menu(menu, tearoff=False)
file_menu.add_command(label='打开', command=open_file)
file_menu.add_command(label='打开上一次的文件', command=lambda: open_last_file(load_config()[0]))
file_menu.add_command(label='保存', command=save_file)
file_menu.add_command(label='退出', command=on_closing)
menu.add_cascade(label='文件', menu=file_menu)

connect_menu = tk.Menu(menu, tearoff=False)
connect_menu.add_command(label='新建连接', command=initial_load_data)
menu.add_cascade(label='连接', menu=connect_menu)

settings_menu = tk.Menu(menu, tearoff=False)
settings_menu.add_command(label='设置', command=open_settings)
menu.add_cascade(label='设置', menu=settings_menu)

about_menu = tk.Menu(menu, tearoff=False)
about_menu.add_command(label='关于', command=about)
menu.add_cascade(label='关于', menu=about_menu)

status_str_ver = tk.StringVar()
status_str_ver.set('请打开一个文件')
status_label = tk.Label(root, textvariable=status_str_ver, bd=1, relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)

# 创建Treeview控件
treeview = ttk.Treeview(root, columns=("物品名", "数量", "盒数", "组数", "个数", "是否完成"), show='headings')
treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# 创建Scrollbar控件
scrollbar = ttk.Scrollbar(treeview, orient=tk.VERTICAL, command=treeview.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# 将Treeview与Scrollbar关联
treeview.configure(yscrollcommand=scrollbar.set)

# 初始化表头
custom_headers = ["物品名", "数量", "盒数", "组数", "个数", "是否完成"]
for header in custom_headers:
    treeview.heading(header, text=header)
    treeview.column(header, width=100, stretch=True)  # 列宽自适应


# 定义标签样式
treeview.tag_configure('completed', background='#a9d08e')  # 绿色
treeview.tag_configure('not_completed', background='#ff8181')  # 红色
treeview.tag_configure('in_progress', background='#ffd299')  # 橙色

# 创建右键菜单
right_click_menu = tk.Menu(treeview, tearoff=False)
right_click_menu.add_command(label="修改状态为已完成", command=mark_as_completed, state="disabled")
right_click_menu.add_command(label="修改状态为进行中", command=mark_as_completed, state="disabled")
right_click_menu.add_command(label="修改状态为未完成", command=mark_as_completed, state="disabled")

# 更新treeview背景色
update_treeview_background()

# 绑定右键点击事件
treeview.bind("<Button-3>", on_right_click)

# 绑定窗口关闭事件
root.protocol("WM_DELETE_WINDOW", on_closing)

root.config(menu=menu)
root.mainloop()