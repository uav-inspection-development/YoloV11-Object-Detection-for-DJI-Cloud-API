# generate_license.py

import json
import argparse
from datetime import datetime
from typing import List

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from src.license_features import DEFAULT_FEATURES


def generate_license(
    secret_key: bytes,
    user_email: str,
    license_id: str,
    valid_until: str,
    output_path: str,
    features: List[str],
) -> None:
    """
    生成加密的许可证文件。

    参数：
        secret_key (bytes): 用于加密的密钥。
        user_email (str): 用户的电子邮件地址。
        license_id (str): 许可证 ID。
        valid_until (str): 许可证的有效期，格式为 "YYYY-MM-DD"。如果为 "None"，则表示无过期日期。
        output_path (str): 输出许可证文件的路径。
    """
    # 获取当前日期作为 issued_at
    issued_at = datetime.now().strftime("%Y-%m-%d")

    # 如果 valid_until 为 "None"，设置为无过期日期
    if valid_until == "None":
        valid_until = "9999-12-31"

    license_data = {
        "user": user_email,
        "license_id": license_id,
        "bound_fingerprint": None,
        "issued_at": issued_at,
        "valid_until": valid_until,
        "features": features,
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
    parser.add_argument("--valid-until", default="None", help="License expiration date (YYYY-MM-DD). Default is no expiration.")
    parser.add_argument("--output-path", default="license.dat", help="Path to save the generated license file.")
    parser.add_argument(
        "--features",
        nargs="*",
        choices=DEFAULT_FEATURES,
        default=DEFAULT_FEATURES,
        help="Enabled features for the license. Default enables all.",
    )
    args = parser.parse_args()

    # 将 SECRET_KEY 转换为字节
    secret_key = args.secret_key.encode()

    # 调用生成许可证函数
    generate_license(
        secret_key,
        args.user_email,
        args.license_id,
        args.valid_until,
        args.output_path,
        args.features,
    )
