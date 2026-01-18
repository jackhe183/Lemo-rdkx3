#!/usr/bin/env python3
# RDK X3 音频驱动
#
# 通俗理解：
# 想象音频就像一个"电话系统"，我们需要：
# 1. 拿起电话说话（录音）
# 2. 放下电话听别人说话（播放）
# 3. 确保电话线没被别人占着（清理占用）
#
# 工具说明：
# - tinycap: 录音工具（像录音机）
# - tinyplay: 播放工具（像播放器）
# - 使用subprocess调用这些命令行工具

import subprocess
import time


class Audio:
    """
    RDK X3 音频驱动类

    【比喻】这是一个"电话管理中心"
    - 他知道怎么录音（按下录音键）
    - 他知道怎么播放（按下播放键）
    - 他能确保电话线没被占着（清理占用进程）

    为什么用 tinycap/tinyplay 而不是 Python 库？
    - RDK X3 的音频硬件需要特定工具
    - 这些是官方提供的命令行工具，最稳定
    """

    # ========== 音频硬件配置常量 ==========
    # 这些是"电话系统"的规格，由硬件决定

    CARD = 0          # 声卡编号：第0号声卡（像有多个电话，用第0个）
    DEVICE_REC = 1    # 录音设备：设备1（麦克风）
    DEVICE_PLAY = 0   # 播放设备：设备0（扬声器）
    CHANNELS = 4      # 通道数：4声道（像4个麦克风同时录音）
    RATE = 48000      # 采样率：48000Hz（每秒取样48000次，音质好）
    BITS = 16         # 位深：16位（每个声音点用16位表示）
    FRAGMENTS = 4     # 缓冲块数：4块（像4个篮子轮流装声音数据）
    FRAGMENT_SIZE = 512  # 每块大小：512字节（每个篮子装多少）

    @staticmethod
    def _cleanup_audio_devices():
        """
        清理占用音频设备的进程（静态方法，不需要实例就能调用）

        【比喻】清理电话线：
        1. 检查谁在占着电话线
        2. 让他们挂断
        3. 我们才能用

        为什么要这样做？
        - 音频设备同时只能被一个进程使用
        - 如果之前有程序异常退出，可能还占着设备
        - 我们需要强制清理，才能正常录音/播放
        """
        try:
            # 查找占用音频设备的进程
            # 【比喻】查查谁在打电话
            # lsof = "list open files"（列出打开的文件）
            # /dev/snd/* = 所有音频设备文件
            result = subprocess.run(
                ["sudo", "lsof", "/dev/snd/*"],
                capture_output=True,      # 捕获输出
                text=True,                # 返回字符串而不是字节
                timeout=5                 # 最多等5秒（防止卡死）
            )

            if result.returncode == 0:
                # 【比喻】找到有人在打电话，记录下来
                pids = set()  # 用集合存储进程ID（去重）

                # 解析输出，提取进程ID
                # 【比喻】从电话记录中找出电话号码
                for line in result.stdout.split('\n'):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            # 第2列是进程ID（PID）
                            # 【比喻】这就是打电话的人的工号
                            pids.add(int(parts[1]))
                        except ValueError:
                            # 转换失败就跳过这行
                            pass

                # 如果有占用的进程，杀掉它们
                # 【比喻】让这些人挂断电话
                if pids:
                    subprocess.run(
                        ["sudo", "kill", "-9"] + list(map(str, pids)),
                        stderr=subprocess.DEVNULL  # 错误信息不显示
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            # 出错就静默忽略（清理不是必须的，只是保险措施）
            # 【比喻】清理电话线失败也不影响我们打电话，只是可能遇到占线
            pass

    def play(self, path):
        """
        播放音频文件

        【比喻】播放录音带：
        1. 先清理电话线
        2. 把磁带放进去
        3. 按播放键

        参数：
            path: WAV文件路径（要播放的文件）

        使用示例：
            audio = Audio()
            audio.play("beep.wav")  # 播放提示音
        """
        # 第1步：清理占用
        # 【比喻】确保电话线没被占着
        self._cleanup_audio_devices()

        # 第2步：构建播放命令
        # 【比喻】准备播放器
        # tinyplay命令格式：
        #   tinyplay <文件> -D <声卡> -d <设备>
        cmd = [
            "sudo", "tinyplay", path,    # 播放命令和文件
            "-D", str(self.CARD),        # 声卡编号
            "-d", str(self.DEVICE_PLAY)  # 播放设备编号
        ]

        # 第3步：执行播放
        # 【比喻】按下播放键
        result = subprocess.run(cmd, capture_output=True)

        # 检查是否成功
        if result.returncode != 0:
            # 【比喻】播放器出故障了
            raise RuntimeError(f"播放失败: {result.stderr.decode()}")

    def record(self, path, duration):
        """
        录音

        【比喻】录音：
        1. 先清理电话线
        2. 按下录音键
        3. 录指定时长
        4. 保存到文件

        参数：
            path: 输出WAV文件路径（保存到哪里）
            duration: 录音时长（秒）

        使用示例：
            audio = Audio()
            audio.record("user.wav", 2)  # 录2秒
        """
        # 第1步：清理占用
        # 【比喻】确保电话线没被占着
        self._cleanup_audio_devices()

        # 第2步：构建录音命令
        # 【比喻】准备录音机
        # tinycap命令格式：
        #   tinycap <输出文件> -D <声卡> -d <设备> -c <通道>
        #           -r <采样率> -b <位深> -p <块大小> -n <块数> -t <时长>
        cmd = [
            "sudo", "tinycap", path,      # 录音命令和输出文件
            "-D", str(self.CARD),         # 声卡编号
            "-d", str(self.DEVICE_REC),   # 录音设备编号
            "-c", str(self.CHANNELS),     # 通道数（4个麦克风）
            "-r", str(self.RATE),         # 采样率（48000Hz，CD音质）
            "-b", str(self.BITS),         # 位深（16位，标准音质）
            "-p", str(self.FRAGMENT_SIZE),# 每块大小（512字节）
            "-n", str(self.FRAGMENTS),    # 缓冲块数（4块）
            "-t", str(duration)           # 录音时长（秒）
        ]

        # 第3步：执行录音
        # 【比喻】按下录音键，等指定时间
        result = subprocess.run(cmd, capture_output=True)

        # 检查是否成功
        if result.returncode != 0:
            # 【比喻】录音机出故障了
            raise RuntimeError(f"录音失败: {result.stderr.decode()}")


# ========== 测试代码 ==========
# 【比喻】测试电话系统能不能正常工作
if __name__ == "__main__":
    print("[测试] 音频驱动")

    # 创建音频对象
    # 【比喻】拿起电话
    audio = Audio()

    # 测试录音
    print("正在录音2秒...")
    audio.record("test_audio.wav", 2)
    print("✓ 录音已保存: test_audio.wav")

    # 注意：4通道音频播放可能失败
    # 【比喻】录音带可能用4个麦克风录的，但播放器只支持2个
    # 建议用 aplay 或 ffplay 播放
