from os.path import exists, isfile
from json import loads, dumps
from httpx import get, post
from sys import exit
import qrcode

def load_cookie() -> str:
    if exists("cookie.txt") and isfile("cookie.txt"):
        return open("cookie.txt").read()
    else:
        return ""


def login():
    global headers
    data = loads(get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate", headers=headers).text)[
        "data"]
    url = data["url"]
    key = data["qrcode_key"]
    code2: qrcode.QRCode = qrcode.QRCode()
    code2.add_data(url)
    print("请扫描二维码登录获取cookie")
    print("如果控制台输出有问题就打开当前目录下qrcode.png扫描")
    code2.print_ascii()
    code2.make_image().save("qrcode.png")
    while True:
        data = get("https://passport.bilibili.com/x/passport-login/web/qrcode/poll", params={"qrcode_key": key},
                   headers=headers)
        if loads(data.text)["data"]["code"] == 0:
            break
        if loads(data.text)["data"]["code"] == 86038:
            print("二维码已经失效，请重新启动程序并扫码")
            exit()
    cookies = []
    for set_cookie in data.headers.get_list('set-cookie'):
        cookie_name, cookie_value = set_cookie.split('=', 1)
        cookies.append(f"{cookie_name}={cookie_value}")
    headers["Cookie"] = ";".join(cookies)
    open("cookie.txt", "w").write(headers["Cookie"])


def get_login_info() -> dict:
    return loads(get("https://api.bilibili.com/x/web-interface/nav", headers=headers).text)


def get_input(prompt: str, allowed_chars: list[str]) -> str:
    while True:
        i = input(prompt)
        if i not in allowed_chars:
            print("请重新输入正确的选择")
        else:
            return i


def get_blacklist() -> list:
    data = loads(
        get("https://api.bilibili.com/x/relation/blacks?ps=1145141919810", headers=headers).text)
    data = data["data"]
    blacklist_ = data["list"]
    _blacklist = []
    for i in blacklist_:
        _blacklist.append(str(i["mid"]))
    return _blacklist


def get_bili_jct():
    cookie = headers["Cookie"].split(";")
    cookie_data = {}
    for i in cookie:
        t = i.split("=")
        if len(t) != 2:
            continue
        cookie_data[t[0]] = t[1]
    return cookie_data["bili_jct"]

def add_blacklist(_blacklist: list[str]):
    bili_jct = get_bili_jct()
    blacklist_str = ",".join(_blacklist)
    params = {"csrf": bili_jct, "fids": blacklist_str, "act": "5", "re_src": "11"}
    return loads(post("https://api.bilibili.com/x/relation/batch/modify", data=params, headers=headers).text)


def load_blacklist(file: str):
    if not (exists(file) and isfile(file)):
        print("文件不存在")
        exit()
    data = loads(open(file, "r").read())
    if all([isinstance(i, int) for i in data]):
        data = [str(i) for i in data]
    if not all([i.isdigit() for i in data]):
        print("文件格式错误，应为json格式的包含字符串类型UID的列表")
        exit()
    return data


if __name__ == "__main__":
    headers = {"User-Agent": "BlacklistMenger/1.0", "Cookie": load_cookie()}
    if not headers["Cookie"]:
        print("开始登录流程获取cookie")
        login()
    else:
        print("从本地读取cookie成功")
    # login_info = get_login_info()
    # print(f"登录成功：昵称：{login_info['data']['uname']}， UID：{login_info['data']['mid']}")

    choice = get_input("请输入对黑名单操作(1:导入,2:导出)：", ["1", "2", "导入", "导出"])
    if choice == "2":
        blacklist = get_blacklist()
        open("blacklist.json", "w").write(dumps(blacklist))
        print("已经导出到当前目录下的blacklist.json")
        print("内容为一个包含UID的列表")
        exit()
    path = input("请输入要导入的黑名单文件的文件路径")
    blacklist = load_blacklist(path)
    re_data = add_blacklist(blacklist)
    print("添加完成，操作失败列表：")
    print("\n".join(re_data["data"]["failed_fids"]))

