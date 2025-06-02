import lzma
import base64
import os
import secrets
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def xor_encrypt(data, key):
    """XOR加密层"""
    if isinstance(data, str):
        data = data.encode('utf-8')

    # 确保密钥是字节类型
    if isinstance(key, str):
        key = key.encode('utf-8')

    # 创建循环密钥以匹配数据长度
    key_cycle = bytearray()
    for i in range(len(data)):
        key_cycle.append(key[i % len(key)])

    # 执行XOR操作
    result = bytearray()
    for i in range(len(data)):
        result.append(data[i] ^ key_cycle[i])

    return bytes(result)


def derive_key_from_password(password, salt=None):
    """使用PBKDF2从密码派生Fernet密钥"""
    if salt is None:
        salt = os.urandom(16)

    if isinstance(password, str):
        password = password.encode('utf-8')

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key, salt


def multi_encrypt_code(source_code, password=None):
    """使用多层加密对源代码进行加密"""
    # 如果没有提供密码，则生成随机密码
    if password is None:
        password = secrets.token_hex(16)

    # 第1层：使用LZMA压缩
    compressed = lzma.compress(source_code.encode('utf-8'))

    # 第2层：生成随机XOR密钥
    xor_key = os.urandom(16)
    xor_encrypted = xor_encrypt(compressed, xor_key)

    # 第3层：使用Fernet进行AES加密
    fernet_key, salt = derive_key_from_password(password)
    fernet = Fernet(fernet_key)
    aes_encrypted = fernet.encrypt(xor_encrypted)

    # 第4层：最终的Base64编码
    final_encoded = base64.b64encode(aes_encrypted).decode('utf-8')

    # 返回解密所需的所有组件
    return {
        'encrypted_data': final_encoded,
        'password': password,
        'xor_key': base64.b64encode(xor_key).decode('utf-8'),
        'salt': base64.b64encode(salt).decode('utf-8')
    }


def create_encrypted_script(source_code, password=None, add_obfuscation=True):
    """创建具有多层加密的自解密脚本"""
    # 加密源代码
    encryption_result = multi_encrypt_code(source_code, password)

    # 提取加密组件
    encrypted_data = encryption_result['encrypted_data']
    password = encryption_result['password']
    xor_key = encryption_result['xor_key']
    salt = encryption_result['salt']

    # 如果请求，创建额外的混淆
    obfuscation_code = ""
    if add_obfuscation:
        obfuscation_code = """
# 反调试和环境检查
import sys
import time
import inspect
import platform

def check_environment():
    \"\"\"简单的环境验证\"\"\"
    # 检查是否在调试器中运行
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace and gettrace():
        print("警告：检测到调试器")
        time.sleep(random.uniform(1, 3))  # 添加随机延迟

    # 检查是否在虚拟环境中运行
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("注意：在虚拟环境中运行")

    # 稍微随机化执行流程
    if random.random() > 0.5:
        time.sleep(random.uniform(0.1, 0.3))

# 执行环境检查
check_environment()
"""

    # 创建自解密脚本
    script = f'''import lzma
import base64
import os
import hashlib
import random
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

{obfuscation_code}

# 加密参数
encrypted_data = '{encrypted_data}'
xor_key = '{xor_key}'
salt = '{salt}'
password = '{password}'

def xor_decrypt(data, key):
    """XOR解密函数"""
    if isinstance(key, str):
        key = base64.b64decode(key.encode('utf-8'))

    # 创建循环密钥以匹配数据长度
    key_cycle = bytearray()
    for i in range(len(data)):
        key_cycle.append(key[i % len(key)])

    # 执行XOR操作
    result = bytearray()
    for i in range(len(data)):
        result.append(data[i] ^ key_cycle[i])

    return bytes(result)

def derive_key(password, salt):
    """从密码和盐派生Fernet密钥"""
    if isinstance(password, str):
        password = password.encode('utf-8')

    if isinstance(salt, str):
        salt = base64.b64decode(salt.encode('utf-8'))

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

try:
    # 第4层：Base64解码
    encrypted_content = base64.b64decode(encrypted_data.encode('utf-8'))

    # 第3层：AES解密
    fernet_key = derive_key(password, salt)
    fernet = Fernet(fernet_key)
    xor_encrypted = fernet.decrypt(encrypted_content)

    # 第2层：XOR解密
    compressed_content = xor_decrypt(xor_encrypted, xor_key)

    # 第1层：LZMA解压缩
    script_content = lzma.decompress(compressed_content).decode('utf-8')

    # 执行解密后的代码
    exec(script_content)
except Exception as e:
    print(f"脚本执行过程中出错: {{e}}")
'''
    return script


if __name__ == "__main__":
    # 获取用户输入的源代码文件
    source_file = input("请输入要加密的Python文件路径: ")

    if not os.path.exists(source_file):
        print(f"错误: 文件 '{source_file}' 不存在!")
        exit(1)

    # 询问是否使用密码或生成密码
    use_password = input("您想使用自定义密码吗? (y/n): ").lower() == 'y'
    password = None
    if use_password:
        password = input("输入您的密码 (将会显示): ")

    # 询问是否添加额外的混淆
    add_obfuscation = input("您想添加额外的混淆吗? (y/n): ").lower() == 'y'

    # 读取源代码
    with open(source_file, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # 创建加密脚本
    encrypted_script = create_encrypted_script(source_code, password, add_obfuscation)

    # 保存加密后的脚本
    output_file = os.path.splitext(source_file)[0] + "_encrypted.py"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(encrypted_script)

    print(f"加密完成! 已保存到 {output_file}")
    if password:
        print(f"密码: {password} (请保密)")
    else:
        print("已生成随机密码并嵌入脚本中")
    print("该文件可以直接运行，会自动解密并执行您的原始代码。")