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

### 配置参考

以下是一个完整的 `GitLab CI` 配置示例，说明了如何在 `GitLab CI/CD` 中使用该脚本来自动化部署。

```yaml
stages:
  - deploy

deploy:
  stage: deploy
  image: yuwei1228/gitlab-portainer-deploy  # 使用自定义的 Docker 镜像
  script:
    - python /app/deploy.py --URL "$PORTAINER_URL" --USERNAME "$PORTAINER_USERNAME" --PASSWORD "$PORTAINER_PASSWORD" --STACK "$PORTAINER_STACK" --ENDPOINT "$PORTAINER_ENDPOINT"
  tags:
    - docker
```