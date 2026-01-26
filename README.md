# EmoVision - 视觉情绪识别Web应用

EmoVision 是一个视觉情绪识别一体化Web应用，支持多种视觉源（图像、视频、摄像头）的实时情绪识别流水线配置、调试与部署。

## 功能特性

- 支持多种视觉源：图像文件、视频文件、实时摄像头
- 实时目标检测：基于 YOLO11 的人脸和人体检测
- 情绪识别：可插拔的情绪识别模型接口
- 丰富的参数配置：检测器、识别器、可视化器全参数可调
- 实时可视化：WebSocket 推送渲染后的帧和统计信息
- 现代化UI：深色专业风格，响应式布局

## 技术栈

### 后端
- FastAPI + Uvicorn (高性能异步API)
- WebSocket (实时帧推送)
- YOLO11 (ultralytics) (目标检测)
- PyTorch (深度学习推理)

### 前端
- React 18 + TypeScript + Vite
- Tailwind CSS (深色主题)
- Zustand (状态管理)
- Recharts (图表可视化)

## 项目结构

```
EmoVision/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/                # API 路由层
│   │   ├── core/               # 核心业务逻辑
│   │   ├── modules/            # 功能模块
│   │   │   ├── detector/       # 目标检测
│   │   │   ├── recognizer/     # 情绪识别
│   │   │   └── visualizer/     # 可视化
│   │   ├── schemas/            # 数据模型
│   │   └── utils/              # 工具函数
│   ├── models/                 # 模型权重
│   └── requirements.txt
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/         # UI 组件
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── store/              # 状态管理
│   │   ├── services/           # API 服务
│   │   ├── types/              # TypeScript 类型
│   │   └── styles/             # 样式文件
│   └── package.json
│
└── .opencode/                  # 项目文档
```

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- CUDA (可选，用于GPU加速)

### 后端安装

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 前端安装

```bash
cd frontend

# 安装依赖
npm install
```

### 启动服务

**启动后端服务：**

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端开发服务器：**

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173 即可使用应用。

## 使用说明

### 1. 选择视觉源

- 点击侧边栏的"上传图像/视频"上传文件
- 或点击"使用摄像头"启用实时摄像头

### 2. 配置参数

展开底部"参数配置"面板，可以调整：

- **目标检测**：模型尺寸、置信度阈值、IoU阈值等
- **情绪识别**：情绪类别标签、批处理大小等
- **可视化**：边界框样式、标签显示、颜色配置等
- **性能**：目标帧率、跳帧数、输出质量等

### 3. 启动流水线

点击侧边栏的"启动"按钮开始情绪识别流水线。

### 4. 查看结果

- 实时视频画面会显示检测框和情绪标签
- 底部统计面板显示实时FPS和延迟
- 情绪分布图表展示各情绪的概率分布

## API 文档

启动后端服务后，访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 自定义情绪识别模型

继承 `BaseEmotionRecognizer` 基类实现自定义模型：

```python
from app.modules.recognizer import BaseEmotionRecognizer

class MyRecognizer(BaseEmotionRecognizer):
    def load_model(self, model_path: str = None) -> None:
        # 加载自定义模型
        pass
    
    def predict(self, frame, detections):
        # 实现情绪识别逻辑
        pass
```

## 开发说明

### 代码规范

- Python: 遵循 PEP 8 规范，使用类型注解
- TypeScript: 使用严格模式，组件使用函数式写法
- 所有公共函数和类必须有文档字符串

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端类型检查
cd frontend
npm run lint
```

## 许可证

MIT License
