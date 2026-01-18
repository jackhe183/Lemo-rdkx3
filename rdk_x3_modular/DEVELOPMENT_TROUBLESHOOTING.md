# RDK X3 模块化驱动开发 - 踩坑文档

本文档记录了 `rdk_x3_modular` 项目开发过程中遇到的所有问题和解决方案，帮助小白开发者快速避坑。

---

## 项目背景

- **目标**: 将 `rdk_x3_driver/rdk_hw.py` 拆分为模块化的摄像头和音频驱动
- **参考**: 已经验证可运行的 `rdk_x3_driver` 代码
- **结果**: 成功跑通摄像头和音频模块，通过所有集成测试

---

## 踩坑记录

### 问题 1: Python 缩进错误（Tab 和空格混用）

**错误信息:**
```
TabError: inconsistent use of tabs and spaces in indentation
  File "/home/sunrise/mediapipe_demo/rdk_x3_modular/test_integration.py", line 137
```

**原因:**
`test_integration.py` 中使用了 Tab 和空格混合缩进。Python 3 对缩进要求严格，不允许混用。

**解决方案:**
```python
# 错误代码（使用 Tab）
    if results.get("Camera") is False:
		print("\nCamera failed.")  # ← Tab 缩进
		return 1

# 正确代码（使用空格）
    if results.get("Camera") is False:
        print("\nCamera failed.")  # ← 4 个空格缩进
        return 1
```

**小白避坑指南:**
1. **配置编辑器**: 在 VSCode、PyCharm 等编辑器中设置 "Insert spaces when pressing tab"
2. **使用 linter**: 安装 `pylint` 或 `flake8` 自动检测缩进问题
3. **统一风格**: 始终使用 4 个空格缩进（Python 官方推荐）

---

### 问题 2: robot_brain.py 语法错误（continue 语句缩进）

**错误信息:**
```python
# 代码无报错但逻辑错误
if frame is None:
#    print("[Warning] Failed to capture frame")
#    time.sleep(0.1)
    continue  # ← 这行会被执行，但上面的注释被当成了代码
```

**原因:**
注释前的缩进不一致，导致 `continue` 语句的缩进级别错误。

**解决方案:**
```python
# 错误代码
if frame is None:
#    print("[Warning] Failed to capture frame")
#    time.sleep(0.1)
    continue  # ← 缩进错误

# 正确代码
if frame is None:
    # print("[Warning] Failed to capture frame")
    # time.sleep(0.1)
    continue  # ← 正确缩进
```

**小白避坑指南:**
- 注释也要保持正确的缩进
- 使用编辑器的 "Toggle Line Comment" 功能（Ctrl+/）自动添加注释

---

### 问题 3: 摄像头连续初始化失败

**错误信息:**
```
[ERROR]["LOG"][src/hb_vin_vin.c:280] HB_VIN_SetDevAttr error!
[1;31m2026/01/18 12:59:41.366 ERROR [x3_cam_init][0246]x3_vin_init failed, -268565506
RuntimeError: open_cam failed with code -1
```

**场景:**
1. 第一次运行 `test_integration.py` 成功
2. 立即第二次运行失败
3. 摄像头硬件状态未恢复

**原因分析:**
- MIPI 摄像头在 `close_cam()` 后需要时间释放资源
- 第一次测试关闭摄像头后，硬件状态未完全恢复
- 第二次初始化时硬件仍处于"占用"状态

**解决方案 1: 添加后端自动检测（推荐）**

参考 `rdk_x3_driver/rdk_hw.py` 的实现，添加 v4l2 后端作为备用：

```python
class Camera:
    def __init__(self, backend='auto'):
        """支持 auto/mipi/v4l2 三种模式"""
        self.cam = None
        self.backend = None
        self._open(backend)

    def _open(self, backend='auto'):
        if backend == 'auto':
            # 先尝试 MIPI，失败后自动切换到 v4l2
            if self._try_open_mipi():
                self.backend = 'mipi'
            elif self._try_open_v4l2():
                self.backend = 'v4l2'
            else:
                raise RuntimeError("Failed to open camera with any backend")
```

