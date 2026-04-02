# Claude Code 源码分析报告
**来源**: 2026-03-31 泄露版本 | **规模**: ~1,900文件, 512,000+行代码

---

## 一、泄露背景

| 信息 | 详情 |
|------|------|
| **泄露日期** | 2026-03-31 |
| **泄露方式** | npm包的.map文件暴露完整TypeScript源码 |
| **发现者** | Chaofan Shou (@Fried_rice) |
| **语言** | TypeScript |
| **运行时** | Bun |
| **CLI框架** | Commander.js |

---

## 二、核心架构

### 2.1 入口点: `main.tsx` (803KB)
- CLI参数解析
- 命令路由
- 主循环控制

### 2.2 核心引擎: `QueryEngine.ts` (46KB, 1295行)
```typescript
// 核心LLM查询引擎
class QueryEngine {
  // API调用循环
  // 流式响应处理
  // 工具调用解析
  // Thinking模式
  // 重试逻辑
  // Token计数
}
```

### 2.3 工具系统: `Tool.ts` (29KB, 792行)
所有工具的基类和接口定义。

---

## 三、工具系统 (`src/tools/`)

### 工具列表 (~40个)

| 类别 | 工具 |
|------|------|
| **文件操作** | `BashTool`, `FileReadTool`, `FileWriteTool`, `FileEditTool`, `GlobTool`, `GrepTool` |
| **Web** | `WebFetchTool`, `WebSearchTool` |
| **AI/Agent** | `AgentTool`, `SkillTool`, `MCPTool`, `TaskCreateTool`, `TaskUpdateTool` |
| **通信** | `SendMessageTool`, `TeamCreateTool`, `TeamDeleteTool` |
| **Git** | `EnterWorktreeTool`, `ExitWorktreeTool` |
| **代码** | `LSPTool`, `NotebookEditTool` |
| **调度** | `CronCreateTool`, `RemoteTriggerTool` |
| **其他** | `EnterPlanModeTool`, `ExitPlanModeTool`, `ToolSearchTool`, `SleepTool`, `SyntheticOutputTool` |

---

## 四、命令系统 (`src/commands/`)

### 命令列表 (~50个slash命令)

| 命令 | 功能 |
|------|------|
| `/commit` | Git提交 |
| `/review` | 代码审查 |
| `/compact` | 上下文压缩 |
| `/mcp` | MCP服务器管理 |
| `/config` | 设置管理 |
| `/doctor` | 环境诊断 |
| `/memory` | 持久化记忆 |
| `/skills` | Skill管理 |
| `/tasks` | 任务管理 |
| `/vim` | Vim模式 |
| `/diff` | 查看变更 |
| `/cost` | 消耗查询 |
| `/context` | 上下文可视化 |
| `/resume` | 恢复会话 |
| `/share` | 分享会话 |

---

## 五、服务层 (`src/services/`)

| 服务 | 路径 | 功能 |
|------|------|------|
| API Client | `api/` | Anthropic API调用、文件API、bootstrap |
| MCP | `mcp/` | Model Context Protocol服务器连接管理 |
| OAuth | `oauth/` | OAuth 2.0认证流程 |
| LSP | `lsp/` | Language Server Protocol管理器 |
| Analytics | `analytics/` | GrowthBook特性开关和数据分析 |
| Plugins | `plugins/` | 插件加载器 |
| Compact | `compact/` | 对话上下文压缩 |
| Memory | `extractMemories/` | 自动记忆提取 |
| Team Sync | `teamMemorySync/` | 团队记忆同步 |

---

## 六、权限系统

### 权限模式
```typescript
type PermissionMode = 
  | 'default'      // 默认询问
  | 'plan'        // 计划模式
  | 'bypassPermissions'  // 跳过权限
  | 'auto'        // 自动决策
```

### 权限检查点
- 工具调用前检查
- Bash命令执行
- 文件读写操作
- 网络请求
- 外部API调用

---

## 七、组件系统 (`src/components/`)

### UI组件 (~140个)
使用 **Ink** (React for CLI) 构建:
- `PromptInput/` - 输入框组件
- `messages/` - 消息渲染
- `permissions/` - 权限对话框
- `settings/` - 设置界面
- `agents/` - Agent管理UI
- `tree/` - 目录树

---

## 八、Bridge系统 (IDE集成)

### 支持的IDE
- VS Code
- JetBrains

### 功能
- 双向通信
- 权限回调
- 会话桥接
- JWT认证

---

## 九、特性开关

使用 Bun 的 `bun:bundle` 特性标志:

```typescript
import { feature } from 'bun:bundle'

const voiceCommand = feature('VOICE_MODE') 
  ? require('./commands/voice/index.js').default 
  : null
```

### 已知特性
- `PROACTIVE` - 主动模式
- `KAIROS` - 时间相关
- `BRIDGE_MODE` - 桥接模式
- `DAEMON` - 守护进程
- `VOICE_MODE` - 语音模式
- `AGENT_TRIGGERS` - Agent触发器
- `MONITOR_TOOL` - 工具监控

---

## 十、对VJ-Gen的参考价值

### 可借鉴的设计

1. **工具系统**
   - 统一的工具接口设计
   - 权限模型
   - 工具注册机制

2. **命令系统**
   - Slash命令解析
   - 命令注册表

3. **Agent系统**
   - 子AgentSpawn机制
   - 团队协作 (`TeamCreateTool`)
   - 任务管理 (`TaskCreateTool`)

4. **服务架构**
   - 模块化服务设计
   - API客户端封装
   - 插件系统

5. **UI组件**
   - Ink CLI UI模式
   - 表格/列表组件
   - 进度显示

### 具体参考实现

```typescript
// 1. 工具基类
class BaseTool {
  name: string
  description: string
  inputSchema: z.ZodType
  permission: PermissionMode
  
  async execute(input: any): Promise<ToolResult>
}

// 2. 统一Adapter接口 (参考VJ-Gen架构)
interface BaseAdapter {
  provider: string
  model: string
  invoke(input: any): Promise<any>
  healthCheck(): Promise<boolean>
}

// 3. 任务队列设计
interface TaskNode {
  id: string
  type: string
  status: TaskStatus
  depends_on: string[]
}
```

---

## 十一、文件统计

| 文件 | 大小 | 行数 |
|------|------|------|
| main.tsx | 803KB | ~4,683行 |
| interactiveHelpers.tsx | 57KB | ~365行 |
| query.ts | 68KB | ~1,729行 |
| QueryEngine.ts | 46KB | ~1,295行 |
| Tool.ts | 29KB | ~792行 |
| commands.ts | 25KB | ~754行 |
| dialogLaunchers.tsx | 23KB | ~132行 |

**总计**: ~1,900文件, 512,000+行代码

---

## 十二、技术栈总结

```
┌─────────────────────────────────────────┐
│           CLI UI (Ink/React)            │
├─────────────────────────────────────────┤
│           Commands (~50)               │
├─────────────────────────────────────────┤
│           Tools (~40)                  │
├─────────────────────────────────────────┤
│         Query Engine (LLM)             │
├─────────────────────────────────────────┤
│          Services Layer                │
│   (API, MCP, OAuth, LSP, Analytics)    │
├─────────────────────────────────────────┤
│          Anthropic API                 │
└─────────────────────────────────────────┘
```

---

*分析完成 | 2026-04-02*
