import ezdxf
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, Rectangle
from matplotlib.text import Text
from matplotlib.lines import Line2D
from matplotlib.widgets import TextBox
from matplotlib.widgets import Button
from matplotlib.patches import FancyBboxPatch
from shapely.geometry import Polygon, Point
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog
import csv
import math
import numpy as np
import sys
import os
import time
from matplotlib.animation import FuncAnimation
import matplotlib
matplotlib.use('QT5Agg')  # 使用Tkinter后端，性能更好



plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Zen Hei']  # 中文字体列表
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 全局变量
dxf_file = "地图.dxf"
csv_path = "树点位.csv"
offsets = [44, 64]  # 十字障碍物通过点位
obstacles = []
interactive_points = []  # 存储交互式点位
interactive_lines = []  # 存储连线
current_point_id = 1  # 当前点位ID计数器
selected_point = None  # 当前选中的点位
edit_mode = "add"  # 当前操作模式：add/edit/connect/disconnect/delete
temp_line = None  # 临时连线对象
last_click_time = 0  # 记录上次点击的时间
global_manager = None  # 新增全局管理器

# 在全局变量部分添加以下内容
show_aux_circles = False  # 辅助圆显示状态
ax_aux = None  # 预先声明
aux_circle1 = None       # 第一个辅助圆对象
aux_circle2 = None       # 第二个辅助圆对象
aux_radius1 = 18.75         # 第一个圆的半径
aux_radius2 = 21         # 第二个圆的半径

show_crosshair = False  # 十字虚线显示状态
crosshair_h = None      # 水平线对象
crosshair_v = None      # 垂直线对象
last_update_time = 0  # 新增
min_update_interval = 0.02  # 最小更新间隔（秒）




#===========================================1\按钮管理器==============================================================#
class ButtonManager:
    def __init__(self):
        self.mode = "add"  # 初始模式：添加点位
        self.buttons = {}

    def set_active(self, btn_name):
        global edit_mode
        edit_mode = btn_name  # 确保全局状态更新

        for name, btn_data in self.buttons.items():
            is_active = (name == btn_name)
            btn_data['background'].set_facecolor('#4CAF50' if is_active else '#E0E0E0')
            btn_data['text'].set_color('white' if is_active else 'black')
            btn_data['active'] = is_active
        self.mode = btn_name
        plt.draw()

    def create_capsule_button(self, ax, label, active_color='#4CAF50', inactive_color='#E0E0E0'):
        """创建胶囊样式按钮"""
        # 绘制圆角矩形背景
        capsule = FancyBboxPatch(
            (0, 0), 1, 1,
            boxstyle="round,pad=0.2,rounding_size=0.3",
            facecolor=inactive_color,
            edgecolor='none',
            transform=ax.transAxes
        )
        ax.add_patch(capsule)

        # 添加文本标签
        text = ax.text(0.5, 0.5, label,
                       ha='center', va='center',
                       transform=ax.transAxes,
                       fontsize=10,
                       weight='bold')
        return {'background': capsule, 'text': text, 'active': False}

    # 在ButtonManager类中添加辅助圆状态切换方法
    def toggle_aux_circles(self,ax):
        global show_aux_circles
        show_aux_circles = not show_aux_circles
        self.update_button_text()
        update_aux_circles(ax)  # 关键：状态切换时更新辅助圆
        plt.draw()

    def update_button_text(self):
        btn_data = self.buttons['aux_circles']
        if show_aux_circles:
            btn_data['text'].set_text('隐藏辅助圆')
            btn_data['background'].set_facecolor('#0ebeff')  # 激活状态颜色（绿色）
            btn_data['text'].set_color('white')  # 文字颜色设为白色
        else:
            btn_data['text'].set_text('显示辅助圆')
            btn_data['background'].set_facecolor('#ee5a5a')  # 默认状态颜色（浅灰）
            btn_data['text'].set_color('black')  # 文字颜色设为黑色

    def toggle_crosshair(self, ax):
        global show_crosshair
        show_crosshair = not show_crosshair
        self.update_crosshair_button_text()

        if crosshair_h and crosshair_v:
            crosshair_h.set_visible(show_crosshair)
            crosshair_v.set_visible(show_crosshair)
            # 强制刷新画布
            ax.figure.canvas.draw_idle()
        plt.draw()

    def update_crosshair_button_text(self):
        btn_data = self.buttons['crosshair']
        if show_crosshair:
            btn_data['text'].set_text('隐藏十字线')
            btn_data['background'].set_facecolor('#0ebeff')  # 激活状态颜色（绿色）
            btn_data['text'].set_color('white')  # 文字颜色设为白色
        else:
            btn_data['text'].set_text('显示十字线')
            btn_data['background'].set_facecolor('#ee5a5a')  # 默认状态颜色（浅灰）
            btn_data['text'].set_color('black')  # 文字颜色设为黑色




