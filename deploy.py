import argparse
import json
import requests
import yaml
import time


def info(message):
    print(f"\033[34m📋 {message}\033[0m")


def warn(message):
    print(f"\033[33m⚠️ {message}\033[0m")


def error(message):
    print(f"\033[31m❌ {message}\033[0m")


def success(message):
    print(f"\033[32m✅ {message}\033[0m")


def login(url, username, password):
    data = {
        "username": username,
        "password": password
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(f"{url}/api/auth", json=data, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    return response_data.get('jwt')


def get_stack_id(url, jwt, stack_name):
    headers = {
        "Authorization": f"Bearer {jwt}"
    }
    response = requests.get(f"{url}/api/stacks", headers=headers)
    response.raise_for_status()
    stacks = response.json()
    for stack in stacks:
        if stack['Name'] == stack_name:
            return stack['Id']
    return None


def get_stack_file(url, stack_id, jwt_token):
    headers = {
        "Authorization": f"Bearer {jwt_token}"
    }
    response = requests.get(f"{url}/api/stacks/{stack_id}/file", headers=headers)
    response.raise_for_status()
    return response.json().get('StackFileContent')


def update_stack(url, jwt, stack_id, stack_file_content, endpoint_id):
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }
    data = {
        "stackFileContent": stack_file_content,
        "prune": True
    }
    response = requests.put(
        f"{url}/api/stacks/{stack_id}?endpointId={endpoint_id}",
        json=data,
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def check_container_health(url, jwt, endpoint_id, stack_name, timeout=300):
    headers = {
        "Authorization": f"Bearer {jwt}"
    }
    filters = json.dumps({"label": [f"com.docker.compose.project={stack_name}"]})
    deadline = time.time() + timeout

    while time.time() < deadline:
        response = requests.get(
            f"{url}/api/endpoints/{endpoint_id}/docker/containers/json",
            headers=headers,
            params={"filters": filters, "all": True}
        )

        if response.status_code != 200:
            error(f"请求失败，状态码：{response.status_code}")
            return False

        containers = response.json()

        if not containers:
            error("没有找到相关容器，检查是否正确启动")
            return False

        any_starting = False
        any_unhealthy = False

        for container in containers:
            container_id = container.get('Id')

            detail_resp = requests.get(
                f"{url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/json",
                headers=headers
            )

            if detail_resp.status_code != 200:
                error(f"获取容器详情失败，容器ID: {container_id}")
                return False

            detail = detail_resp.json()
            health = detail.get('State', {}).get('Health')

            if not health:
                warn(f"容器 {container_id} 没有健康检查配置")
                return False

            health_status = health.get('Status')

            if health_status == 'starting':
                any_starting = True
            elif health_status == 'unhealthy':
                error(f"检测到容器 {container_id} unhealthy，打印最近 200 行日志：")
                log_params = {
                    "stdout": True,
                    "stderr": True,
                    "tail": 200
                }
                logs_resp = requests.get(
                    f"{url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/logs",
                    headers=headers,
                    params=log_params
                )
                if logs_resp.status_code == 200:
                    print(logs_resp.text)
                    info("Please check the logs.")
                else:
                    error(f"获取日志失败，状态码：{logs_resp.status_code}")
                any_unhealthy = True
            elif health_status == 'healthy':
                continue
            else:
                error(f"未知健康状态: {health_status}")
                return False

        if any_unhealthy:
            return False

        if any_starting:
            time.sleep(5)
            continue

        return True

    error("超时，容器未全部通过健康检查")
    return False


def modify_stack_file(updated_stack_file, IMAGE_TAG="latest"):
    try:
        stack_config = yaml.safe_load(updated_stack_file)
        for service_config in stack_config.get('services', {}).values():
            if 'image' in service_config:
                image_full = service_config['image']
                if ':' in image_full:
                    image_name, _ = image_full.rsplit(':', 1)
                else:
                    image_name = image_full
                service_config['image'] = f"{image_name}:{IMAGE_TAG}"
        return yaml.dump(stack_config)
    except Exception as e:
        error(f"修改镜像标签失败: {e}")
        return updated_stack_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--URL', required=True)
    parser.add_argument('--USERNAME', required=True)
    parser.add_argument('--PASSWORD', required=True)
    parser.add_argument('--STACK', required=True)
    parser.add_argument('--ENDPOINT', required=True)
    parser.add_argument('--IMAGE_TAG', default="latest", help="镜像标签（默认: latest）")
    args = parser.parse_args()

    jwt_token = login(args.URL, args.USERNAME, args.PASSWORD)

    stack_id = get_stack_id(args.URL, jwt_token, args.STACK)

    stack_file = get_stack_file(args.URL, stack_id, jwt_token)

    updated_stack_file = modify_stack_file(stack_file, args.IMAGE_TAG)

    UpdateDate = update_stack(args.URL, jwt_token, stack_id, updated_stack_file, args.ENDPOINT)
    print(f"⏳ Start Update, Update Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(UpdateDate['UpdateDate']))}, Update By: {UpdateDate['UpdatedBy']}")

    if not check_container_health(args.URL, jwt_token, args.ENDPOINT, args.STACK):
        UpdateDate = update_stack(args.URL, jwt_token, stack_id, stack_file, args.ENDPOINT)
        error("Update failed: Containers did not pass health checks, start rollback.")
        print(f"🔄 Start Rollback, Rollback Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(UpdateDate['UpdateDate']))}, Rollback By: {UpdateDate['UpdatedBy']}")

        if not check_container_health(args.URL, jwt_token, args.ENDPOINT, args.STACK):
            raise Exception("❌ Rollback failed")
        success("rollback completed.")
        raise Exception("Update failed")

    success(f"✅ Update Success, Time : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
