import requests
import os


# 获取环境变量
OAUTH2_INTROSPECT_URL = os.getenv("OAUTH2_INTROSPECT_URL")
OAUTH2_TOKEN_URL = os.getenv("OAUTH2_TOKEN_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

def verify_token(token):
    """
    验证访问令牌的有效性
    使用 OAuth2 服务器的 introspection endpoint 来验证令牌
    """
    try:
        resp = requests.post(
            OAUTH2_INTROSPECT_URL,
            data={"token": token},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        result = resp.json()
        return result.get("active", False)
    except Exception:
        return False

def get_access_token():
    """
    从 OAuth2 服务器获取访问令牌
    使用 client_credentials 授权类型
    """
    try:
        response = requests.post(
            OAUTH2_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving access token: {e}")
        return None