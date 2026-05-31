# ClipShare — Mac ↔ Windows LAN Text Transfer

两台指定电脑之间快速互传文本内容（代码报错、日志、代码片段等），局域网内零配置自动发现。

---

## 安装

### 两台电脑都要做：

**1. 安装 Python 3.8+**

- **Mac**: 预装 Python 3 (终端输入 `python3 --version` 确认)
- **Windows**: [python.org](https://python.org) 下载安装，**勾选 "Add Python to PATH"**

**2. 将此 `clipshare/` 文件夹复制到两台电脑上**

**3. 安装依赖**

```bash
cd clipshare/
pip install -r requirements.txt
```

---

## 使用

### 接收端 — 运行 `receiver.py`

在要**接收**内容的那台电脑上：

```bash
cd clipshare/
python3 receiver.py
# 或 Windows: python receiver.py
```

保持终端开着即可。收到的文本**自动复制到剪贴板**，直接粘贴。

### 发送端 — 运行 `sender.py`

在要**发送**内容的那台电脑上：

```bash
cd clipshare/

# 方式1: 发送剪贴板内容（最常用，最快）
python3 sender.py --clip

# 方式2: 直接发送文本
python3 sender.py "NullPointerException at Foo.java:42"

# 方式3: 发送文件内容
python3 sender.py --file error.log

# 方式4: 管道输入
cat crash_report.txt | python3 sender.py --stdin
```

> **提示**: `--clip` 是最常用的方式。在 IDE 里复制报错信息，切到终端执行 `python3 sender.py --clip`，对端剪贴板就有了。

### 其他命令

```bash
python3 sender.py status         # 检查接收端是否在线
python3 sender.py config         # 查看当前配置
python3 receiver.py --no-mdns    # 禁用自动发现（手动模式）
python3 receiver.py --port 9877  # 指定端口
```

---

## 工作原理

```
┌─────────────────┐         HTTP POST /clip         ┌─────────────────┐
│   发送端         │ ──────────────────────────────→ │   接收端         │
│  sender.py      │    {"text": "...", ...}         │  receiver.py    │
│                 │                                  │                 │
│  复制报错信息    │                                  │  自动写入剪贴板   │
│  → 一键发送     │ ←─── mDNS 自动发现 ──────────── │  → 直接粘贴      │
└─────────────────┘                                  └─────────────────┘
```

- **mDNS 自动发现**: 两台电脑在局域网内自动互相发现，无需配 IP
- **剪贴板直通**: 发送端复制 → 接收端粘贴，中间只有一条命令
- **UTF-8 全文支持**: 中英文、emoji 均可传输

---

## 手动指定 IP（可选）

如果 mDNS 自动发现不工作（如路由器阻止组播）：

**方法1**: 在 `clipshare.json` 中设置：
```json
{
    "peer_host": "192.168.1.100"
}
```

**方法2**: 命令行指定：
```bash
python3 sender.py --peer 192.168.1.100 --clip
```

**方法3**: 环境变量：
```bash
export CLIPSHARE_PEER_HOST=192.168.1.100
```

---

## 配置说明

`clipshare.json` (自动生成，可手动编辑):

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `port` | 9876 | 通信端口，两台电脑需一致 |
| `secret` | auto | 共享密钥，首次运行自动生成 |
| `peer_host` | null | 手动指定对端 IP。不设置则用 mDNS 自动发现 |
| `max_size_kb` | 512 | 单次最大传输大小 (KB) |

环境变量覆盖: `CLIPSHARE_PORT`, `CLIPSHARE_SECRET`, `CLIPSHARE_PEER_HOST`, `CLIPSHARE_MAX_SIZE_KB`

---

## 故障排除

| 问题 | 解决 |
|------|------|
| **"No peer found"** | 确认对端已运行 `python3 receiver.py`；两台电脑在同一局域网 |
| **"zeroconf not installed"** | `pip install zeroconf` |
| **剪贴板不工作** (Linux) | `sudo apt install xclip` |
| **端口被占用** | 修改 `clipshare.json` 中的 `port` 或 `python3 receiver.py --port 9877` |
| **防火墙阻止** | Mac: 首次运行允许网络权限；Windows: 允许 Python 通过防火墙 |
