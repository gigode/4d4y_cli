# 4D4Y Forum CLI

一个仿早期 telnet BBS 时代界面和操作方式的 4D4Y 论坛 CLI 浏览工具。

## 功能特性

- **BBS 风格界面**: 仿 telnet 时代经典界面，终端原生显示
- **板块浏览**: 浏览论坛所有板块，进入 Discovery 等板块阅读帖子
- **帖子阅读**: 阅读帖子内容，支持分页浏览
- **回复功能**: 登录后可以回复帖子
- **会话保持**: 自动保存登录状态，下次启动自动恢复会话
- **纯文字显示**: 帖子中的图片以链接形式显示，不显示图片本身

## 安装

### 源码安装

```bash
# 克隆仓库
git clone https://github.com/gigode/4d4y_cli.git
cd 4d4y_cli

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install requests beautifulsoup4

# 直接运行
python -m forzd4y.cli
```

## 使用方法

### 启动程序

```bash
python -m forzd4y.cli
```

### 界面操作

#### 主菜单

- `[1]` 浏览论坛板块 - 查看所有可用板块
- `[2]` 进入 Discovery 板块 - 直接进入 Discovery 板块
- `[3]` 搜索帖子 - (开发中)
- `[L]` 登录/注销 - 登录或注销账户
- `[Q]` 退出 - 退出程序

#### 帖子列表

- `[J/K]` 或 `↓/↑` - 上/下选择帖子
- `[Enter]` - 查看选中的帖子
- `[R]` - 回复帖子
- `[B]` - 返回上级菜单
- `[1-9]` - 直接输入序号选择帖子

#### 帖子阅读

- `[J]` 或 `↓` - 下一页
- `[K]` 或 `↑` - 上一页
- `[R]` - 回复此帖
- `[H]` - 跳到首页
- `[L]` - 跳到尾页
- `[1-9]` - 跳转到指定页
- `[Q]` - 返回板块列表

### 登录

首次使用时，需要使用用户名和密码登录 4D4Y 论坛:

```
用户名: your_username
密码: ********
```

登录后会话信息会保存在 `~/.config/4d4y_cli/` 目录下，下次启动会自动恢复登录状态。

## 配置

配置文件保存在 `~/.config/4d4y_cli/config.json`

会话 cookies 保存在 `~/.config/4d4y_cli/cookies.json`

如需清除登录状态，删除这些文件即可。

## 系统要求

- Python 3.7 或更高版本
- 支持 ANSI 颜色的终端 (大多数现代终端都支持)

## 依赖

- `requests` - HTTP 请求库
- `beautifulsoup4` - HTML 解析库

## 项目结构

```
4d4y_cli/
├── forzd4y/            # 主程序包（Python模块名不能以数字开头）
│   ├── __init__.py      # 包初始化
│   ├── api.py           # 论坛 API 客户端
│   ├── cli.py           # 命令行界面入口
│   ├── config.py        # 配置管理
│   └── ui.py           # 终端 UI 渲染
├── requirements.txt     # Python 依赖
├── setup.py            # 安装配置
└── README.md           # 本文件
```

## 工作原理

本工具通过模拟浏览器行为与 4D4Y 论坛 (Discuz 架构) 进行交互:

1. **登录**: 访问登录页面获取 formhash，然后提交登录表单
2. **保持会话**: 使用 requests session 自动管理 cookies
3. **获取帖子列表**: 解析 `forumdisplay.php?fid={fid}` 页面
4. **获取帖子内容**: 解析 `viewthread.php?tid={tid}` 页面
5. **回复帖子**: 提交 `post.php?action=reply&tid={tid}` 表单

## 参考项目

本项目参考了以下开源 Android 论坛客户端:

- [ReSource](https://github.com/kenischu/ReSource) - 一个现代 Android 论坛客户端
- [hipda](https://github.com/GreenSkinMonster/hipda) - HiPDA 论坛 Android 客户端

## 免责声明

本工具仅供学习和个人使用，请遵守 4D4Y 论坛的用户协议。

## License

MIT License
