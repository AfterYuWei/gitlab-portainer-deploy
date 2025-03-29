自用的portianer的部署脚本

参考配置：
``` yml
stages:
  - deploy

deploy:
  stage: deploy
  image: xxx/gitlab-portainer-deploy
  script:
    - python /app/deploy.py \
        --URL "$PORTAINER_URL" \
        --USERNAME "$PORTAINER_USERNAME" \
        --PASSWORD "$PORTAINER_PASSWORD" \
        --STACK "$PORTAINER_STACK" \
        --ENDPOINT "$PORTAINER_ENDPOINT"
  tags:
    - docker
```