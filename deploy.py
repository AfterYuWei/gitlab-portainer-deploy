import argparse
import requests
import yaml
import sys
import time

class PortainerUpdater:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.jwt = None
        self.headers = {}

    def login(self):
        res = requests.post(f"{self.base_url}/api/auth", json={
            "Username": self.username,
            "Password": self.password
        })
        res.raise_for_status()
        self.jwt = res.json().get("jwt")
        self.headers = {"Authorization": f"Bearer {self.jwt}"}
        print("[INFO] 登录成功")

    def get_environment_id(self, env_name):
        res = requests.get(f"{self.base_url}/api/endpoints", headers=self.headers)
        res.raise_for_status()
        for env in res.json():
            if env['Name'] == env_name:
                print(f"[INFO] 获取到环境ID: {env['Id']}")
                return env['Id']
        raise ValueError(f"未找到环境: {env_name}")

    def get_stack_info(self, stack_name, env_id):
        res = requests.get(f"{self.base_url}/api/stacks", headers=self.headers)
        res.raise_for_status()
        for stack in res.json():
            if stack['Name'] == stack_name and stack['EndpointId'] == env_id:
                print(f"[INFO] 获取到堆栈ID: {stack['Id']}")
                return stack
        raise ValueError(f"未找到堆栈: {stack_name}")

    def get_stack_file(self, stack_id, env_id):
        res = requests.get(f"{self.base_url}/api/stacks/{stack_id}/file", headers=self.headers, params={"endpointId": env_id})
        res.raise_for_status()
        return res.json().get("StackFileContent", "")

    def update_stack(self, stack_id, env_id, content, envs):
        payload = {
            "StackFileContent": content,
            "Env": envs,
            "Prune": True,
            "PullImage": True
        }
        res = requests.put(f"{self.base_url}/api/stacks/{stack_id}",
                           headers=self.headers,
                           params={"endpointId": env_id},
                           json=payload)
        return res

    def is_service_healthy(self, env_id, service_name, timeout=300):
        print("[INFO] 等待服务容器健康检查通过...")
        attempts = timeout // 3
        for _ in range(attempts):
            res = requests.get(f"{self.base_url}/api/endpoints/{env_id}/docker/containers/json", headers=self.headers)
            res.raise_for_status()
            containers = res.json()
            for container in containers:
                names = container.get("Names", [])
                if any(service_name in name for name in names):
                    container_id = container.get("Id")
                    detail_res = requests.get(f"{self.base_url}/api/endpoints/{env_id}/docker/containers/{container_id}/json", headers=self.headers)
                    detail_res.raise_for_status()
                    detail = detail_res.json()
                    health = detail.get("State", {}).get("Health", {}).get("Status")
                    cname = detail.get("Name", "<unknown>").lstrip("/")
                    status = health if health else detail.get("State", {}).get("Status", "unknown")
                    print(f"[INFO] 容器 {cname} 当前状态: {status}")
                    if health == "healthy":
                        return True
                    elif health == "unhealthy":
                        return False
            time.sleep(3)
        return False

    def deploy(self, env_name, stack_name, service, new_image, rollback=False, timeout=300):
        self.login()
        env_id = self.get_environment_id(env_name)
        stack = self.get_stack_info(stack_name, env_id)
        stack_id = stack['Id']
        orig_stack_file = self.get_stack_file(stack_id, env_id)
        orig_yaml = yaml.safe_load(orig_stack_file)

        if service not in orig_yaml.get('services', {}):
            raise ValueError(f"服务 {service} 不存在于堆栈中")

        old_image = orig_yaml['services'][service]['image']
        orig_yaml['services'][service]['image'] = new_image
        updated_yaml_content = yaml.dump(orig_yaml)

        print(f"[INFO] 更新服务 {service} 的镜像: {old_image} -> {new_image}")
        res = self.update_stack(stack_id, env_id, updated_yaml_content, stack.get('Env', []))

        if res.status_code == 200:
            healthy = self.is_service_healthy(env_id, service, timeout=timeout)
            if healthy:
                print("[INFO] 部署成功并健康")
            else:
                print("[ERROR] 容器未变为 healthy，视为失败")
                if rollback:
                    print("[INFO] 开始回滚...")
                    rollback_res = self.update_stack(stack_id, env_id, orig_stack_file, stack.get('Env', []))
                    if rollback_res.status_code == 200:
                        print("[INFO] 回滚成功")
                        raise RuntimeError("部署失败，已回滚")
                    else:
                        print(f"[ERROR] 回滚失败: {rollback_res.status_code} {rollback_res.text}")
                        raise RuntimeError("部署失败且回滚失败")
                else:
                    raise RuntimeError("部署失败，未启用回滚")
        else:
            print(f"[ERROR] 部署失败: {res.status_code} {res.text}")
            if rollback:
                print("[INFO] 开始回滚...")
                rollback_res = self.update_stack(stack_id, env_id, orig_stack_file, stack.get('Env', []))
                if rollback_res.status_code == 200:
                    print("[INFO] 回滚成功")
                    raise RuntimeError("部署失败，已回滚")
                else:
                    print(f"[ERROR] 回滚失败: {rollback_res.status_code} {rollback_res.text}")
                    raise RuntimeError("部署失败且回滚失败")
            else:
                raise RuntimeError("部署失败，未启用回滚")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--URL', required=True)
    parser.add_argument('--USERNAME', required=True)
    parser.add_argument('--PASSWORD', required=True)
    parser.add_argument('--ENVIRONMENT', required=True)
    parser.add_argument('--STACK', required=True)
    parser.add_argument('--SERVICE', required=True)
    parser.add_argument('--IMAGE', required=True)
    parser.add_argument('--ROLLBACK', action='store_true')
    parser.add_argument('--TIMEOUT', type=int, default=300, help='健康检查等待时间，单位秒')
    args = parser.parse_args()

    updater = PortainerUpdater(args.URL, args.USERNAME, args.PASSWORD)
    try:
        updater.deploy(
            env_name=args.ENVIRONMENT,
            stack_name=args.STACK,
            service=args.SERVICE,
            new_image=args.IMAGE,
            rollback=args.ROLLBACK,
            timeout=args.TIMEOUT
        )
    except Exception as e:
        print(f"[FATAL] 部署过程中发生错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