#===========================================2\数据记录器、按钮管理==============================================================#
class InteractivePoint:
    def __init__(self, x, y, point_id, name=None, angle=999):
        self.x = x
        self.y = y
        self.point_id = point_id
        self.name = name if name else str(point_id)
        self.angle = angle
        self.connections = []  # 存储连接的其他点的ID
        self.point_artist = None  # matplotlib点对象
        self.text_artist = None  # matplotlib文本对象

    def draw(self, ax):
        # 绘制点（统一坐标系）
        self.point_artist = ax.scatter(
            self.x, self.y,  # 修改为(x,y)
            color='#a1c4fd', s=50, marker='o',
            edgecolors='white', zorder=10, picker=5
        )

        # 绘制标签（统一坐标系）
        label = f"{self.point_id}:{self.name}"
        self.text_artist = ax.text(
            self.x, self.y + 5, label,  # 修改为(x,y)
            fontsize=12, color='#ffffff', ha='center', va='bottom',
            bbox=dict(facecolor='black', alpha=0.7, boxstyle='round,pad=0.3')
        )

    def update_position(self, x, y):
        # 更新位置（统一坐标系）
        self.x = x
        self.y = y
        self.point_artist.set_offsets([(x, y)])  # 修改为(x,y)
        self.text_artist.set_position((x, y + 5))

    def update_name(self, name):
        """更新点位名称"""
        self.name = name
        if self.text_artist:
            label = f"{self.point_id}:{self.name}"
            self.text_artist.set_text(label)

    def add_connection(self, target_id):
        """添加连接"""
        if target_id not in self.connections and target_id != self.point_id:
            self.connections.append(target_id)

    def remove_connection(self, target_id):
        """移除连接"""
        if target_id in self.connections:
            self.connections.remove(target_id)

    def remove_from_plot(self, ax):
        """从图形中完全移除点"""
        if self.point_artist and self.point_artist in ax.collections:
            self.point_artist.remove()
        if self.text_artist and self.text_artist in ax.texts:
            self.text_artist.remove()
        self.point_artist = None
        self.text_artist = None

