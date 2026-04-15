from os.path import exists, isfile
from json import loads, dumps
from httpx import get, post
from time import sleep
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
    blacklist_ = []
    data = loads(get("https://api.bilibili.com/x/relation/blacks", headers=headers).text)
    print("请求页数：", 1)
    data = data["data"]
    blacklist_ += [str(i["mid"]) for i in data['list']]
    t = data["total"]
    if len(data["list"]) < 50:
        return blacklist_
    num = (t - len(data["list"])) // 50
    for i in range(2, num + 3):
        a = loads(get(f"https://api.bilibili.com/x/relation/blacks?pn={i}", headers=headers).text)["data"]["list"]
        blacklist_ += [str(i["mid"]) for i in a]
        print("请求页数：", i)
        sleep(2)
    return blacklist_


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
    login_info = get_login_info()
    print(f"登录成功：昵称：{login_info['data']['uname']}， UID：{login_info['data']['mid']}")

    while True:
        choice = get_input("\n请输入对黑名单操作(1:导入,2:导出)：", ["1", "2", "导入", "导出"])
        
        if choice in ["2", "导出"]:
            blacklist = get_blacklist()
            open("blacklist.json", "w").write(dumps(blacklist))
            print("已经导出到当前目录下的blacklist.json")
            print("内容为一个包含UID的列表")
            
        else:
            path = input("请输入要导入的黑名单文件的文件路径(直接回车默认读取当前目录下的blacklist.json)：")
            if not path.strip():
                path = "blacklist.json"
            blacklist = load_blacklist(path)
            print(f"共读取到 {len(blacklist)} 个黑名单用户，开始分批导入（每批20个）...")
            failed_total = []

            for i in range(0, len(blacklist), 20):
                batch = blacklist[i:i+20]
                re_data = add_blacklist(batch)
                
                if re_data.get("code") == 0 and re_data.get("data") is not None:
                    batch_failed = re_data["data"].get("failed_fids", [])
                    if isinstance(batch_failed, list):
                        failed_total.extend(batch_failed)
                    print(f"进度：{min(i+20, len(blacklist))}/{len(blacklist)} 处理完毕...")
                else:
                    print(f"进度：{min(i+20, len(blacklist))}/{len(blacklist)} 遇到异常：{re_data}")
                    
                sleep(1.5)  # 加一点延时，防止请求太快被B站拦截

            print("--- 导入任务结束 ---")
            if failed_total:
                print("以下 UID 导入失败（可能账号已注销或已在黑名单中）：")
                print("\n".join([str(uid) for uid in failed_total]))
            else:
                print("全部导入成功，无失败记录！")

        # 每轮跑完后询问是否继续
        cont = input("\n操作已完成。输入 k 继续执行其他操作，按回车或其他键退出：")
        if cont.strip().lower() != 'k':
            break
