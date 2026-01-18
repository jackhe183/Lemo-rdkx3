# RDK X3 模块化驱动与多模态交互大脑

## 项目结构

```
rdk_x3_modular/
├── drivers/
│   ├── __init__.py           # 模块导出
│   ├── camera_driver.py      # 摄像头驱动（上下文管理器）
│   └── audio_driver.py       # 音频驱动（tinycap/tinyplay）
├── robot_brain.py            # 多模态交互大脑
├── test_integration.py       # 集成测试脚本
└── README.md                 # 本文档
```

## 硬件约束

### 摄像头
- **后端**: `hobot_vio.libsrcampy`（仅支持 MIPI）
- **配置**: `(0, 1, 30, 320, 240)`
- **格式**: NV12 → BGR（numpy.frombuffer + cv2.cvtColor）

### 音频
- **录音**: `tinycap -D 0 -d 1 -c 4 -r 48000 -b 16`
- **播放**: `tinyplay -D 0 -d 0`
- **冲突处理**: 使用 `sudo lsof /dev/snd/*` 检测并清理占用进程

### MediaPipe
- **模型复杂度**: `model_complexity=0`（保证 < 50ms 延迟）

## 使用方法

### 1. 前置准备

```bash
# 停止桌面服务（必须）
sudo systemctl stop lightdm

# 安装依赖
pip install mediapipe opencv-python numpy
```

### 2. 运行集成测试

```bash
cd /home/sunrise/mediapipe_demo/rdk_x3_modular
sudo python3 test_integration.py
```

预期输出：
```
==================================================
RDK X3 Integration Test
==================================================

[TEST 1/3] Camera Driver
------------------------------
✓ Camera opened successfully
✓ Frame captured: (240, 320, 3)
✓ Photo saved: test_photo.jpg
✓ Camera closed automatically

[TEST 2/3] Audio Driver
------------------------------
✓ Audio driver initialized
Recording 1 second...
✓ Recording saved: test_record.wav

[TEST 3/3] MediaPipe Hands
------------------------------
✓ MediaPipe version: x.x.x
✓ Hands model loaded (complexity=0)
✓ Process time: XX.Xms
✓ Performance OK (< 50ms)

==================================================
TEST SUMMARY
==================================================
✓ Camera: PASSED
✓ Audio: PASSED
✓ MediaPipe: PASSED

==================================================
✓ ALL TESTS PASSED
==================================================
```

### 3. 运行多模态交互大脑

```bash
sudo python3 robot_brain.py
```

#### 手势触发逻辑

| 手势 | 触发条件 | 动作 |
|------|----------|------|
| **捏合** (Pinch) | 食指指尖与拇指指尖距离 < 0.05 | 播放提示音 (beep.wav / welcome.wav) |
| **张开手掌** (Palm) | 5 根手指全部伸展 | 录音 2 秒 (user.wav) |

#### 性能监控
- 每 30 帧输出一次 FPS
- 触发动作有 1 秒冷却时间

**注意**: RDK X3 上 MediaPipe 处理时间约为 **300-350ms**，超过 50ms 目标。这是平台性能限制。

### 4. 驱动模块使用示例

```python
from drivers import Camera, Audio

# 摄像头（上下文管理器）
with Camera() as cam:
    frame = cam.get_frame_bgr()
    # 自动关闭

# 音频
audio = Audio()
audio.record("output.wav", 2)
audio.play("beep.wav")
```

## API 参考

### Camera 类

```python
class Camera:
    """MIPI 摄像头驱动（上下文管理器）"""

    def __init__(self):
        """初始化摄像头"""

    def get_frame_bgr(self):
        """获取 BGR 格式帧"""
        # Returns: numpy.ndarray (240, 320, 3)

    def close(self):
        """释放摄像头资源"""

    def __enter__(self):
        """上下文管理器入口"""

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口（自动清理）"""
```

### Audio 类

```python
class Audio:
    """音频驱动（tinycap/tinyplay）"""

    def record(self, path, duration):
        """
        录音

        Args:
            path: 输出 WAV 文件路径
            duration: 录音时长（秒）
        """

    def play(self, path):
        """
        播放

        Args:
            path: WAV 文件路径
        """
```

### RobotBrain 类

```python
class RobotBrain:
    """多模态交互大脑"""

    def __init__(self):
        """初始化（加载 MediaPipe Hands）"""

    def process_frame(self, frame):
        """处理单帧：检测手势并触发动作"""

    def run(self, duration=None):
        """
        主循环

        Args:
            duration: 运行时长（秒），None = 无限循环
        """
```

## 故障排除

### 问题 1: MIPI 摄像头初始化失败

**错误**: `open_cam failed with code -1`

**解决**:
1. 确保 `lightdm` 已停止：`sudo systemctl stop lightdm`
2. 物理断电重启硬件

### 问题 2: 音频设备占用

**错误**: `Recording failed: Device or resource busy`

**解决**:
驱动会自动清理占用进程。如仍有问题：
```bash
sudo lsof /dev/snd/*
sudo kill -9 <PID>
```

### 问题 3: MediaPipe 延迟过高

**检查**:
- 确保 `model_complexity=0`
- 检查 CPU 负载：`top`

## 版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-01-18 | 1.0 | 初始版本：模块化驱动 + 多模态交互大脑 |