# ----------------------------------------------3\主程序绘图---------------------------------------------------#
def read_and_visualize_dxf(file_path):
    """读取DXF文件并可视化实体"""
    global obstacles, interactive_points, interactive_lines, global_manager

    try:
        # 读取DXF文件
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()

        # 创建绘图对象
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.set_title("交互式DXF地图 | 作者：Azitide | 版本：2025-7-02",fontsize=10)
        ax.set_aspect("equal")

        global key_press_cid
        key_press_cid = fig.canvas.mpl_connect('key_press_event', lambda event: on_key(event, ax))

        # 存储不同实体的绘图对象
        lines, circles, splines = [], [], []

        # 遍历所有实体
        for entity in msp:
            entity_type = entity.dxftype()

            # 处理直线
            if entity_type == 'LINE':
                start, end = entity.dxf.start, entity.dxf.end
                lines.append([(start[1], start[0]), (end[1], end[0])])

            # 处理圆
            elif entity_type == 'CIRCLE':
                center = (entity.dxf.center.x, entity.dxf.center.y)
                radius = entity.dxf.radius
                circles.append(plt.Circle(center, radius, fill=False, color='blue'))

            # 处理样条曲线
            elif entity_type == 'SPLINE' and hasattr(entity, 'control_points'):
                control_points = [cp[:2] for cp in entity.control_points]
                spline_points = list(entity.flattening(distance=0.01))
                x = [p.x for p in spline_points]
                y = [p.y for p in spline_points]
                splines.append((x, y))
        # 绘制所有实体
        # 直线
        for line in lines:
            x_vals = [line[0][0], line[1][0]]
            y_vals = [line[0][1], line[1][1]]
            ax.plot(y_vals, x_vals, 'k-', linewidth=2)
        # 圆
        circle_collection = PatchCollection(circles, match_original=True)
        ax.add_collection(circle_collection)

        # 样条曲线
        for x, y in splines:
            ax.plot(y, x, 'g-', linewidth=2)

        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)
        plt.xlabel("Y Coordinate")
        plt.ylabel("X Coordinate")

        create_crosshair(ax)  # 移动到这里

        # 处理CSV文件中的障碍物
        if csv_path and os.path.exists(csv_path):
            obstacles = read_cross_obstacles_from_csv(csv_path)
            for obstacle in obstacles:
                obstacle.draw(ax)

        # 绘制交互式点位和连线
        redraw_interactive_elements(ax)

        # 绑定事件处理函数
        fig.canvas.mpl_connect('button_press_event',
                               lambda event: on_click(event, ax, button_axes_list))
        fig.canvas.mpl_connect('key_press_event', lambda event: on_key(event, ax))
        fig.canvas.mpl_connect('pick_event', on_pick)

        plt.tight_layout()

        # 添加按钮控制面板
        manager = ButtonManager()
        global_manager = manager
       # plt.subplots_adjust(,bottom=0.15)
        fig.subplots_adjust(left=0.08, right=0.8, top=0.91, bottom=0.1)
        # 调整按钮位置避免重叠
        button_specs = [
            ('add', '添加点位', [0.84, 0.8, 0.1, 0.06]),
            ('edit', '移动点位', [0.84, 0.7, 0.1, 0.06]),
            ('connect', '连接点位', [0.84, 0.6, 0.1, 0.06]),
            ('disconnect', '删除线段', [0.84, 0.5, 0.1, 0.06]),  # 新增断开连接按钮
            ('delete', '删除点位', [0.84, 0.4, 0.1, 0.06]),
            ('rename', '修改地名', [0.84, 0.3, 0.1, 0.06]),

            ('crosshair', '显示十字线', [0.84, 0.23, 0.1, 0.04]),  # 新增按钮
            ('aux_circles', '显示辅助圆', [0.84, 0.19, 0.1, 0.04]),# 新增辅助圆按钮

            ('import_csv', '导入点位', [0.84, 0.12, 0.1, 0.04]),  # 新增导入按钮
            ('export_csv', '导出点位', [0.84, 0.08, 0.1, 0.04])  # 新增导出按钮
        ]

        ax_aux = None  # 预先声明变量
        button_axes_list = []
        for mode, label, pos in button_specs:
            ax_btn = plt.axes(pos)
            btn_data = manager.create_capsule_button(ax_btn, label)
            manager.buttons[mode] = btn_data

            # 通用按钮绑定
            if mode != 'aux_circles':
                ax_btn.button = Button(ax_btn, '')
                ax_btn.button.on_clicked(lambda event, m=mode: button_click_handler(event, m))
            else:  # 特殊处理辅助圆按钮
                ax_aux = ax_btn
                ax_aux.button = Button(ax_aux, '')

            button_axes_list.append(ax_btn)

        # 单独绑定辅助圆事件
        if ax_aux:
            ax_aux.button.on_clicked(lambda event: manager.toggle_aux_circles(ax))
        fig.canvas.mpl_connect('motion_notify_event', lambda event: on_mouse_move(event, ax))



        def button_click_handler(event, mode):
            global edit_mode
            if mode == 'export_csv':
                file_path = export_points_to_csv()
                if file_path:
                    update_status(ax, f"点位数据已导出到: {file_path}")
                else:
                    update_status(ax, "导出已取消")
            elif mode == 'import_csv':
                count = import_points_from_csv(ax)
                if count > 0:
                    update_status(ax, f"成功导入 {count} 个点位数据")
                else:
                    update_status(ax, "导入已取消或失败")
            elif mode == 'crosshair':  # 特殊处理十字线按钮
                manager.toggle_crosshair(ax)
            else:
                edit_mode = mode
                manager.set_active(mode)
                print(f"切换到 {mode} 模式")
                update_status(ax, f"模式: {mode}")

        # 创建胶囊按钮
        button_axes_list = []
        for mode, label, pos in button_specs:
            ax_btn = plt.axes(pos)
            btn_data = manager.create_capsule_button(ax_btn, label)
            manager.buttons[mode] = btn_data

            # 只保留一次绑定
            ax_btn.button = Button(ax_btn, '')
            ax_btn.button.on_clicked(lambda event, m=mode: button_click_handler(event, m))
            button_axes_list.append(ax_btn)

        # 统一绑定地图点击事件（只绑定一次）
        fig.canvas.mpl_connect('button_press_event',
                               lambda event: on_click(event, ax, button_axes_list))

        manager.set_active('add')
        plt.show()

    except Exception as e:
        print(f"Error: {e}")

#-----------------------------------------------------------------------------------------------------------//
def redraw_interactive_elements(ax):
    global interactive_points, interactive_lines

    if hasattr(ax, '_event_listeners'):
        for cid in ax._event_listeners.get('motion_notify_event', []):
            ax.figure.canvas.mpl_disconnect(cid)

    # 1. 清除所有旧连线（修复对象引用问题）
    # 清除旧连线（确保彻底移除）
    for line in interactive_lines:
        for artist in line['artist']:
            if artist in ax.lines:
                artist.remove()
    #interactive_lines.clear()  # 清空连线列表

    # 2. 清除所有旧点位
    for point in interactive_points:
        # 使用新增的remove_from_plot方法
        point.remove_from_plot(ax)

    # 3. 重新绘制所有点位
    for point in interactive_points:
        point.draw(ax)

    # 4. 绘制连线（修复对象存储方式）
    for point in interactive_points:
        for target_id in point.connections:
            target = next((p for p in interactive_points if p.point_id == target_id), None)
            if target:
                # 存储单个Line2D对象而非列表
                line = ax.plot(
                    [point.x, target.x], [point.y, target.y],
                    'b-', linewidth=1, alpha=0.3, linestyle='dashed'
                )
                interactive_lines.append({
                    'start': point.point_id,
                    'end': target.point_id,
                    'artist': line  # 直接存储Line2D对象列表
                })
        # 更新全局连线列表
    # 5. 增强画布刷新机制
    ax.figure.canvas.draw_idle()
    plt.pause(0.01)  # 确保UI完全刷新
    ax._event_listeners = {'motion_notify_event': [
        ax.figure.canvas.mpl_connect('motion_notify_event',
                                     lambda e: on_mouse_move(e, ax))
    ]}


