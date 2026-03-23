import requests
try:
    # 随便请求一个音乐平台的网址，看是否能通
    res = requests.get("https://y.qq.com", timeout=5)
    print("网络请求成功，状态码:", res.status_code)
except Exception as e:
    print("网络请求失败:", e)