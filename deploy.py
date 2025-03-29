import argparse
import json
import requests


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

def get_stack_file(url, stack_id, jwt_token):
    # 构造请求头，包含 Bearer token
    headers = {
        "Authorization": f"Bearer {jwt_token}"
    }

    # 发送 GET 请求获取 stack file 内容
    response = requests.get(f"{url}/api/stacks/{stack_id}/file", headers=headers)

    # 如果请求成功，检查返回的状态码
    response.raise_for_status()

    # 解析返回的 JSON 响应
    response_data = response.json()

    # 返回 StackFileContent 字段
    return response_data.get('StackFileContent')


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



if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser()
    parser.add_argument('--URL', required=True)
    parser.add_argument('--USERNAME', required=True)
    parser.add_argument('--PASSWORD', required=True)
    parser.add_argument('--STACK', required=True)
    parser.add_argument('--ENDPOINT', required=True)
    args = parser.parse_args()

    # 获取JWT
    jwt_token = login(args.URL, args.USERNAME, args.PASSWORD)

    # 获取 stack_id
    stack_id = get_stack_id(args.URL, jwt_token, args.STACK)

    # 使用 JWT 获取 docker compose 内容
    stack_file = get_stack_file(args.URL, stack_id, jwt_token)

    # 更新指定的stack
    UpdateDate = update_stack(args.URL, jwt_token, stack_id, stack_file, args.ENDPOINT)

    print(UpdateDate)