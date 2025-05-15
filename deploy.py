import argparse
import requests
import yaml
import sys

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

    def deploy(self, env_name, stack_name, service, new_image, rollback=False):
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
            print("[INFO] 部署成功")
        else:
            print(f"[ERROR] 部署失败: {res.status_code} {res.text}")
            if rollback:
                print("[INFO] 开始回滚...")
                rollback_res = self.update_stack(stack_id, env_id, orig_stack_file, stack.get('Env', []))
                if rollback_res.status_code == 200:
                    print("[INFO] 回滚成功")
                else:
                    print(f"[ERROR] 回滚失败: {rollback_res.status_code} {rollback_res.text}")


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
    args = parser.parse_args()

    updater = PortainerUpdater(args.URL, args.USERNAME, args.PASSWORD)
    updater.deploy(
        env_name=args.ENVIRONMENT,
        stack_name=args.STACK,
        service=args.SERVICE,
        new_image=args.IMAGE,
        rollback=args.ROLLBACK
    )


if __name__ == '__main__':
    main()