#+++++++++++++++++++++++++++++++++++++++++++++++++++按键事件处理++++++++++++++++++++++++++++++++++++++++++++++++//
def on_click(event, ax, button_axes):
    # 1. 检查是否在按钮区域
    if any(event.inaxes == btn_ax for btn_ax in button_axes):
        return

    # 2. 防抖检查
    global last_click_time
    current_time = time.time()
    if current_time - last_click_time < 0.3:
        return
    last_click_time = current_time

    # 3. 区域限制检查
    if not (0 <= event.xdata <= 400 and 0 <= event.ydata <= 400):
        update_status(ax, "错误：点位必须在400×400区域内！")
        return

    """处理鼠标点击事件"""
    global interactive_points, current_point_id, selected_point, edit_mode, temp_line
    # 获取坐标（使用统一坐标系）
    x, y = event.xdata, event.ydata

    if edit_mode == "add":
        # 添加新点位
        point = InteractivePoint(x, y, current_point_id)
        interactive_points.append(point)
        current_point_id += 1
        redraw_interactive_elements(ax)
        print(f"添加点位: ID={point.point_id}, 位置=({x:.2f}, {y:.2f})")

    elif edit_mode == "connect" and selected_point:
        # 寻找点击位置附近的点位
        clicked_point = None
        min_dist = float('inf')

        for point in interactive_points:
            dist = math.sqrt((point.x - x) ** 2 + (point.y - y) ** 2)
            if dist < min_dist and dist < 10:  # 10像素阈值
                min_dist = dist
                clicked_point = point

        if clicked_point and clicked_point != selected_point:
            # 添加双向连接
            selected_point.add_connection(clicked_point.point_id)
            clicked_point.add_connection(selected_point.point_id)
            print(f"连接点位: {selected_point.point_id} -> {clicked_point.point_id}")
            selected_point = None
            redraw_interactive_elements(ax)

    elif edit_mode == "edit" and selected_point:
        # 更新选中点位的位置
        selected_point.update_position(x, y)
        print(f"移动点位: ID={selected_point.point_id} 到位置=({x:.2f}, {y:.2f})")
        selected_point = None
        redraw_interactive_elements(ax)

    elif edit_mode == "delete":
        # 寻找点击位置附近的点位
        clicked_point = None
        min_dist = float('inf')

        for point in interactive_points:
            dist = math.sqrt((point.x - x) ** 2 + (point.y - y) ** 2)
            if dist < min_dist and dist < 10:  # 10像素阈值
                min_dist = dist
                clicked_point = point

        if clicked_point:
            point_id = clicked_point.point_id

            # 0. 先移除图形对象（立即生效）
            clicked_point.remove_from_plot(ax)

            # 1. 移除其他点对该点的连接引用
            for point in interactive_points:
                if point_id in point.connections:
                    point.connections.remove(point_id)

            # 2. 完全移除点位对象
            interactive_points = [p for p in interactive_points if p.point_id != point_id]

            # 3. 增强刷新机制
            redraw_interactive_elements(ax)
            ax.figure.canvas.flush_events()  # 强制处理所有事件
            plt.draw()  # 立即重绘

            print(f"删除点位: ID={point_id}")
            update_status(ax, f"已删除点位: ID={point_id}")

    elif edit_mode == "rename":
        if not selected_point:
            update_status(ax, "错误：请先选择一个点位！")
            return
        # 寻找点击位置附近的点位
        clicked_point = None
        min_dist = float('inf')
        for point in interactive_points:
            dist = math.sqrt((point.x - x) ** 2 + (point.y - y) ** 2)
            if dist < min_dist and dist < 10:
                min_dist = dist
                clicked_point = point
        if clicked_point:
            rename_point(ax, clicked_point)

    elif edit_mode == "disconnect":
        # 寻找点击位置附近的连线
        min_dist = float('inf')
        target_line = None

        for line_data in interactive_lines.copy():  # 使用副本避免遍历时修改
            # 获取连线起点和终点
            start_point = next((p for p in interactive_points if p.point_id == line_data['start']), None)
            end_point = next((p for p in interactive_points if p.point_id == line_data['end']), None)

            if start_point and end_point:
                # 计算点到线段的最短距离
                dist = point_to_line_distance((x, y),
                                              (start_point.x, start_point.y),
                                              (end_point.x, end_point.y))
                if dist < min_dist and dist < 10:  # 10像素阈值
                    min_dist = dist
                    target_line = line_data

        if target_line:
            for artist in target_line['artist']:
                if artist in ax.lines:
                    artist.remove()  # 从画布移除图形
            ax.figure.canvas.draw_idle()  # 立即刷新画布
            # 修改3：更新点对象的连接关系
            start_id = target_line['start']
            end_id = target_line['end']

            if start_point := next((p for p in interactive_points if p.point_id == start_id), None):
                if end_id in start_point.connections:
                    start_point.connections.remove(end_id)
            if end_point := next((p for p in interactive_points if p.point_id == end_id), None):
                if start_id in end_point.connections:
                    end_point.connections.remove(start_id)

            # 再移除数据对象
            interactive_lines.remove(target_line)

            # 修改5：强制重绘界面
            redraw_interactive_elements(ax)

