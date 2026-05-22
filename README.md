# JRETS-NotchBridge

`JRETS-NotchBridge` 是一个面向 **JR East Train Simulator** 的 Windows 外设控制桥接程序。它会读取 USB 摇杆或油门轴输入，将其映射为列车档位，并向游戏发送对应的键盘按键。

项目使用 Python 和 Pygame 开发，面向最终用户通过 PyInstaller 打包发布。

## 功能特性

- 将摇杆轴映射到制动、空挡和动力档位
- 通过 `vehicles.json` 支持不同列车的档位结构
- 支持线性映射和分段标定映射
- 支持可选的轴末端紧急制动触发
- 支持空挡、紧急制动、重同步、鸣笛、定速、发车音乐和广播等按钮映射
- 支持游戏窗口焦点检测，游戏未激活时暂停发送控制输入
- 运行配置保存在 `%APPDATA%` 下

## 项目文件

- `main.py`：主界面与输入循环
- `notch.py`：档位定义与映射辅助逻辑
- `key_sender.py`：键盘注入与按键队列
- `focus_checker.py`：前台窗口与游戏焦点检测
- `vehicles.json`：列车档位预设
- `build.ps1`：PyInstaller 打包脚本

## 运行要求

- Windows 10 或 Windows 11
- Python 3.x（仅源码运行或本地构建时需要）
- 一个兼容的 USB 摇杆、油门杆或其他游戏控制器
- JR East Train Simulator

## 配置文件

程序运行时会把工作文件写入：

```text
%APPDATA%\JRETS-NotchBrige
```

其中主要包括：

- `config.json`：保存控制器与映射设置
- `vehicles.json`：首次运行时从打包资源复制出的列车定义文件

## 本地开发

安装开发所需 Python 依赖后，可直接运行：

```powershell
python main.py
```

如需构建 Windows 打包版本，执行：

```powershell
.\build.ps1
```

打包输出目录为 `dist\JRETS_Controller`。

## 发布包

当前 `0.1.0` 版本提供 PyInstaller 压缩包，内容包括：

- `JRETS_Controller.exe`
- 打包后的运行时依赖
- 内置的 `vehicles.json`

解压后直接运行 `JRETS_Controller.exe` 即可。

## 说明

- 当前仓库已忽略 `config.json`、`build/`、`dist/` 和 `release/`，避免本地状态和构建产物进入源码仓库。
- 打包程序名和 AppData 目录名当前使用的是 `JRETS-NotchBrige`，这与现有代码实现保持一致。
