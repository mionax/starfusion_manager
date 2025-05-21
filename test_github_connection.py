import requests
import sys

url = "https://raw.githubusercontent.com/mionax/starfusion-workflows/main/README.md"

try:
    print(f"尝试访问: {url}")
    response = requests.get(url, timeout=10) # 设置超时时间
    response.raise_for_status() # 检查HTTP错误
    print("成功连接到 raw.githubusercontent.com")
    print(f"状态码: {response.status_code}")
    # print("响应内容前200字符:")
    # print(response.text[:200])

except requests.exceptions.RequestException as e:
    print(f"访问 {url} 时出错:")
    print(e)
    # 打印更详细的错误信息，特别是关于SSL/TLS的
    if isinstance(e, requests.exceptions.SSLError):
        print("SSL 错误：请检查你的证书配置或网络环境。")
    elif isinstance(e, requests.exceptions.ConnectionError):
         print("连接错误：请检查防火墙、代理设置或网络连接。")
    elif isinstance(e, requests.exceptions.Timeout):
         print("请求超时：网络连接可能不稳定或速度较慢。")
    print("请根据错误信息排查问题。")

except Exception as e:
    print(f"发生意外错误: {e}")
    print(sys.exc_info()) 