def on_key(event, ax):
    """处理键盘事件"""
    global edit_mode, selected_point, global_manager

    global is_renaming
    if is_renaming:
        return  # 重名期间忽略所有快捷键

    if event.key == 'ctrl+a' or event.key == 'ctrl+A':
        edit_mode = "add"
        selected_point = None
        print("切换到添加模式: 点击地图添加点位")
        update_status(ax, "模式: 添加点位 (A)")

    elif event.key == 'ctrl+e' or event.key == 'ctrl+E':
        edit_mode = "edit"
        print("切换到编辑模式: 选择点位后点击新位置移动")
        update_status(ax, "模式: 编辑点位 (E) - 先选择点位，再点击新位置")

    elif event.key == 'ctrl+c' or event.key == 'ctrl+C':
        edit_mode = "connect"
        selected_point = None
        print("切换到连接模式: 先选择起点，再选择终点")
        update_status(ax, "模式: 连接点位 (C) - 先选择起点，再选择终点")

    elif event.key == 'ctrl+x' or event.key == 'ctrl+X':  # 断开连接快捷键
        edit_mode = "disconnect"
        if global_manager:
            global_manager.set_active('disconnect')
        print("切换到断开连接模式: 点击要断开的连线")
        update_status(ax, "模式: 断开连接 (X) - 点击要断开的连线")

    elif event.key == 'ctrl+d' or event.key == 'ctrl+D':
        edit_mode = "delete"
        if global_manager:  # 添加空值检查
            global_manager.set_active('delete')
        print("切换到删除模式: 点击要删除的点位")
        update_status(ax, "模式: 删除点位 (D) - 点击要删除的点位")

    elif event.key == 'ctrl+s' or event.key == 'ctrl+S':
        # 保存点位数据到文件
        save_points_to_file()
        print("点位数据已保存到points_data.txt")
        update_status(ax, "点位数据已保存到points_data.txt")

    elif event.key == 'ctrl+n' or event.key == 'ctrl+N' or event.key == 'ctrl+r' or event.key == 'ctrl+R':
        if selected_point:
            rename_point(ax, selected_point)
        else:
            update_status(ax, "错误：请先选择一个点位！")

    elif event.key == 'ctrl+e' or event.key == 'ctrl+E':  # 导出快捷键
        filename = export_points_to_csv()
        update_status(ax, f"点位数据已导出到 {filename}")

    elif event.key == 'ctrl+i' or event.key == 'ctrl+I':  # 导入快捷键
        count = import_points_from_csv(ax)
        update_status(ax, f"成功导入 {count} 个点位数据")

    elif event.key == 'ctrl+h' or event.key == 'ctrl+H':  # 十字线快捷键
        if global_manager:
            global_manager.toggle_crosshair(ax)
        print("切换十字线显示状态")
        update_status(ax, f"十字线: {'显示' if show_crosshair else '隐藏'}")
def on_pick(event):
    """处理点位选择事件"""
    global selected_point, edit_mode
    if event.mouseevent.dblclick:  # 双击选择
        if isinstance(event.artist, plt.Text):
            # 文本选择 - 查找对应的点
            for point in interactive_points:
                if point.text_artist == event.artist:
                    selected_point = point
                    highlight_selected_point()
                    print(f"选中点位: ID={point.point_id}, 名称={point.name}")
                    return

        elif hasattr(event.artist, 'get_offsets'):
            # 点选择
            for point in interactive_points:
                if point.point_artist == event.artist:
                    selected_point = point
                    highlight_selected_point()
                    print(f"选中点位: ID={point.point_id}, 名称={point.name}")
                    return

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


#========================================================功能算法============================================//
def highlight_selected_point():
    """高亮显示选中的点位"""
    global selected_point

    if selected_point and selected_point.point_artist:
        # 重置所有点的颜色
        for point in interactive_points:
            if point.point_artist:
                point.point_artist.set_facecolor('#a1c4fd')

        # 高亮选中的点
        selected_point.point_artist.set_facecolor('#764ba2')
        plt.draw()