**解决方案 2: 使用 MIPI_HOST=-1 自动检测**

```python
# 固定 mipi_host=0 可能失败
ret = self.cam.open_cam(0, 0, 30, [320, 320], [240, 240])  # ❌

# 使用 -1 让系统自动检测
ret = self.cam.open_cam(0, -1, 30, [320, 320], [240, 240])  # ✅
```

**解决方案 3: 杀掉占用进程**

在初始化摄像头前强制清理占用进程：

```python
def _open(self):
    # 停止桌面服务
    subprocess.run(["sudo", "systemctl", "stop", "lightdm"],
                  stderr=subprocess.DEVNULL)
    # 杀掉占用进程
    subprocess.run(["sudo", "pkill", "-9", "-f", "mipi"],
                  stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "pkill", "-9", "-f", "cam"],
                  stderr=subprocess.DEVNULL)
```

**小白避坑指南:**
1. **优先使用 auto 后端**: `Camera(backend='auto')` 会自动尝试 MIPI 和 v4l2
2. **测试间隔**: 连续测试之间等待 2-3 秒
3. **完全重启**: 如果连续失败，执行 `sudo reboot` 或物理断电

---

### 问题 4: 导入路径错误（ModuleNotFoundError）

**错误信息:**
```
ModuleNotFoundError: No module named 'drivers'
```

**场景:**
```bash
# 当前目录
cd /home/sunrise/mediapipe_demo

# 尝试导入
python3 -c "from drivers.camera_driver import Camera"  # ❌ 失败
```

**原因:**
Python 解释器在当前目录查找 `drivers` 模块，但模块在 `rdk_x3_modular/drivers/` 下。

**解决方案:**

**方法 1: 切换到正确目录**
```bash
cd /home/sunrise/mediapipe_demo/rdk_x3_modular
python3 -c "from drivers.camera_driver import Camera"  # ✅
```

**方法 2: 设置 PYTHONPATH**
```bash
export PYTHONPATH=/home/sunrise/mediapipe_demo/rdk_x3_modular:$PYTHONPATH
python3 -c "from drivers.camera_driver import Camera"  # ✅
```

**方法 3: 使用绝对路径运行**
```bash
python3 /home/sunrise/mediapipe_demo/rdk_x3_modular/test_integration.py  # ✅
```

**小白避坑指南:**
1. **使用 __main__ 块测试**: 在每个模块文件末尾添加测试代码
   ```python
   if __name__ == "__main__":
       # 测试代码
       cam = Camera()
       print("Camera test OK")
   ```
2. **使用集成测试**: 通过 `test_integration.py` 统一测试所有模块
3. **确认目录结构**: 确保 `__init__.py` 存在于 `drivers/` 目录中

---

### 问题 5: v4l2 后端帧尺寸不匹配

**现象:**
使用 v4l2 后端时，返回的帧尺寸不是期望的 320x240。

**原因:**
v4l2 设备（如 USB 摄像头）可能不支持 320x240 分辨率。

**解决方案:**
在 `_get_frame_v4l2()` 中添加自动调整尺寸：

```python
def _get_frame_v4l2(self):
    ret, frame = self.cam.read()
    if ret and frame is not None:
        # 如果尺寸不匹配，自动调整
        if frame.shape[1] != self.WIDTH or frame.shape[0] != self.HEIGHT:
            frame = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
        return frame
    return None
```

**小白避坑指南:**
- 使用 `cv2.resize()` 保证输出尺寸一致
- 在日志中打印实际获取的尺寸，便于调试

---

## 成功要点总结

### 1. 参考已有代码

开发流程：
1. 先阅读并理解 `rdk_x3_driver/rdk_hw.py` 的实现
2. 提取核心功能拆分到独立模块
3. 保留关键的参数配置和 API 调用方式

关键对照：
| 功能 | rdk_x3_driver | rdk_x3_modular |
|------|---------------|----------------|
| MIPI 初始化 | `open_cam(0, -1, 30, [w,w], [h,h])` | ✅ 相同 |
| NV12 转换 | `np.frombuffer + cv2.cvtColor` | ✅ 相同 |
| 音频录音 | `tinycap -D 0 -d 1 -c 4 -r 48000 -b 16` | ✅ 相同 |
| 后端检测 | auto → MIPI → v4l2 | ✅ 相同 |

