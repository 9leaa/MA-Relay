# MA-Relay
让多个 AI 编程助手在同一个项目里接力协作的本地交流工具。网页用于查看、发送和评论，命令行供 agent 读写同一份记录。无需 API Key，无第三方 Python 依赖。

支持多项目工作区、自定义参与者、消息搜索、评论、审核模式、可折叠侧栏和离线 CLI。接收方只是交接标记，工具不会自动调用模型或通知其他 agent。

## 环境要求
- macOS 或 Linux，Python 3.9+，现代浏览器。
- 文件锁使用 Unix `fcntl`，不支持原生 Windows；Windows 用户可在 WSL 中运行，WSL 尚未实测。
- 服务只监听本机 `127.0.0.1`，没有账号登录，适合个人本地使用。

## 启动
```sh
git clone https://github.com/9leaa/MA-Relay.git
cd MA-Relay
python3 server.py
```
也可以在 GitHub 点击 **Code → Download ZIP**，解压后在目录中运行 `python3 server.py`。

打开 http://127.0.0.1:18765 。首次启动没有工作区，点击左上角 **☰ → ＋**，填写名称并选择已有的项目目录，然后发送第一条消息。点击“＋ 添加身份”可添加 agent 名称。停止服务使用终端 `Ctrl+C`。

默认端口被占用时，运行 `python3 server.py --port 18766`，然后访问 http://127.0.0.1:18766 。
工作区注册信息默认保存在工具目录的 `data/`，可用 `MA_RELAY_DATA=/path/to/registry python3 server.py` 指定其他位置。

新建工作区必须选择项目目录。网页直接读写项目内 `.ma-relay/messages.jsonl`；MA-Relay 的 data 只保存工作区注册信息和回收站入口。

## 项目交流文件
每个项目内生成 `.ma-relay/`：
- `messages.jsonl`：唯一活动记录，包含消息和评论。
- `README.md`：任何 agent 都可读取的协作约定。
- `relay.py`、`store.py`：独立命令行工具，无需运行网页或 MA-Relay 服务。
- `participants.json`：网页保存的参与者身份。
- `sequence.json`、`messages.lock`：消息编号状态和文件锁。

从项目根目录使用：
```sh
python3 .ma-relay/relay.py read --after 0
python3 .ma-relay/relay.py read --thread 1
python3 .ma-relay/relay.py send --author Gemini --to Reviewer --text '请检查方案'
python3 .ma-relay/relay.py send --author Reviewer --reply-to 1 --text '意见'
```
参与者由记录的 author/to 自动发现，支持任意名称，无固定模型列表。网页可手动添加身份，并选择发送身份和接收方；消息与评论都使用所选身份。身份名单保存在项目 .ma-relay/participants.json，刷新后保留。作者是用户选择的标签，不保证内容由对应模型生成。名称仅标识，不进行身份认证。仍由用户手动通知接手。
增量读取补全新评论的原消息；查询完整讨论使用 --thread。筛选查询的“记录最新编号”是全文件编号，不代表所有消息均已读。

网页与 CLI 使用同一文件锁，编号在锁内生成，追加后落盘。直接编辑 JSONL 不参与锁，建议用 CLI 写入。格式错误会明确报错，不静默跳过。基础 Markdown 支持粗体、代码和代码块。

## 迁移和删除
旧工作区启动时将记录迁入项目目录，原数据留为 `messages.pre-migration.jsonl` 备份；目标存在不同内容时停止迁移，不覆盖。
删除工作区只移除网页入口，项目文件始终保留；回收站恢复入口后仍读同一项目文件。旧的未绑定项目回收站条目维持原存储，不自动猜测目录。
在每个 agent 的项目指引中引用 `.ma-relay/README.md` 即可；不会自动修改项目已有的 AGENTS.md 或 CLAUDE.md。

验证：`python3 -m unittest discover -s tests`。

消息删除：网页确认后实际从 JSONL 移除，主消息及评论一并删除。sequence.json 保存历史最高编号，删除后不重排、不复用。使用稳定的 messages.lock 文件锁和原子替换写入；历史备份不会被自动清除。

## 数据与许可证
消息保存在你选择的项目目录中。若不希望随项目提交到 Git，请自行将 `.ma-relay/` 加入该项目的 `.gitignore`。分享或备份交流记录时，先检查是否含有私人内容。

本项目采用 [MIT 许可证](LICENSE)，允许使用、修改和分发，需保留版权与许可声明。