def update_status(ax, message):
    """更新状态消息 - 修复位置问题"""
    # 删除旧的状态文本
    for text in ax.texts:
        if text.get_text().startswith("状态:"):
            text.remove()

    # 添加新的状态文本在左下角
    ax.text(
        1.16, 0.97, f"状态: {message}",
        transform=ax.transAxes, ha='center',
        bbox=dict(facecolor='white', alpha=0.8)
    )
    plt.draw()


def save_points_to_file():
    """保存点位数据到文件"""
    with open('points_data.txt', 'w') as f:
        f.write("点位数据\n")
        f.write("ID\tX坐标\tY坐标\t角度\t名称\t连接\n")

        for point in interactive_points:
            connections = ', '.join(map(str, point.connections)) if point.connections else "无"
            f.write(f"{point.point_id}\t{point.x:.2f}\t{point.y:.2f}\t{point.angle}\t{point.name}\t{connections}\n")


def rename_point(ax, point):
    """使用Tkinter输入框替代Matplotlib TextBox"""
    global selected_point, key_press_cid, is_renaming

    # 设置重命名状态
    is_renaming = True
    # 安全断开键盘监听
    if key_press_cid:
        fig = ax.figure
        fig.canvas.mpl_disconnect(key_press_cid)  # 使用存储的ID

    # 创建隐藏根窗口
    root = tk.Tk()
    root.withdraw()
    root.focus_set()
    # 弹出输入对话框
    new_name = simpledialog.askstring("重命名",
                                      f"重命名点位 {point.point_id}:",
                                      initialvalue=point.name,
                                      parent=root)
    # 关键：重建键盘监听
    key_press_cid = fig.canvas.mpl_connect('key_press_event',
                                           lambda event: on_key(event, ax))
    # 处理结果
    if new_name:
        point.update_name(new_name)
        update_status(ax, f"点位 {point.point_id} 名称更新为: {new_name}")
        redraw_interactive_elements(ax)
    else:
        update_status(ax, "重命名已取消")

    # 清除选中状态防止重复触发
    selected_point = None
    highlight_selected_point()
    root.destroy()
    is_renaming = False


def point_to_line_distance(point, line_start, line_end):
    """计算点到线段的最短距离[1,6](@ref)"""
    x, y = point
    x1, y1 = line_start
    x2, y2 = line_end

    # 线段长度的平方
    l2 = (x2 - x1) ** 2 + (y2 - y1) ** 2

    # 如果线段长度为零，直接返回点到端点的距离
    if l2 == 0:
        return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)

    # 计算投影比例
    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2))

    # 计算投影点坐标
    projection_x = x1 + t * (x2 - x1)
    projection_y = y1 + t * (y2 - y1)

    # 返回点到投影点的距离
    return math.sqrt((x - projection_x) ** 2 + (y - projection_y) ** 2)


# 新增辅助圆管理函数
def update_aux_circles(ax):
    global show_aux_circles, aux_circle1, aux_circle2

    if show_aux_circles:
        if not aux_circle1:  # 首次创建
            center_x, center_y = 200, 200
            aux_circle1 = Circle((center_x, center_y), aux_radius1,
                                 color='blue', alpha=0.2, zorder=5)  # 柔和的蓝色
            ax.add_patch(aux_circle1)
        else:
            aux_circle1.set_visible(True)  # 确保可见性设置为True
        if not aux_circle2:
            center_x, center_y = 200, 200
            aux_circle2 = Circle((center_x, center_y), aux_radius2,
                                 color='red', alpha=0.15, zorder=5)  # 柔和的红色
            ax.add_patch(aux_circle2)
        else:
            aux_circle2.set_visible(True)  # 确保可见性设置为True
    else:
        # 隐藏而非移除
        if aux_circle1:
            aux_circle1.set_visible(False)
        if aux_circle2:
            aux_circle2.set_visible(False)

    # 确保画布刷新
    ax.figure.canvas.draw_idle()

 # 添加鼠标移动事件处理
def on_mouse_move(event, ax):
    try:
        global last_update_time
        current_time = time.time()
        # 节流控制：距离上次更新时间小于阈值则跳过
        if current_time - last_update_time < min_update_interval:
            return
        last_update_time = current_time
        if event.inaxes != ax:  # 确保在主绘图区域
            return

        # 获取当前坐标系范围
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()

        # 限制在绘图区域内
        x = max(x_min, min(event.xdata, x_max))
        y = max(y_min, min(event.ydata, y_max))

        # 仅当十字线激活时更新
        if show_crosshair and crosshair_h and crosshair_v:
            crosshair_h.set_ydata([y])
            crosshair_v.set_xdata([x])

            # 更新辅助圆位置
        if show_aux_circles and aux_circle1 and aux_circle2:
            aux_circle1.center = (x, y)
            aux_circle2.center = (x, y)

        ax.figure.canvas.draw_idle()


    except RuntimeError as e:
        if "grab_mouse" in str(e):
            # 处理特定冲突
            print("鼠标事件冲突，尝试释放资源...")
            ax.figure.canvas.mpl_disconnect(ax.figure.canvas._idgrab)
            ax.figure.canvas._idgrab = None
        else:
            raise e


