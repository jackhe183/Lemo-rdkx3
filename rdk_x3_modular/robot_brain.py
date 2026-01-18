#!/usr/bin/env python3
# RDK X3 多模态交互大脑
#
# 通俗理解：
# 这是一个"智能机器人管家"，他能：
# 1. 看到你（通过摄像头）
# 2. 理解你的手势（通过MediaPipe AI模型）
# 3. 听你说话和对你说话（通过音频）
# 4. 根据你的手势做反应（触发对应的动作）
#
# 工作流程：
# 摄像头 -> 画面 -> AI识别手势 -> 触发动作 -> 音频反馈

import time
import math
import numpy as np
import cv2
from drivers import Camera, Audio


class RobotBrain:
    """
    多模态交互大脑

    【比喻】这是一个"智能管家的大脑"：
    - 眼睛：摄像头（看世界）
    - 视觉皮层：MediaPipe AI模型（理解手势）
    - 耳朵和嘴巴：音频模块（听和说）
    - 决策中心：这个类本身（决定做什么）

    手势触发逻辑：
    - 捏合（食指+拇指靠在一起）：播放提示音
    - 张开手掌（5指伸展）：录音2秒

    性能监控：
    - 每30帧输出一次FPS
    - 触发动作有1秒冷却时间（防止重复触发）
    """

    # ========== MediaPipe 手部关键点定义 ==========
    # 【比喻】这是手部的"地图标记"
    # MediaPipe会检测21个手部关键点，这里定义我们要用到的

    WRIST = 0         # 手腕（原点）
    THUMB_TIP = 4     # 拇指尖端
    INDEX_TIP = 8     # 食指指尖
    MIDDLE_TIP = 12   # 中指指尖
    RING_TIP = 16     # 无名指指尖
    PINKY_TIP = 20    # 小指指尖

    # 手指检测用的关键点对
    # 【比喻】判断手指是否伸直，需要比较指尖和关节的距离
    FINGER_INDICES = {
        'thumb': (4, 2),      # 拇指：指尖 vs 指关节
        'index': (8, 6),      # 食指：指尖 vs 第2关节
        'middle': (12, 10),   # 中指：指尖 vs 第2关节
        'ring': (16, 14),     # 无名指：指尖 vs 第2关节
        'pinky': (20, 18),    # 小指：指尖 vs 第2关节
    }

    # ========== 手势识别阈值 ==========
    # 【比喻】判断手势的"标准线"

    PINCH_THRESHOLD = 0.05        # 捏合阈值（距离<0.05算捏合）
                                  # 【比喻】两个指尖距离小于5%算"捏住"
    FINGER_EXTEND_THRESHOLD = 0.05  # 手指伸展阈值
                                  # 【比喻】指尖比关节远5%以上算"伸直"

    # ========== 音频反馈文件 ==========
    BEEP_FILE = "beep.wav"      # 提示音文件
    WELCOME_FILE = "welcome.wav"  # 欢迎音文件

    def __init__(self):
        """
        初始化机器人大脑

        【比喻】机器人大脑"开机"：
        1. 连接眼睛（摄像头）
        2. 连接耳朵和嘴巴（音频）
        3. 加载AI模型（手势识别）
        4. 初始化状态记忆（记录上次触发时间）
        """
        print("[大脑] 正在初始化...")

        # ===== 第1步：硬件驱动 =====
        # 【比喻】连接感官设备

        # 摄像头（眼睛）
        # 【比喻】打开眼睛
        self.cam = Camera()

        # 音频（耳朵和嘴巴）
        # 【比喻】打开耳朵和嘴巴
        self.audio = Audio()

        # ===== 第2步：加载AI模型 =====
        # 【比喻】学习如何理解手势

        try:
            import mediapipe as mp

            # MediaPipe Hands 模型
            # 【比喻】这是一个"手势识别专家"
            self.mp_hands = mp.solutions.hands

            # 创建手部检测器
            # 【比喻】激活手势识别功能
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,    # 视频模式（连续帧，更流畅）
                max_num_hands=1,            # 最多检测1只手（简化处理）
                model_complexity=0,         # 模型复杂度：0=最快（适合嵌入式）
                                            # 【比喻】用"简化版专家"，速度快
                min_detection_confidence=0.5,   # 检测置信度阈值（50%）
                min_tracking_confidence=0.5     # 跟踪置信度阈值（50%）
            )

            # 绘图工具（可选，用于调试时画骨架）
            self.mp_draw = mp.solutions.drawing_utils

        except ImportError:
            raise RuntimeError("未安装mediapipe！请运行: pip install mediapipe")

        # ===== 第3步：状态记忆 =====
        # 【比喻】大脑需要记住一些事情

        self.frame_count = 0         # 已处理帧数（用于计算FPS）
        self.last_log_time = time.time()  # 上次输出日志的时间
        self.last_pinch_time = 0     # 上次触发捏合的时间
        self.last_palm_time = 0      # 上次触发手掌的时间
        self.cooldown = 1.0          # 冷却时间：1秒
                                    # 【比喻】同一动作1秒内只能触发一次
                                    # （防止按住手势时重复触发）

        print("[大脑] 准备就绪。等待手势...")

    def _calculate_distance(self, p1, p2):
        """
        计算两个关键点之间的距离（欧几里得距离）

        【比喻】用尺子量两个点之间有多远

        参数：
            p1, p2: 关键点对象（包含x, y坐标）

        返回：
            float: 距离值（0~1之间，相对于图像尺寸）
        """
        # 【比喻】勾股定理：斜边 = sqrt(横向距离² + 纵向距离²)
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def _is_finger_extended(self, landmarks, finger_name):
        """
        检查手指是否伸直

        【比喻】判断手指是"伸直"还是"弯曲"
        - 方法：比较指尖到手腕的距离 vs 关节到手腕的距离
        - 如果指尖更远，说明手指伸直了

        参数：
            landmarks: 21个关键点的列表
            finger_name: 手指名称（'thumb', 'index', 'middle', 'ring', 'pinky'）

        返回：
            bool: True=伸直，False=弯曲

        示意图：
            手腕 ●────● 关节
                     ╲
                      ● 指尖（伸直：指尖比关节远）
        """
        # 获取关键点索引
        # 【比喻】找到要测量的位置
        tip_idx, pip_idx = self.FINGER_INDICES[finger_name]

        # 获取关键点坐标
        tip = landmarks[tip_idx]      # 指尖
        pip = landmarks[pip_idx]      # 关节
        wrist = landmarks[self.WRIST] # 手腕（原点）

        # 计算距离
        # 【比喻】用尺子量：
        dist_tip = self._calculate_distance(wrist, tip)   # 手腕到指尖
        dist_pip = self._calculate_distance(wrist, pip)   # 手腕到关节

        # 判断是否伸直
        # 【比喻】如果指尖比关节远，说明手指伸直了
        return (dist_tip - dist_pip) > self.FINGER_EXTEND_THRESHOLD

    def _detect_pinch(self, landmarks):
        """
        检测捏合手势

        【比喻】判断拇指和食指是否"捏在一起"
        - 方法：计算拇指和食指指尖的距离
        - 如果距离很小（<0.05），判定为捏合

        参数：
            landmarks: 21个关键点的列表

        返回：
            bool: True=捏合，False=未捏合

        手势示意：
            捏合：👌（拇指和食指指尖接触）
        """
        # 获取关键点
        thumb_tip = landmarks[self.THUMB_TIP]  # 拇指指尖
        index_tip = landmarks[self.INDEX_TIP]  # 食指指尖

        # 计算距离
        # 【比喻】用尺子量两个指尖的距离
        distance = self._calculate_distance(thumb_tip, index_tip)

        # 判断是否捏合
        # 【比喻】距离小于5%（相对于图像宽度）就算"捏住"
        return distance < self.PINCH_THRESHOLD

    def _detect_open_palm(self, landmarks):
        """
        检测张开手掌手势

        【比喻】判断手掌是否"张开"
        - 方法：检查5根手指是否都伸直
        - 如果至少4根手指伸直，判定为张开手掌

        参数：
            landmarks: 21个关键点的列表

        返回：
            bool: True=张开手掌，False=未张开

        手势示意：
            张开：✋（5指都伸直）
            握拳：✊（手指都弯曲）
        """
        # 统计伸直的手指数量
        # 【比喻】数数有几根手指伸直了
        extended_count = sum(
            self._is_finger_extended(landmarks, finger)
            for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']
        )

        # 至少4根手指伸直才算"张开"
        # 【比喻】允许1根手指弯曲（比如小指可能不太直）
        return extended_count >= 4

    def _trigger_pinch_action(self):
        """
        触发捏合手势对应的动作

        【比喻】当你做"OK"手势时，机器人会：
        - 播放提示音（beep.wav 或 welcome.wav）

        冷却机制：
        - 1秒内重复触发无效
        - 【比喻】防止你按住手势时一直响
        """
        # 检查冷却时间
        # 【比喻】看看是不是刚触发过不久
        current_time = time.time()
        if current_time - self.last_pinch_time < self.cooldown:
            return  # 还在冷却中，不触发

        # 记录触发时间
        # 【比喻】记一下这次触发的"时间戳"
        self.last_pinch_time = current_time

        # 执行动作
        # 【比喻】播放提示音
        print("[动作] 检测到捏合手势。播放提示音...")

        try:
            # 先尝试播放 beep.wav
            try:
                self.audio.play(self.BEEP_FILE)
            except:
                # 如果 beep.wav 不存在，尝试 welcome.wav
                # 【比喻】首选文件找不到，用备选
                self.audio.play(self.WELCOME_FILE)
        except Exception as e:
            # 两个文件都不存在，只是提示但不报错
            # 【比喻】找不到音频文件，但继续工作
            print(f"[音频] 播放失败: {e}")

    def _trigger_palm_action(self):
        """
        触发张开手掌手势对应的动作

        【比喻】当你张开手掌时，机器人会：
        - 录音2秒（记录你的声音）
        - 保存为 user.wav

        冷却机制：
        - 1秒内重复触发无效
        - 【比喻】防止你一直张着手导致重复录音
        """
        # 检查冷却时间
        # 【比喻】看看是不是刚触发过不久
        current_time = time.time()
        if current_time - self.last_palm_time < self.cooldown:
            return  # 还在冷却中，不触发

        # 记录触发时间
        # 【比喻】记一下这次触发的"时间戳"
        self.last_palm_time = current_time

        # 执行动作
        # 【比喻】开始录音
        print("[动作] 检测到张开手掌。开始录音...")

        try:
            self.audio.record("user.wav", 2)  # 录2秒
            print("[音频] 录音已保存: user.wav")
        except Exception as e:
            print(f"[音频] 录音失败: {e}")

    def process_frame(self, frame):
        """
        处理单帧图像：检测手势并触发动作

        【比喻】大脑的"思考过程"：
        1. 看到画面（摄像头输入）
        2. 理解手势（AI识别）
        3. 决定做什么（触发动作）
        4. 记录性能（FPS统计）

        参数：
            frame: BGR格式的图像（从摄像头获取）

        返回：
            frame: 处理后的图像（可选，用于调试显示）
        """
        # ===== 第1步：图像格式转换 =====
        # 【比喻】把画面翻译成AI能看懂的语言
        # MediaPipe需要RGB格式，摄像头给的是BGR格式
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ===== 第2步：AI识别 =====
        # 【比喻】让AI专家分析画面，找手势
        results = self.hands.process(frame_rgb)

        # ===== 第3步：手势检测和动作触发 =====
        if results.multi_hand_landmarks:
            # 【比喻】AI找到了手！
            for hand_landmarks in results.multi_hand_landmarks:
                # 检测捏合手势
                # 【比喻】是不是在做"OK"手势？
                if self._detect_pinch(hand_landmarks.landmark):
                    self._trigger_pinch_action()  # 播放提示音

                # 检测张开手掌手势（用 elif 保证同时只触发一个）
                # 【比喻】不是"OK"的话，是不是张开手掌？
                elif self._detect_open_palm(hand_landmarks.landmark):
                    self._trigger_palm_action()  # 录音

        # ===== 第4步：性能统计 =====
        # 【比喻】大脑每30帧输出一次"工作报告"

        # 计数帧数
        self.frame_count += 1

        # 每30帧输出一次FPS
        if self.frame_count % 30 == 0:
            # 计算FPS（每秒帧数）
            # 【比喻】算算大脑处理速度有多快
            elapsed = time.time() - self.last_log_time
            fps = 30 / elapsed  # 30帧花了多少秒

            print(f"[性能] FPS: {fps:.1f}")
            self.last_log_time = time.time()

        return frame

    def run(self, duration=None):
        """
        主循环：持续获取画面、识别手势、触发动作

        【比喻】机器人的"日常工作"：
        - 一直盯着摄像头看（获取画面）
        - 不断分析手势（AI识别）
        - 遇到特定手势就做反应（触发动作）
        - 定期汇报工作状态（性能监控）

        参数：
            duration: 运行时长（秒）
                     None = 无限循环（直到手动停止）
        """
        # 记录开始时间
        # 【比喻】上班打卡
        start_time = time.time()
        print("[大脑] 开始主循环...")

        try:
            # ===== 无限循环 =====
            # 【比喻】机器人的日常工作
            while True:
                # 检查是否到达运行时长
                # 【比喻】看看是不是下班时间了
                if duration and (time.time() - start_time) > duration:
                    break  # 到时间了，下班！

                # ===== 获取画面 =====
                # 【比喻】看一眼摄像头
                frame = self.cam.get_frame_bgr()

                if frame is None:
                    # 画面获取失败，跳过这一帧
                    # 【比喻】眼睛眨了一下，没看清，继续
                    continue

                # ===== 处理画面 =====
                # 【比喻】分析画面，理解手势，触发动作
                self.process_frame(frame)

                # ===== 显示画面（可选）=====
                # 【比喻】在屏幕上显示看到的东西
                # 注释掉了，因为RDK X3可能没有屏幕
                # 如果需要调试，可以取消注释
                # cv2.imshow('Robot Brain', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break  # 按q键退出

        except KeyboardInterrupt:
            # 用户按Ctrl+C停止
            # 【比喻】老板喊停
            print("\n[大脑] 用户中断")

        finally:
            # ===== 清理工作 =====
            # 【比喻】下班前的收尾工作
            print(f"[大脑] 关闭中。已处理 {self.frame_count} 帧。")
            self.cam.close()  # 关闭摄像头


def main():
    """
    程序入口

    【比喻】整个机器人的"启动按钮"
    """
    # 打印欢迎信息
    print("=" * 50)
    print("RDK X3 多模态交互大脑")
    print("=" * 50)

    # 创建大脑实例
    # 【比喻】唤醒机器人
    brain = RobotBrain()

    # 运行主循环（60秒）
    # 【比喻】让机器人工作1分钟
    # 可以改成 None 让它一直运行，直到按Ctrl+C停止
    brain.run(duration=60)


# ========== 程序入口 ==========
# 【比喻】这是插电源的地方
if __name__ == "__main__":
    main()
