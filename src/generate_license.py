# generate_license.py

import json
import argparse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


def generate_license(secret_key: bytes, user_email: str, license_id: str, output_path: str):
    """
    生成加密的许可证文件。

    参数：
        secret_key (bytes): 用于加密的密钥。
        user_email (str): 用户的电子邮件地址。
        license_id (str): 许可证 ID。
        output_path (str): 输出许可证文件的路径。
    """
    license_data = {
        "user": user_email,
        "license_id": license_id,
        "bound_fingerprint": None,
        "issued_at": "2025-05-30",
        "valid_until": "2026-05-30"
    }

    raw = json.dumps(license_data).encode()
    cipher = AES.new(secret_key, AES.MODE_CBC, iv=secret_key[:16])
    encrypted = cipher.encrypt(pad(raw, AES.block_size))

    with open(output_path, "wb") as f:
        f.write(encrypted)

    print(f"License generated and saved to {output_path}")


if __name__ == "__main__":
    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser(description="Generate an encrypted license file.")
    parser.add_argument("--secret-key", required=True, help="Secret key for license encryption.")
    parser.add_argument("--user-email", required=True, help="User email for the license.")
    parser.add_argument("--license-id", required=True, help="License ID.")
    parser.add_argument("--output-path", default="license.dat", help="Path to save the generated license file.")
    args = parser.parse_args()

    # 将 SECRET_KEY 转换为字节
    secret_key = args.secret_key.encode()

    # 调用生成许可证函数
    generate_license(secret_key, args.user_email, args.license_id, args.output_path)