# 📝 Lemo-rdkx3 项目

## 🌟 项目简介
**Lemo-rdkx3** 是基于地平线 RDK X3 (Horizon Sunrise X3 Pi) 开发的多模态智能桌宠机器人大脑。
本项目旨在通过 MediaPipe 视觉感知与音频交互，构建一个具备低延迟、模块化驱动和情感反馈能力的智能实体。

## 🛠 硬件环境 (Hardware Stack)
*   **核心板**: Horizon RDK X3 (4GB RAM)
*   **视觉**: F37 MIPI 摄像头 (连接至 CAM0 接口)
*   **音频**: 微雪 Audio Driver HAT (基于 ES7210 录音 / ES8156 播放)
*   **开发机**: Win10 + PyCharm (通过 SSH 远程开发) + `uv` 环境管理

## 🏗 系统架构 (Architecture)
项目采用底层驱动与高层逻辑分离的模块化设计：
*   `drivers/camera_driver.py`: 基于 `libsrcampy` 的 CSI 图像抓取，支持 NV12 到 BGR 的硬解码转换。
*   `drivers/audio_driver.py`: 基于 `tinyalsa` 的低延迟音频处理。
*   `robot_brain.py`: 多模态中枢，集成 MediaPipe 手势识别逻辑。

## 📖 AI 开发约束 (Critical Constraints for AI)
*此部分用于每次开发前同步给 AI，防止其写出不兼容的代码：*
1.  **摄像头**: 严禁使用 `cv2.VideoCapture`，必须使用 `hobot_vio.libsrcampy`。
2.  **图像转换**: 必须通过 `np.frombuffer` 结合 `reshape(int(H * 1.5), W)` 处理 NV12 原始流。
3.  **MediaPipe**: 必须设置 `model_complexity=0` 以保证 A53 核心实时性。
4.  **音频**: 直接调用系统 `tinycap`/`tinyplay` 命令，避免库冲突。
5.  **冲突管理**: 运行前必须 `sudo systemctl stop lightdm` 释放摄像头。

## 🚀 快速开始
### 1. 环境准备
```bash
sudo systemctl stop lightdm
pip install mediapipe numpy==1.26.4 opencv-python
```

### 2. 运行集成测试
验证所有硬件模块是否正常工作：
```bash
sudo python3 test_integration.py
```

### 3. 启动 Lemo 大脑
```bash
sudo python3 robot_brain.py
```

## 🖐 已实现交互逻辑 (Interactions)
| 触发手势 | 算法逻辑 | 执行动作 |
| :--- | :--- | :--- |
| **捏合 (Pinch)** | `INDEX_TIP` & `THUMB_TIP` 距离 < 0.05 | 播放反馈音频 `beep.wav` |
| **手掌 (Palm)** | 五指全部伸展 | 开启 2 秒录音保存为 `user.wav` |

## 📅 路线图 (Roadmap)
- [x] 模块化底层驱动封装
- [x] MediaPipe 手势识别集成
- [x] 多模态音视联动逻辑
- [ ] **Next:** 接入舵机控制 (脖子转动)
- [ ] **Next:** 接入 LD19 激光雷达 (空间避障)
- [ ] **Next:** 离线语音唤醒集成


**建议：** 你可以先把这部分内容复制成 `README.md` 上传到 GitHub，然后把你的 `drivers/` 目录和 `robot_brain.py` 完整推上去。

**下一步你打算先攻克哪个 Roadmap 上的任务？** 我们可以准备开始写舵机的驱动了。