### 2. 逐步测试策略

```
第1步: 修复语法错误（缩进问题）
       ↓
第2步: 测试单个模块（drivers/camera_driver.py）
       ↓
第3步: 运行集成测试（test_integration.py --skip-camera）
       ↓
第4步: 完整集成测试（test_integration.py）
       ↓
第5步: 测试应用层（robot_brain.py）
```

### 3. 关键代码修改

**camera_driver.py 改进:**
```python
# 添加后端自动检测
def __init__(self, backend='auto'):  # 新增 backend 参数
    self.backend = None  # 记录当前使用的后端

# 使用 mipi_host=-1 自动检测
ret = self.cam.open_cam(0, -1, 30, [320, 320], [240, 240])

# 根据后端类型获取帧
def get_frame_bgr(self):
    if self.backend == 'mipi':
        return self._get_frame_mipi()
    elif self.backend == 'v4l2':
        return self._get_frame_v4l2()

# 根据后端类型释放资源
def close(self):
    if self.backend == 'mipi':
        self.cam.close_cam()
    elif self.backend == 'v4l2':
        self.cam.release()
```

### 4. 测试验证

最终测试结果：
```
==================================================
✓ ALL TESTS PASSED
==================================================
✓ Camera: PASSED  (MIPI backend, 320x240)
✓ Audio: PASSED   (48000Hz, 4ch)
✓ MediaPipe: PASSED (complexity=0, ~270ms)
```

---

## 小白开发者 SOP（标准操作流程）

### 环境准备

```bash
# 1. 确保已安装依赖
pip install mediapipe opencv-python numpy

# 2. 停止桌面服务（必须）
sudo systemctl stop lightdm

# 3. 进入项目目录
cd /home/sunrise/mediapipe_demo/rdk_x3_modular
```

### 测试流程

```bash
# 步骤 1: 运行集成测试（跳过摄像头，快速验证）
sudo python3 test_integration.py --skip-camera

# 步骤 2: 如果音频测试通过，运行完整测试
sudo python3 test_integration.py

# 步骤 3: 如果摄像头测试失败，检查日志
# 常见错误：
# - open_cam failed: 需要物理断电重启
# - MIPIHOSTIOC_INIT error: 确认 lightdm 已停止

# 步骤 4: 测试多模态交互大脑
sudo python3 robot_brain.py
```

### 代码开发规范

```python
# 1. 模块导入
from drivers import Camera, Audio  # 使用统一的导入接口

# 2. 使用上下文管理器（推荐）
with Camera() as cam:
    frame = cam.get_frame_bgr()
    # 自动清理资源

# 3. 手动管理资源（备选）
cam = Camera()
try:
    frame = cam.get_frame_bgr()
finally:
    cam.close()  # 确保资源释放
```

---

## 常见调试命令

```bash
# 检查摄像头占用
sudo pkill -9 -f "mipi|cam"

# 检查音频占用
sudo lsof /dev/snd/*

# 停止桌面服务
sudo systemctl stop lightdm

# 重启桌面服务
sudo systemctl start lightdm

# 查看 MIPI 传感器
i2ctransfer -y -f 1 w1@0x40 0xb r1

# 查看内核日志（摄像头相关）
dmesg | grep -i "mipi\|vin\|camera"

# 测试单个模块
python3 drivers/camera_driver.py
python3 drivers/audio_driver.py
```

---

## 版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-01-18 | 1.0 | 初始版本，记录模块化开发过程和踩坑经验 |

---

## 参考资源

- **参考实现**: `rdk_x3_driver/rdk_hw.py`（已验证可运行）
- **官方文档**: [RDK X3 MIPI 摄像头](https://d-robotics.github.io/rdk_doc/Basic_Application/vision/mipi_camera)
- **API 文档**: `/usr/local/lib/python3.10/dist-packages/hobot_vio/`
