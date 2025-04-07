import argparse
from datetime import datetime, timedelta
import json

import pytz
import requests
import yaml


def login(url, username, password):
    # 构造请求数据
    data = {
        "username": username,
        "password": password
    }

    # 构造请求头
    headers = {
        "Content-Type": "application/json"
    }

    # 发送 POST 请求
    response = requests.post(f"{url}/api/auth", json=data, headers=headers)

    # 如果请求成功，检查返回的状态码
    response.raise_for_status()  # 如果返回状态码不是2xx，会抛出异常

    # 解析返回的 JSON 响应
    response_data = response.json()

    return response_data.get('jwt')


def get_stack_id(url, jwt, stack_name):
    # 构造请求头
    headers = {
        "Authorization": f"Bearer {jwt}"
    }

    # 发送 GET 请求以获取所有 stacks
    response = requests.get(f"{url}/api/stacks", headers=headers)
    response.raise_for_status()

    # 解析返回的 JSON 响应
    stacks = response.json()

    # 查找对应 stack_name 的 stack_id
    for stack in stacks:
        if stack['Name'] == stack_name:
            return stack['Id']

    return None


def get_stack_file(url, stack_id, jwt_token, image_tag="latest"):
    # 构造请求头，包含 Bearer token
    headers = {
        "Authorization": f"Bearer {jwt_token}"
    }

    # 发送 GET 请求获取 stack file 内容
    response = requests.get(f"{url}/api/stacks/{stack_id}/file", headers=headers)

    # 如果请求成功，检查返回的状态码
    response.raise_for_status()

    # 解析返回的 JSON 响应
    stack_file_content = response.json().get('StackFileContent')

    # 如果没有内容或不是 YAML，直接返回
    if not stack_file_content:
        return stack_file_content

    # 修改镜像标签
    try:
        stack_config = yaml.safe_load(stack_file_content)
        for service_config in stack_config.get('services', {}).values():
            if 'image' in service_config:
                image_full = service_config['image']
                # 使用 rsplit 防止替换掉端口号
                if ':' in image_full:
                    image_name, _ = image_full.rsplit(':', 1)
                else:
                    image_name = image_full
                service_config['image'] = f"{image_name}:{image_tag}"
        return yaml.dump(stack_config)
    except Exception as e:
        print(f"修改镜像标签失败: {e}")
        return stack_file_content  # 出错时返回原始内容


def update_stack(url, jwt, stack_id, stack_file_content, endpoint_id):
    """更新指定stack的stackFileContent"""
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }

    # 构建更新请求的数据
    data = {
        "stackFileContent": stack_file_content,
        "prune": True
    }

    # 发送 PUT 请求
    response = requests.put(
        f"{url}/api/stacks/{stack_id}?endpointId={endpoint_id}",
        json=data,
        headers=headers
    )

    response.raise_for_status()  # 确保请求成功

    # 返回更新后的stack信息
    return response.json()


import time


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
            params={"filters": filters}
        )

        if response.status_code != 200:
            print(f"请求失败，状态码：{response.status_code}")
            return False

        containers = response.json()

        if not containers:
            print("没有找到相关容器，检查是否正确启动")
            return False

        all_healthy = True

        # 检查每个容器的健康状态
        for container in containers:
            container_id = container.get('Id')
            status = container.get('Status', '')

            # 检查 Status 是否包含 "(healthy)"
            if '(healthy)' not in status:
                all_healthy = False

        # 如果所有容器都健康，返回True
        if all_healthy:
            return True

        time.sleep(5)  # 每次循环等待5秒再重试

    print("超时，容器未全部通过健康检查")
    return False


if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser()
    parser.add_argument('--URL', required=True)
    parser.add_argument('--USERNAME', required=True)
    parser.add_argument('--PASSWORD', required=True)
    parser.add_argument('--STACK', required=True)
    parser.add_argument('--ENDPOINT', required=True)
    parser.add_argument('--IMAGE_TAG', default="latest", help="镜像标签（默认: latest）")
    args = parser.parse_args()

    # 获取JWT
    jwt_token = login(args.URL, args.USERNAME, args.PASSWORD)

    # 获取 stack_id
    stack_id = get_stack_id(args.URL, jwt_token, args.STACK)

    # 获取并自动修改 Stack 文件
    updated_stack_file = get_stack_file(args.URL, stack_id, jwt_token, args.IMAGE_TAG)

    # 提交更新
    UpdateDate = update_stack(args.URL, jwt_token, stack_id, updated_stack_file, args.ENDPOINT)
    print("Start Update")

    # 检查健康状态
    if not check_container_health(args.URL, jwt_token, args.ENDPOINT, args.STACK):
        raise Exception("❌ 更新失败：容器未全部通过健康检查")

    print("🎉 更新完成, 完成时间:", (datetime.fromtimestamp(UpdateDate['UpdateDate'], tz=pytz.UTC) + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'))