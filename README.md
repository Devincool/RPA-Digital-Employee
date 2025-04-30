# RPA-Digital-Employee (RDE)

[English](README.md) | [中文](README_zh.md)

RDE is an automated customer service solution for Xianyu e-commerce platform based on RPA technology. Through deeply optimized prompt engineering and efficient API calling strategies, it provides intelligent, fast, and cost-effective customer service for Xianyu sellers.

> This is the community version, open-sourcing core algorithm implementations. To protect commercial interests, it does not include data encryption modules and frontend/backend interfaces. For private deployment of complete solutions (including frontend/backend interfaces, data encryption, multi-account management, and other enterprise-level features), please contact us for the commercial version.

## Key Features

- 🤖 Intelligent Customer Service: Smart dialogue system based on large language models
- ⚡ Fast Response: Second-level response time, easily ranking on Xianyu service response leaderboard
- 💰 Cost-Effective: Minimize API tokens consumption to reduce operational costs
- 🔄 System Integration: Seamless integration with Xianyu backend management system
- 📦 Knowledge Base Support: Automatic product information retrieval and dynamic knowledge base construction
- 🔒 Security & Reliability: Built-in secure storage mechanism to protect sensitive information
- 💹 Price Management: Support automatic price negotiation and modification on Xianyu

## Demo Video

<video width="640" height="360" controls>
  <source src="resources/demo.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

## Requirements

- Python 3.8+
- Windows 10/11
- Xianyu Client (Supported versions: v1.21.18 and above)

## Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/your-username/RPA-Digital-Employee.git
cd RPA-Digital-Employee
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the service:
```bash
python run_service.py
```

2. The system will automatically:
   - Connect to Xianyu client
   - Initialize customer service system
   - Load product knowledge base
   - Start monitoring and responding to customer messages

## Configuration

Main configuration file is located at `core/config.py`, including:
- API key configuration
- Prompt templates
- System parameters
- Product information cache settings

## Project Structure

```
RPA-Digital-Employee/
├── core/                    # Core functional modules
│   ├── CustomerService.py   # Main customer service program
│   ├── config.py           # Configuration file
│   ├── secure.py           # Secure storage module
│   ├── tools.py            # Utility module (includes Xianyu management interface)
│   └── xianyu_adapter_*.py # Xianyu client adapters
├── run_service.py          # Service startup script
└── README.md               # Project documentation
```

## Important Notes

1. Before first run, ensure:
   - Xianyu client is properly installed and logged in
   - Required API keys are configured (LLM API key and Xianyu management key, latter is optional)
   - Network connection is stable

2. Security recommendations:
   - Regularly update API keys
   - Do not commit configuration files containing sensitive information to version control
   - Use secure network environment

## Contributing

Issues and Pull Requests are welcome to help improve the project.

## Investment Opportunities

We are a studio focused on RPA+AI technology innovation, with complete product planning and business strategy. Currently seeking angel investment to accelerate product development and market expansion.

If you are interested in our project, please contact us through:

- Email: jishen_devin@163.com
- WeChat: <img src="resources/wechat.jpg" width="200" height="272" alt="WeChat QR Code">

## License

MIT License 