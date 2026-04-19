# GoLand 本地调试

这份说明面向当前仓库在 macOS 上的 GoLand 本地调试。

## 1. 先准备 Go SDK

当前各个 Go 模块都声明了：

```text
go 1.24.0
```

在 GoLand 里设置：

1. 打开 `GoLand -> Settings -> Go -> GOROOT`
2. 添加本机 Go SDK
3. 版本至少选择 `1.24.x`

常见 macOS 安装路径：

- Homebrew Intel: `/usr/local/opt/go/libexec`
- Homebrew Apple Silicon: `/opt/homebrew/opt/go/libexec`
- 官方安装包: `/usr/local/go`

如果这几个路径都不存在，先安装 Go，再回到 GoLand 设置 GOROOT。

## 2. 设置 GOPROXY

截图里的提示说明当前 IDE 没有可用的模块代理。

建议在 `GoLand -> Settings -> Go -> Go Modules` 中设置：

```text
GOPROXY=https://goproxy.cn,direct
```

如果你不想走国内代理，也可以用：

```text
GOPROXY=https://proxy.golang.org,direct
```

## 3. 以仓库根目录打开项目

直接用仓库根目录打开：

```text
electric-ai-platform
```

仓库已经包含 `go.work`，GoLand 会把各个服务模块一起识别出来，不需要手动写 `replace`。

## 4. 先启动本地依赖

Go 服务依赖 MySQL 和 Redis。

在 GoLand 终端或系统终端里执行：

```bash
./scripts/dev-up.sh
```

关闭依赖时执行：

```bash
./scripts/dev-down.sh
```

默认端口：

- MySQL: `127.0.0.1:3307`
- Redis: `127.0.0.1:6380`

## 5. GoLand Run Configuration 怎么配

对每个服务都按下面配置：

1. `Run -> Edit Configurations`
2. 新建 `Go Build`
3. `Run kind` 选 `File`
4. `Files` 选择目标服务的 `cmd/server/main.go`
5. `Working directory` 指到目标服务目录

示例：

- `auth-service`
  - File: `services/auth-service/cmd/server/main.go`
  - Working directory: `services/auth-service`
- `gateway-service`
  - File: `services/gateway-service/cmd/server/main.go`
  - Working directory: `services/gateway-service`

## 6. 环境变量怎么加载

当前仓库的 Go 配置加载规则是：

- 优先保留 GoLand 显式注入的环境变量
- 然后读取工作目录向上的 `.env` / `.env.local`
- 离当前服务更近的 `.env.local` 会覆盖父目录同名项

所以只要 `Working directory` 指到正确服务目录，服务级 `.env.local` 就会自动生效。

## 7. 前端为什么会报 `127.0.0.1:8080` 连接失败

`web-console` 的 Vite 代理固定转发到：

```text
http://127.0.0.1:8080
```

也就是 `gateway-service`。

因此前端报：

```text
connect ECONNREFUSED 127.0.0.1:8080
```

通常不是前端问题，而是 `gateway-service` 没启动。

最少要先跑起来：

- `auth-service`
- `model-service`
- `task-service`
- `asset-service`
- `audit-service`
- `gateway-service`

然后前端开发服务器再访问 `http://127.0.0.1:5173`。
