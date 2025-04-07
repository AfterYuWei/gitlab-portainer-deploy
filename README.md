
# 自用 Portainer 部署脚本

该脚本旨在通过 Portainer 自动化部署 Stack，使用 Docker Compose 部署的 stack 会自动根据创建的文件进行部署。只需根据配置文件中的参数信息，脚本会自动根据 Stack 名称获取对应的 Stack ID 并完成更新操作。

## 配置说明

### 环境变量

在运行部署脚本之前，需要配置以下环境变量：

- `PORTAINER_URL`：Portainer 实例的 URL 地址。
- `PORTAINER_USERNAME`：登录 Portainer 的用户名。
- `PORTAINER_PASSWORD`：登录 Portainer 的密码。
- `PORTAINER_STACK`：要部署的 Stack 名称。
- `PORTAINER_ENDPOINT`：指定 Portainer 的 endpoint，用于获取相关的 stack 列表和信息。
- `IMAGE_TAG`：可选，指定要更新的镜像标签，默认为 `latest`。

### 运行脚本

1. 克隆或下载本仓库中的 `deploy.py` 文件。
2. 确保你已安装 `requests` 和 `pyyaml` 库，或者你可以直接通过 Docker 来运行脚本。 
3. 使用以下命令在本地运行脚本：

```bash
python deploy.py --URL <PORTAINER_URL> --USERNAME <PORTAINER_USERNAME> --PASSWORD <PORTAINER_PASSWORD> --STACK <PORTAINER_STACK> --ENDPOINT <PORTAINER_ENDPOINT> --IMAGE_TAG <IMAGE_TAG>
```

### 配置参考

以下是一个完整的 `GitLab CI` 配置示例，说明了如何在 `GitLab CI/CD` 中使用该脚本来自动化部署。

```yaml
stages:
  - deploy

deploy:
  stage: deploy
  image: yuwei1228/gitlab-portainer-deploy  # 使用自定义的 Docker 镜像
  script:
    - python /app/deploy.py --URL "$PORTAINER_URL" --USERNAME "$PORTAINER_USERNAME" --PASSWORD "$PORTAINER_PASSWORD" --STACK "$PORTAINER_STACK" --ENDPOINT "$PORTAINER_ENDPOINT" --IMAGE_TAG "$IMAGE_TAG"
  tags:
    - docker
```

## 脚本功能

该脚本主要分为几个步骤：

1. **登录 Portainer**：通过 `username` 和 `password` 获取 JWT Token。
2. **获取 Stack ID**：根据提供的 `stack_name` 获取对应的 Stack ID。
3. **获取 Stack 文件**：下载并修改 Stack 的 YAML 文件中的镜像标签（如果需要），默认为 `latest` 标签。
4. **更新 Stack**：提交更新后的 Stack 文件，并触发更新操作。
5. **健康检查**：检查相关容器的健康状态，确保更新后的容器运行正常。如果超时或者容器状态不健康，脚本会抛出异常并报告失败。

## 依赖

此脚本依赖以下 Python 库：

- `requests`：用于发送 HTTP 请求。
- `pyyaml`：用于处理 YAML 配置文件。

你可以使用以下命令安装这些依赖：

```bash
pip install requests pyyaml
```

### Docker 方式运行

如果你不希望手动安装 Python 库，可以直接使用 Docker 来运行该脚本。以下是示例 Dockerfile 配置：

```dockerfile
# 使用官方 Python 镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录为 /app
WORKDIR /app

# 将当前目录的内容复制到容器的 /app 目录
COPY . /app

# 安装项目的依赖
RUN pip install --no-cache-dir requests pyyaml

# 设置容器的默认命令
CMD ["python", "deploy.py"]
```

你可以通过以下命令来构建 Docker 镜像并运行容器：

```bash
docker build -t portainer-deploy .
docker run -e URL=<PORTAINER_URL> -e USERNAME=<PORTAINER_USERNAME> -e PASSWORD=<PORTAINER_PASSWORD> -e STACK=<PORTAINER_STACK> -e ENDPOINT=<PORTAINER_ENDPOINT> portainer-deploy
```

## 错误处理

- 如果在更新 Stack 或检查容器健康时发生错误，脚本会抛出异常并打印错误信息。
- 如果所有容器未通过健康检查，脚本会在超时后报告失败。