def _update_aux_circles(event, ax):
    """专用辅助圆更新函数"""
    if not event.inaxes == ax:
        return

    x = max(0, min(event.xdata, 400))
    y = max(0, min(event.ydata, 400))

    if aux_circle1:
        aux_circle1.center = (x, y)
    if aux_circle2:
        aux_circle2.center = (x, y)
    ax.figure.canvas.draw()


def _update_crosshair(event, ax):
    """专用十字线更新函数"""
    if not event.inaxes == ax:
        return

    if crosshair_h and crosshair_v:
        crosshair_h.set_ydata([event.ydata])
        crosshair_v.set_xdata([event.xdata])
        ax.figure.canvas.draw_idle()

def read_cross_obstacles_from_csv(csv_path):
    """从CSV文件读取十字障碍物参数"""
    obstacles = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # 跳过首行（标题行）
        for row in reader:
            # 解析格式：x坐标, y坐标, 旋转角度, 编号
            if len(row) >= 4:
                x = float(row[1])
                y = float(row[0])
                angle = float(row[2])
                number = int(row[3])
                obstacles.append(CrossObstacle((x, y), angle, number))
    return obstacles


def export_points_to_csv():
    """导出点位数据到CSV文件（添加文件选择对话框）"""
    root = tk.Tk()
    root.withdraw()

    # 弹出文件保存对话框
    file_path = tk.filedialog.asksaveasfilename(
        title="保存点位数据",
        defaultextension=".csv",
        filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
        initialfile="points_data.csv"
    )

    # 用户取消操作
    if not file_path:
        return None

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'X', 'Y', 'angle', 'name', '依赖关系'])

        for point in interactive_points:
            connections_str = '、'.join(map(str, point.connections)) if point.connections else ""
            writer.writerow([
                point.point_id,
                f"{point.y:.2f}",
                f"{point.x:.2f}",
                point.angle,
                point.name,
                connections_str
            ])
    return file_path  # 返回实际保存路径


# 优化十字线创建函数
def create_crosshair(ax):
    global crosshair_h, crosshair_v
    # 设置初始位置在绘图区域中心（400x400区域）
    crosshair_h = ax.axhline(y=200, color='#606470', linestyle='--',
                            linewidth=1, alpha=0.7, visible=False, zorder=1000)
    crosshair_v = ax.axvline(x=200, color='#606470', linestyle='--',
                            linewidth=1, alpha=0.7, visible=False, zorder=1000)

#====================================================================================================================//

def import_points_from_csv(ax):
    global interactive_points, current_point_id

    # 1. 完全清除现有元素
    clear_interactive_elements(ax)
    current_point_id = 1

    # 2. 文件选择对话框
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="选择点位数据文件",
        filetypes=[("CSV文件", "*.csv")],
        initialfile = "points_data.csv"
    )

    if not file_path:
        return 0

    try:
        # 3. 读取CSV数据
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            id_map = {}

            for row in reader:
                point = InteractivePoint(
                    x=float(row['Y']),
                    y=float(row['X']),
                    point_id=int(row['ID']),
                    name=row['name'],
                    angle=float(row.get('angle', 999))
                )

                # 存储连接关系
                connections = [int(id_str) for id_str in row['依赖关系'].split('、') if id_str]
                point.connections = connections

                interactive_points.append(point)
                id_map[point.point_id] = point

                # 更新ID计数器
                current_point_id = max(current_point_id, point.point_id + 1)

            # 4. 重建双向连接
            for point in interactive_points:
                for target_id in point.connections.copy():
                    if target_id in id_map:
                        id_map[target_id].add_connection(point.point_id)

        # 5. 重绘元素并重建事件系统
        fig = ax.figure
        redraw_interactive_elements(ax)

        # 重新绑定所有事件
        fig.canvas.mpl_connect('button_press_event',
                               lambda e: on_click(e, ax))
        fig.canvas.mpl_connect('key_press_event',
                               lambda e: on_key(e, ax))
        fig.canvas.mpl_connect('pick_event', on_pick)
        fig.canvas.mpl_connect('motion_notify_event',
                               lambda e: on_mouse_move(e, ax))

        return len(interactive_points)

    except Exception as e:
        update_status(ax, f"导入失败: {str(e)}")
        return 0


