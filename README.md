
# Portainer Stack 自动部署工具

该工具用于通过 Portainer API 自动更新指定堆栈中的服务镜像，并支持部署失败后的自动回滚。适用于 GitLab CI/CD 自动化部署场景，已内置健康检查机制，确保服务稳定后才认为部署成功。

---

## 📦 使用方式

通过命令行运行 `deploy.py`，或在 GitLab CI 的 `deploy` 阶段中集成该工具。

### 命令行参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--URL` | ✅ | Portainer 面板地址，例如 `http://portainer.local:9000` |
| `--USERNAME` | ✅ | 登录 Portainer 的用户名 |
| `--PASSWORD` | ✅ | 登录 Portainer 的密码 |
| `--ENVIRONMENT` | ✅ | Portainer 中的环境名称（非 ID） |
| `--STACK` | ✅ | 堆栈（Stack）名称 |
| `--SERVICE` | ✅ | 要更新的服务名（服务名必须在 docker-compose.yml 的 services 中定义） |
| `--IMAGE` | ✅ | 要更新为的镜像名（**强烈建议包含 tag，例如 `api:1.0.1`**） |
| `--ROLLBACK` | 可选 | 如果部署失败则自动回滚 |
| `--TIMEOUT` | 可选 | 健康检查的最长等待时间，默认 300 秒 |

---

## 🧪 示例命令

```bash
python deploy.py \
  --URL "http://portainer.local:9000" \
  --USERNAME "admin" \
  --PASSWORD "yourpassword" \
  --ENVIRONMENT "local" \
  --STACK "my_stack" \
  --SERVICE "api" \
  --IMAGE "registry.example.com/project/api:1.0.1" \
  --ROLLBACK
```

---

## 🧰 GitLab CI 集成示例

以下为 `.gitlab-ci.yml` 中的 `deploy` 阶段配置：

```yaml
deploy:
  stage: deploy
  image: yuwei1228/gitlab-portainer-deploy:latest
  script:
    - python /app/deploy.py --URL "$PORTAINER_URL" --USERNAME "$PORTAINER_USERNAME" --PASSWORD "$PORTAINER_PASSWORD" --ENVIRONMENT "local" --STACK "yuwei_home" --SERVICE "api" --IMAGE ${API_IMAGE_NAME} --ROLLBACK
    - python /app/deploy.py --URL "$PORTAINER_URL" --USERNAME "$PORTAINER_USERNAME" --PASSWORD "$PORTAINER_PASSWORD" --ENVIRONMENT "local" --STACK "yuwei_home" --SERVICE "ui" --IMAGE ${UI_IMAGE_NAME} --ROLLBACK
  tags:
    - ruoyi
```

> 💡 **建议：**
> - `API_IMAGE_NAME` 和 `UI_IMAGE_NAME` 应包含镜像 tag，例如：  
>   `export API_IMAGE_NAME=registry.example.com/project/api:${CI_COMMIT_SHORT_SHA}`

---

## 🛡️ 健康检查机制

- 工具会等待新容器启动并进入 `healthy` 状态；
- 如果容器 `unhealthy` 或超时未进入 `healthy`，视为部署失败；
- 启用 `--ROLLBACK` 可在失败时自动恢复至旧版本镜像。

---

## 🧩 依赖环境

- Python 3.6+
- 安装依赖项（仅本地测试时需要）：
  ```bash
  pip install requests pyyaml
  ```

---