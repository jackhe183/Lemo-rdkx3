#!/usr/bin/env python3
# RDK X3 摄像头驱动
#
# 通俗理解：
# 想象摄像头就像一个"快递员"，我们需要：
# 1. "招聘"这个快递员（初始化摄像头）
# 2. 告诉他怎么送快递（设置分辨率、帧率等）
# 3. 接收他送来的包裹（获取图像数据）
# 4. 解雇时给他办好离职手续（释放资源）
#
# 支持两种"快递员"：
# - MIPI：官方专用快递员（速度快，但需要专用通道）
# - v4l2：通用快递员（兼容性好，但速度稍慢）

import numpy as np
import cv2
import subprocess
import sys


class Camera:
    """
    RDK X3 摄像头驱动类

    【比喻】这是一个"摄像头管理公司"的老板
    - 他知道怎么招聘和管理不同类型的快递员（后端）
    - 他能确保快递员离职时清理干净（上下文管理器）
    - 他能把快递员送来的包裹翻译成我们能看懂的样子（图像格式转换）
    """

    # ========== 硬件配置常量 ==========
    # 这些是"快递员"的工作规范，不能随意修改

    CAM_IDX = 0      # 摄像头编号：如果有多个摄像头，这是第0号
    FPS = 30         # 帧率：每秒送30个包裹（画面）
    WIDTH = 320      # 图像宽度：320像素（像横向有320个小格子）
    HEIGHT = 240     # 图像高度：240像素（像纵向有240个小格子）

    def __init__(self, backend='auto'):
        """
        初始化摄像头

        【比喻】老板准备招聘快递员

        参数说明：
            backend: 想要招聘哪种快递员
                - 'auto': 自动选择（先试MIPI，不行就v4l2）【推荐】
                - 'mipi': 只要MIPI专用快递员
                - 'v4l2': 只要通用快递员

        使用示例：
            cam = Camera()              # 自动选择
            cam = Camera(backend='mipi') # 强制使用MIPI
        """
        # 这些是"员工档案"，一开始都是空的
        self.cam = None       # 具体的快递员对象（还没招聘）
        self.backend = None   # 记录最后用的是哪种快递员

        # 开始招聘流程
        self._open(backend)

    def _open(self, backend='auto'):
        """
        打开摄像头（内部方法）

        【比喻】执行招聘流程：
        1. 先把占着位置的旧员工赶走（清理占用进程）
        2. 根据要求招聘新员工（尝试不同后端）
        """

        # ===== 第1步：清理现场 =====
        # 【比喻】招聘新员工前，先把占着位置的人赶走

        # 停止桌面服务（lightdm）
        # 【比喻】桌面服务像个"霸道总裁"，它会占着摄像头资源
        # 我们需要先让它下台，才能用摄像头
        subprocess.run(["sudo", "systemctl", "stop", "lightdm"],
                      stderr=subprocess.DEVNULL)  # 错误信息不显示（静默模式）

        # 杀掉所有占用摄像头的进程
        # 【比喻】有些人离职了但没办手续，还占着工位
        # 我们强制把他们赶走
        subprocess.run(["sudo", "pkill", "-9", "-f", "mipi"],
                      stderr=subprocess.DEVNULL)  # -9表示强制杀死，不留情面
        subprocess.run(["sudo", "pkill", "-9", "-f", "cam"],
                      stderr=subprocess.DEVNULL)

        # ===== 第2步：招聘新员工 =====

        if backend == 'auto':
            # 【比喻】自动模式：先找最好的，不行再找备选

            # 先尝试MIPI（速度快，官方推荐）
            if self._try_open_mipi():
                self.backend = 'mipi'
                print(f"[Camera] 使用 MIPI 专用快递员 (libsrcampy)")

            # MIPI不行就试v4l2（兼容性好，通用）
            elif self._try_open_v4l2():
                self.backend = 'v4l2'
                print(f"[Camera] 使用 v4l2 通用快递员 (ISP)")

            # 都不行就报错
            else:
                raise RuntimeError("所有快递员都招不到！摄像头初始化失败")

        elif backend == 'mipi':
            # 【比喻】只要MIPI专用快递员
            if not self._try_open_mipi():
                raise RuntimeError("MIPI专用快递员招聘失败")
            self.backend = 'mipi'

        elif backend == 'v4l2':
            # 【比喻】只要通用快递员
            if not self._try_open_v4l2():
                raise RuntimeError("通用快递员招聘失败")
            self.backend = 'v4l2'

        else:
            raise ValueError(f"不认识的后端类型: {backend}")

    def _try_open_mipi(self):
        """
        尝试打开MIPI摄像头（内部方法）

        【比喻】面试MIPI专用快递员：
        - 检查他的证件（导入hobot_vio库）
        - 给他讲工作要求（调用open_cam）
        - 看他能不能胜任（检查返回值）

        返回：True=成功，False=失败
        """
        try:
            # 导入MIPI摄像头库
            # 【比喻】从官方人才市场找MIPI快递员
            from hobot_vio import libsrcampy

            # 创建摄像头对象
            # 【比喻】快递员来面试了
            self.cam = libsrcampy.Camera()

            # 初始化摄像头
            # 【比喻】给快递员讲工作规范：
            # open_cam参数详解：
            #   参数1: CAM_IDX (0) -> 用哪个摄像头（第0号）
            #   参数2: -1 -> MIPI通道号（-1表示自动检测）
            #            【比喻】-1就像说"随便哪条路都行，你自己挑"
            #   参数3: FPS (30) -> 每秒送多少次
            #   参数4: [WIDTH, WIDTH] -> 宽度（写成数组是因为硬件支持双输出）
            #   参数5: [HEIGHT, HEIGHT] -> 高度（同上）
            ret = self.cam.open_cam(
                self.CAM_IDX,           # 摄像头编号
                -1,                     # MIPI通道（自动检测）
                self.FPS,               # 帧率
                [self.WIDTH, self.WIDTH],   # 宽度数组
                [self.HEIGHT, self.HEIGHT]  # 高度数组
            )

            # 返回值：0表示成功，非0表示失败
            # 【比喻】0就像"OK，我干了"，非0就像"对不起，我不行"
            return ret == 0

        except Exception as e:
            # 任何错误都算失败
            # 【比喻】面试中出了任何问题，都不录用
            return False

    def _try_open_v4l2(self):
        """
        尝试打开v4l2摄像头（内部方法）

        【比喻】面试通用快递员：
        - 他可能有多个"分店"（/dev/video0, /dev/video1...）
        - 我们一个一个试，看哪个能用

        返回：True=成功，False=失败
        """
        try:
            # 【比喻】去不同的"分店"招聘
            # 尝试 /dev/video0, /dev/video1, /dev/video2, /dev/video3
            for dev_id in range(4):

                # 打开视频设备
                # 【比喻】走进这家分店看看
                cap = cv2.VideoCapture(dev_id, cv2.CAP_V4L2)

                # 检查是否成功打开
                if cap.isOpened():
                    # 【比喻】分店开着，可以谈谈

                    # 设置工作规范
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.WIDTH)    # 宽度
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.HEIGHT)  # 高度
                    cap.set(cv2.CAP_PROP_FPS, self.FPS)              # 帧率

                    # 测试读一帧
                    # 【比喻】让他先送一个包裹试试看
                    if cap.read()[0]:
                        # 成功！录用他
                        self.cam = cap
                        return True

                    # 不行就关门，试下一家
                    cap.release()

            # 所有分店都不行
            return False

        except Exception as e:
            return False

    def get_frame_bgr(self):
        """
        获取一帧图像（BGR格式）

        【比喻】让快递员送一个包裹过来，并帮我们拆好包装

        返回：
            numpy.ndarray: 图像数组（240行，320列，3个颜色通道）
                          【比喻】一个240x320的彩色像素网格
            None: 获取失败
        """
        # 检查快递员是否在岗
        if self.cam is None:
            raise RuntimeError("快递员还没招聘！请先初始化摄像头")

        # 根据快递员类型，用不同的方式取包裹
        if self.backend == 'mipi':
            return self._get_frame_mipi()   # MIPI专用快递员的送法
        elif self.backend == 'v4l2':
            return self._get_frame_v4l2()   # 通用快递员的送法
        else:
            raise RuntimeError(f"不认识的快递员类型: {self.backend}")

    def _get_frame_mipi(self):
        """
        从MIPI摄像头获取帧（内部方法）

        【比喻】MIPI专用快递员的送包裹流程：
        1. 他送来一个"压缩包"（NV12格式）
        2. 我们需要解压（numpy.frombuffer）
        3. 翻译成我们能看懂的语言（BGR格式）

        技术细节：
        - NV12是YUV格式的一种，像"压缩的JPEG"
        - BGR是OpenCV常用的格式，像"解压后的位图"
        """
        try:
            # 从摄像头获取原始图像
            # 【比喻】快递员送来了一个包裹
            # 参数说明：
            #   2: VPS输出通道号（硬件规定的，固定用2）
            #   WIDTH, HEIGHT: 我们要的图像尺寸
            img = self.cam.get_img(2, self.WIDTH, self.HEIGHT)

            if img is None:
                return None

            # ===== 格式转换：NV12 -> BGR =====

            # 步骤1: 把字节数据转成numpy数组
            # 【比喻】把压缩包拆开，拿出里面的东西
            frame = np.frombuffer(img, dtype=np.uint8)

            # 步骤2: 重塑成NV12格式的形状
            # 【比喻】按照NV12的摆放规则整理东西
            # NV12格式说明：
            #   - Y平面：完整图像的亮度（灰度图）
            #   - UV平面：交错存放的颜色信息（高度是Y的一半）
            #   - 总大小：height * 1.5 * width
            yuv = frame.reshape(int(self.HEIGHT * 1.5), self.WIDTH)

            # 步骤3: 转换成BGR格式
            # 【比喻】翻译成我们能看懂的颜色格式
            # cv2.cvtColor就像一个"翻译器"
            bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_NV12)

            return bgr

        except Exception as e:
            print(f"[Camera] MIPI快递员送包裹失败: {e}", file=sys.stderr)
            return None

    def _get_frame_v4l2(self):
        """
        从v4l2摄像头获取帧（内部方法）

        【比喻】通用快递员的送包裹流程：
        1. 他直接送来现成的包裹（已经是BGR格式）
        2. 我们检查一下大小对不对
        3. 不对的话调整一下
        """
        try:
            # 读取一帧
            # 【比喻】快递员送来了包裹
            ret, frame = self.cam.read()

            if ret and frame is not None:
                # 检查尺寸
                # 【比喻】包裹大小对不对？
                if frame.shape[1] != self.WIDTH or frame.shape[0] != self.HEIGHT:
                    # 不对就调整
                    # 【比喻】用缩放机调整到我们要的大小
                    frame = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
                return frame

            return None

        except Exception as e:
            print(f"[Camera] v4l2快递员送包裹失败: {e}", file=sys.stderr)
            return None

    def close(self):
        """
        关闭摄像头，释放资源

        【比喻】给快递员办离职手续：
        1. 清点他的工具
        2. 让他走人
        3. 把工位腾出来给下一个人

        重要：如果不调用这个方法，摄像头会一直被占用！
        """
        if self.cam is not None:
            try:
                # 根据快递员类型，用不同的离职流程
                if self.backend == 'mipi':
                    self.cam.close_cam()    # MIPI专用离职流程
                elif self.backend == 'v4l2':
                    self.cam.release()      # 通用离职流程
            except:
                # 即使出错也要继续清理
                pass
            # 标记为"离职"
            self.cam = None

    # ===== 上下文管理器（Python高级特性）=====
    # 【比喻】这就像一个"自动离职办理器"
    # 用"with"语句时，会自动调用这两个方法

    def __enter__(self):
        """
        进入上下文

        【比喻】员工入职时自动调用
        用法：with Camera() as cam:
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文

        【比喻】员工离职时自动调用（无论正常离职还是出问题）
        这保证了资源一定会被释放！
        """
        self.close()
        return False  # False表示不压制异常


# ========== 测试代码 ==========
# 【比喻】这是招聘测试，看看我们能不能招到快递员
if __name__ == "__main__":
    print("[测试] 摄像头驱动")

    # 使用上下文管理器（推荐）
    # 【比喻】雇佣临时工，用完自动解雇
    with Camera() as cam:
        frame = cam.get_frame_bgr()
        if frame is not None:
            print(f"✓ 成功获取画面: {frame.shape}")
            # 输出示例: (240, 320, 3) 表示 240行 x 320列 x 3颜色(BGR)
        else:
            print("✗ 获取画面失败")
