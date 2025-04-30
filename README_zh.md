# RPA-Digital-Employee (RDE)

[English](README.md) | [中文](README_zh.md)

RDE是一个基于RPA技术的闲鱼电商客服自动化解决方案。通过深度优化的提示词工程和高效的API调用策略，为闲鱼卖家提供智能、快速、经济的客服服务。

> 本项目为社区版，开源核心算法。为保护商业利益，不包含数据加密模块和前后端界面。如需私有化部署完整解决方案（含前后端界面、数据加密、多账号管理等企业级功能），请联系我们获取商业版本。

## 主要特点

- 🤖 智能客服：基于大语言模型的智能对话系统
- ⚡ 快速响应：秒级响应，轻松上闲鱼服务响应榜
- 💰 经济高效：最小化API tokens消耗，降低运营成本
- 🔄 系统集成：与闲鱼后台管理系统无缝对接
- 📦 知识库支持：自动获取商品信息，构建动态知识库
- 🔒 安全可靠：内置安全存储机制，保护敏感信息
- 💹 价格管理：支持闲鱼自动议价、改价功能

## 演示视频

<video width="640" height="360" controls>
  <source src="resources/demo.mp4" type="video/mp4">
  您的浏览器不支持视频播放。
</video>

## 环境要求

- Python 3.8+
- Windows 10/11
- 闲鱼客户端（支持版本：v1.21.18及以上）

## 安装步骤

1. 克隆项目到本地：
```bash
git clone https://github.com/your-username/RPA-Digital-Employee.git
cd RPA-Digital-Employee
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动服务：
```bash
python run_service.py
```

2. 系统会自动：
   - 连接到闲鱼客户端
   - 初始化客服系统
   - 加载商品知识库
   - 开始监听并响应客户消息

## 配置说明

主要配置文件位于 `core/config.py`，包含：
- API密钥配置
- 提示词模板
- 系统参数设置
- 商品信息缓存配置

## 目录结构

```
RPA-Digital-Employee/
├── core/                    # 核心功能模块
│   ├── CustomerService.py   # 客服系统主程序
│   ├── config.py           # 配置文件
│   ├── secure.py           # 安全存储模块
│   ├── tools.py            # 工具模块（含闲管家接口）
│   └── xianyu_adapter_*.py # 闲鱼客户端适配器
├── run_service.py          # 服务启动脚本
└── README.md               # 项目说明文档
```

## 注意事项

1. 首次运行前请确保：
   - 闲鱼客户端已正确安装并登录
   - 已配置必要的API密钥（大模型API蜜钥和闲管家蜜钥，闲管家不必须）
   - 网络连接正常

2. 安全建议：
   - 定期更新API密钥
   - 不要将包含敏感信息的配置文件提交到版本控制
   - 使用安全的网络环境

## 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目。

## 投融资需求

我们是一家专注于RPA+AI技术创新的工作室，拥有完整的产品规划和商业计划。目前正在寻求天使投资，以加速产品研发和市场拓展。

如果您对我们的项目感兴趣，欢迎通过以下方式联系我们：

- 邮箱：jishen_devin@163.com
- 微信：<img src="resources/wechat.jpg" width="200" height="272" alt="微信二维码">

## 许可证

MIT License