# 新增函数：完全清除交互元素
def clear_interactive_elements(ax):
    """完全清除所有交互式点位和连线"""
    global interactive_points, interactive_lines

    # 1. 移除所有图形元素
    for point in interactive_points[:]:
        point.remove_from_plot(ax)
    for line in interactive_lines[:]:
        for artist in line['artist']:
            if artist in ax.lines:
                artist.remove()

    # 2. 清空数据结构
    interactive_points.clear()
    interactive_lines.clear()

    # 3. 释放事件监听器
    if hasattr(ax, '_event_listeners'):
        for event_type, cids in ax._event_listeners.items():
            for cid in cids:
                ax.figure.canvas.mpl_disconnect(cid)
        del ax._event_listeners


#*********************************************************十字障碍物生成+++++++++++++++++++++++++++++++++++++++++++++#

class CrossObstacle():
    def __init__(self, params, angle=0, number=None):
        self.params = params  # 原始坐标 (x, y)
        self.angle = angle
        self.number = number
        self.pass_points = self.generate_pass_points()  # 直接生成点位

    def generate_pass_points(self):
        """生成十字障碍物通过点位（无碰撞检测）"""
        x, y = self.params
        all_pass_points = []
        theta = math.radians(self.angle)
        rotation_matrix = np.array([
            [math.cos(theta), -math.sin(theta)],
            [math.sin(theta), math.cos(theta)]
        ])

        for offset in offsets:
            # 四个方向的点位（左、右、上、下）
            points = [
                (x - offset, y), (x + offset, y),
                (x, y - offset), (x, y + offset)
            ]
            # 旋转点位（绕障碍物中心）
            rotated_points = [
                tuple(np.dot(np.array(p) - (x, y), rotation_matrix) + (x, y))
                for p in points
            ]
            all_pass_points.extend(rotated_points)  # 直接添加所有点位
        return all_pass_points

    def draw(self, ax):
        """绘制障碍物及通过点位（使用原始坐标系）"""
        # ---- 关键修改：直接使用原始坐标 (x, y) ----
        x, y = self.params[0], self.params[1]  # 不再交换坐标

        # ---- 1. 绘制障碍物本体（绿色十字）----
        angle_rad = np.deg2rad(self.angle)
        arm_length = 18
        # 水平线端点
        h_start = (
            x + (x - arm_length / 2 - x) * np.cos(angle_rad) - (y - y) * np.sin(angle_rad),
            y + (x - arm_length / 2 - x) * np.sin(angle_rad) + (y - y) * np.cos(angle_rad)
        )
        h_end = (
            x + (x + arm_length / 2 - x) * np.cos(angle_rad) - (y - y) * np.sin(angle_rad),
            y + (x + arm_length / 2 - x) * np.sin(angle_rad) + (y - y) * np.cos(angle_rad)
        )

        # 计算旋转后的垂直线端点
        v_start = (
            x + (x - x) * np.cos(angle_rad) - (y - arm_length / 2 - y) * np.sin(angle_rad),
            y + (x - x) * np.sin(angle_rad) + (y - arm_length / 2 - y) * np.cos(angle_rad)
        )
        v_end = (
            x + (x - x) * np.cos(angle_rad) - (y + arm_length / 2 - y) * np.sin(angle_rad),
            y + (x - x) * np.sin(angle_rad) + (y + arm_length / 2 - y) * np.cos(angle_rad)
        )

        # 直接绘制线段（保持原始坐标）
        ax.plot([h_start[0], h_end[0]], [h_start[1], h_end[1]], color='#112d4e', linewidth=3)
        ax.plot([v_start[0], v_end[0]], [v_start[1], v_end[1]], color='#112d4e', linewidth=3)

        # ---- 2. 绘制通过点位（圆点）----
        for point in self.pass_points:
            # 直接使用原始坐标
            ax.scatter(point[0], point[1], color='#9df3c4', s=10, zorder=50)

        # ---- 3. 添加障碍物编号（字母）----
        if self.number is not None:
            letter = chr(self.number + 64)  # 1->A, 2->B
            # 直接使用原始坐标
            ax.text(x, y, letter, fontsize=18, color='#58de66',
                    ha='center', va='center', fontweight='bold')


def generate_pass_points():
    pass_points = set()
    for obs in obstacles:
        if isinstance(obs, CrossObstacle):
            # 直接使用实例的pass_points属性
            for point in obs.pass_points:
                if not check_collision_with_safety_margin(point, 24) and not is_within_distance(point, pass_points, 10):
                    pass_points.add(point)
    return pass_points


def check_collision_with_safety_margin(point, safety_margin=24):  # 检查是否与障碍物发生碰撞
    print(f"Checking collision for point {point} with safety margin {safety_margin}")
    for obs in obstacles:
        if obs.check_collision(point, point, safety_margin):
            print(f"Collision detected with obstacle {obs.__class__.__name__} at {point}")
            return True
    print(f"No collision detected for point {point}")
    return False


def is_within_distance(point, points, distance):
    for p in points:
        if np.sqrt((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2) <= distance:
            return True
    return False


if __name__ == "__main__":
    read_and_visualize_dxf(dxf_file)
