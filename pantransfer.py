import re
import json
import threading
import time
import random
import requests
import argparse
import requests.cookies
import webbrowser
import jsonify
from tkinter import *
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from retrying import retry
from flask import Flask

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

S_WIDTH = 600
S_HEIGHT = 500

#Nas固定位置
NasPackage = '30.78.240.222/AIGC/网盘素材'
# 创建 ArgumentParser 对象
parser = argparse.ArgumentParser(description='网盘自动转存')
# 添加参数
parser.add_argument('--link', help='转存链接')

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'Host': 'pan.baidu.com',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="98", "Google Chrome";v="98"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://pan.baidu.com'
}

BDSTOKEN_URL = 'https://pan.baidu.com/api/loginStatus?clienttype=0&web=1'
VERIFY_URL = 'https://pan.baidu.com/share/verify'
TRANSFER_URL = 'https://pan.baidu.com/share/transfer'
TRANSFER_REPID_URL = 'https://pan.baidu.com/api/rapidupload'
TRANSFER_RENAME_URL = 'https://pan.baidu.com/api/filemanager?async=2&onnest=fail&clienttype=0&opera=rename&app_id=250528&web=1'
GET_DIR_LIST_URL = 'https://pan.baidu.com/api/list?order=time&desc=1&showempty=0&web=1&page=1&num=1000'
CREATE_DIR_URL = 'https://pan.baidu.com/api/create?a=commit'


class Thread:
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def thread_start(self):
        t = threading.Thread(target=self.func, args=self.args)
        t.setDaemon(True)
        t.start()


class GUI:
    def __init__(self, init_window_name):
        self.init_window_name = init_window_name

    def set_init_window(self):
        self.init_window_name.title("百度云批量转存工具_v1.2 / by mobclix")
        self.init_window_name.geometry(str(S_WIDTH) + 'x' + str(S_HEIGHT) + '+'
                                       + str((self.init_window_name.winfo_screenwidth() - S_WIDTH) // 2) + '+'
                                       + str((self.init_window_name.winfo_screenheight() - S_HEIGHT) // 2 - 18))
        self.init_window_name.attributes("-alpha", 0.9)

        self.cookie_data_label = Label(self.init_window_name, anchor='w', text="cookie：")
        self.cookie_data_label.place(relx=0.025, rely=0.01, relheight=0.04, relwidth=0.32)

        self.dirname_data_label = Label(self.init_window_name, anchor='w', text="保存路径：")
        self.dirname_data_label.place(relx=0.025, rely=0.12, relheight=0.04, relwidth=0.32)

        self.link_data_label = Label(self.init_window_name, anchor='w', text="链接：")
        self.link_data_label.place(relx=0.025, rely=0.21, relheight=0.04, relwidth=0.32)

        self.cookie_data_Text = Text(self.init_window_name)
        self.cookie_data_Text.place(relx=0.025, rely=0.05, relheight=0.06, relwidth=0.42)

        self.dirname_data_Text = Text(self.init_window_name)
        self.dirname_data_Text.place(relx=0.025, rely=0.16, relheight=0.04, relwidth=0.42)

        self.scrollbar_link = Scrollbar(self.init_window_name)
        self.scrollbar_link.place(relx=0.445, rely=0.25, relheight=0.65, width=18)
        self.link_data_Text = Text(self.init_window_name, yscrollcommand=self.scrollbar_link.set)
        self.link_data_Text.place(relx=0.025, rely=0.25, relheight=0.65, relwidth=0.42)
        self.scrollbar_link.configure(command=self.link_data_Text.yview)

        self.scrollbar_log = Scrollbar(self.init_window_name)
        self.scrollbar_log.place(relx=0.95, rely=0.05, relheight=0.85, width=18)
        self.log_data_Text = Text(self.init_window_name, yscrollcommand=self.scrollbar_log.set)
        self.log_data_Text.place(relx=0.5, rely=0.05, relheight=0.85, relwidth=0.45)
        self.scrollbar_log.configure(command=self.log_data_Text.yview)

        self.start_button = Button(self.init_window_name, text="开始", bg="#fff", width=10,
                                   command=lambda: Thread(main, self).thread_start())
        self.start_button.place(relx=0.025, rely=0.92, relheight=0.06, relwidth=0.1)

        self.label_update = Label(self.init_window_name, text='查看教程', font=('Arial', 9, 'underline'),
                                  foreground="#0000ff", cursor='mouse')
        self.label_update.place(relx=0.70, rely=0.92, relheight=0.06, relwidth=0.1)
        self.label_update.bind("<Button-1>",
                               lambda e: webbrowser.open("https://blog.csdn.net/mobclix/article/details/123068801",
                                                         new=0))

        self.label_example = Label(self.init_window_name, text='检查新版', font=('Arial', 9, 'underline'),
                                   foreground="#0000ff", cursor='mouse')
        self.label_example.place(relx=0.82, rely=0.92, relheight=0.06, relwidth=0.1)
        self.label_example.bind("<Button-1>",
                                lambda e: webbrowser.open("https://github.com/mobclix/PanTransfers", new=0))


logText = ""

def random_sleep(start=1, end=3):
    sleep_time = random.randint(start, end)
    time.sleep(sleep_time)


def check_link_type(link):
    if link.find('pan.baidu.com/s/') != -1:
        link_type = 'common'
    elif link.count('#') > 2:
        link_type = 'rapid'
    else:
        link_type = 'unknown'
    return link_type


def link_format(links):
    link_list = [link for link in links if link]
    link_list = [link + ' ' for link in link_list]
    return link_list


def parse_url_and_code(url):
    url = url.lstrip('链接:').strip()
    res = re.sub(r'提取码*[：:](.*)', r'\1', url).split(' ', maxsplit=2)
    link_url = res[0]
    pass_code = res[1]
    unzip_code = None
    if len(res) == 3:
        unzip_code = res[2]
    link_url = re.sub(r'\?pwd=(.*)', '', link_url)
    return link_url, pass_code, unzip_code


class PanTransfer:
    def __init__(self, cookie, user_agent, dir_name):
        self.headers = dict(HEADERS)
        self.headers['Cookie'] = cookie
        self.dir_name = dir_name
        self.user_agent = user_agent
        self.bdstoken = None
        self.timeout = 10
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)
        self.get_bdstoken()
        self.create_dir()

    @retry(stop_max_attempt_number=5, wait_fixed=1000)
    def post(self, url, post_data):
        return self.session.post(url=url, data=post_data, timeout=self.timeout, allow_redirects=False, verify=False)

    @retry(stop_max_attempt_number=5, wait_fixed=1000)
    def get(self, url):
        return self.session.get(url=url, timeout=self.timeout, allow_redirects=True)

    def get_bdstoken(self):
        response = self.get(BDSTOKEN_URL)
        bdstoken_list = re.findall('"bdstoken":"(.*?)"', response.text)
        if bdstoken_list:
            self.bdstoken = bdstoken_list[0]
        else:
            raise ValueError('获取bdstoken失败！')

    def transfer_files_repid(self, rapid_data, dir_name):
        global logText
        url = TRANSFER_REPID_URL + f'?bdstoken={self.bdstoken}'
        post_data = {'path': dir_name + '/' + rapid_data[3], 'content-md5': rapid_data[0],
                     'slice-md5': rapid_data[1], 'content-length': rapid_data[2]}
        response = self.post(url, post_data)
        if response.json()['errno'] == 404:
            post_data = {'path': dir_name + '/' + rapid_data[3], 'content-md5': rapid_data[0].lower(),
                         'slice-md5': rapid_data[1].lower(), 'content-length': rapid_data[2]}
            response = self.post(url, post_data)
        data = response.json()
        if data['errno'] == 0:
            self.logs(END, '转存成功！保存位置:' + data['info']['path'] + '\n\n')
            logText += '转存成功！保存位置:' + data['info']['path'] + '\n\n'
        else:
            raise ValueError('转存失败！errno:' + str(data['errno']))

    def transfer_files(self, shareid, user_id, fs_id_list, dir_name, unzip_code):
        global logText
        url = TRANSFER_URL + f'?shareid={shareid}&from={user_id}&bdstoken={self.bdstoken}'
        if not dir_name.strip().startswith('/'):
            dir_name = '/' + dir_name.strip()
        fsidlist = f"[{','.join(i for i in fs_id_list)}]"
        post_data = {'fsidlist': fsidlist, 'path': dir_name}
        response = self.post(url, post_data)
        data = response.json()
        if data['errno'] == 0:
            for each in data['extra']['list']:
                self.logs(END, '转存成功！保存位置:' + each['to'] + '\n')
                diskpath = each['to']
                fileName = diskpath.replace("/test", "")
                filePath = NasPackage + fileName + '\n'
                logText += 'Nas保存位置:' + filePath
                if unzip_code is not None:
                    self.transfer_files_rename(each['to_fs_id'], each['to'], each['from'].replace('/', ''), unzip_code)
                self.logs(END, '\n')
            return True
        else:
            raise ValueError('转存失败！errno:' + str(data['errno']))
            logText += ('转存失败！errno:' + str(data['errno']))
            return False

    def get_dir_list(self, dir_name):
        url = GET_DIR_LIST_URL + f'&dir={dir_name}&bdstoken={self.bdstoken}'
        response = self.get(url)
        data = response.json()
        if data['errno'] == 0:
            dir_list_json = data['list']
            if type(dir_list_json) != list:
                raise ValueError('没获取到网盘目录列表,请检查cookie和网络后重试!\n\n')
            else:
                return dir_list_json
        else:
            ValueError('获取网盘目录列表失败! errno:' + data['errno'] + '\n\n')

    def create_dir(self):
        if self.dir_name != '/' and self.dir_name != '':
            # dir_list_json = self.get_dir_list()
            # dir_list = [dir_json['server_filename'] for dir_json in dir_list_json]
            dir_name_list = self.dir_name.split('/')
            dir_name = dir_name_list[len(dir_name_list) - 1]
            dir_name_list.pop()
            path = '/'.join(dir_name_list) + '/'
            dir_list_json = self.get_dir_list(path)
            dir_list = [dir_json['server_filename'] for dir_json in dir_list_json]
            if dir_name and dir_name not in dir_list:
                url = CREATE_DIR_URL + f'&bdstoken={self.bdstoken}'
                post_data = {'path': self.dir_name, 'isdir': '1', 'block_list': '[]', }
                response = self.post(url, post_data)
                data = response.json()
                if data['errno'] == 0:
                    self.logs(END, '创建目录成功！\n\n')
                else:
                    self.logs(END, '创建目录失败！路径中不能包含以下任何字符: \\:*?"<>|\n\n')

    def transfer_files_rename(self, fs_id, path, name, unzip_code):
        try:
            url = TRANSFER_RENAME_URL + f'&bdstoken={self.bdstoken}'
            newname = name + ' ' + unzip_code
            post_data = {'filelist': f'[{{"id": {fs_id}, "path": "{path}", "newname": "{newname}"}}]'}
            response = self.post(url, post_data)
            data = response.json()
            if data['errno'] == 0:
                self.logs(END, '重命名成功！:' + newname + '\n')
            else:
                self.logs(END, '重命名失败！errno:' + str(data['errno']) + '\n')
            time.sleep(1)
        except Exception as e:
            self.logs(END, '重命名失败！err:' + str(e) + '\n')

    def verify_link(self, link_url, pass_code):
        sp = link_url.split('/')
        url = VERIFY_URL + '?surl=' + sp[len(sp) - 1][1:]
        post_data = {'pwd': pass_code, 'vcode': '', 'vcode_str': '', }
        response = self.post(url, post_data)
        data = response.json()
        if data['errno'] == 0:
            bdclnd = data['randsk']
            cookie = self.session.headers['Cookie']
            if 'BDCLND=' in cookie:
                cookie = re.sub(r'BDCLND=(\S+?);', f'BDCLND={bdclnd};', cookie)
            else:
                cookie += f';BDCLND={bdclnd};'
            self.session.headers['Cookie'] = cookie
            return data
        elif data['errno'] == -9:
            raise ValueError('提取码错误！')
        elif data['errno'] == -62 or data['errno'] == -19 or data['errno'] == -63:
            raise ValueError('错误尝试次数过多，请稍后再试！')
        else:
            raise ValueError('验证链接失败！errno:' + str(data['errno']))

    def get_share_link_info(self, link_url, pass_code):
        self.verify_link(link_url, pass_code)
        random_sleep(start=1, end=3)
        response = self.get(link_url)
        info = re.findall(r'locals\.mset\((.*)\);', response.text)
        if len(info) == 0:
            raise ValueError("获取分享信息失败！")
        else:
            link_info = json.loads(info[0])
        return link_info

    def get_link_data(self, link_url, pass_code):
        link_info = self.get_share_link_info(link_url, pass_code)
        shareid = link_info['shareid']
        user_id = link_info['share_uk']
        file_list = [{'fs_id': i['fs_id'], 'filename': i['server_filename'], 'isdir': i['isdir']} for i in
                     link_info['file_list']]
        if len(file_list) == 0:
            raise ValueError('文件列表为空！')
        return {'shareid': shareid, 'user_id': user_id, 'file_list': file_list}

    def transfer_common(self, link):
        link_url, pass_code, unzip_code = parse_url_and_code(link)
        link_data = self.get_link_data(link_url, pass_code)
        shareid, user_id = link_data['shareid'], link_data['user_id']
        fs_id_list = [str(data['fs_id']) for data in link_data['file_list']]
        self.transfer_files(shareid, user_id, fs_id_list, self.dir_name, unzip_code)

    def transfer_repid(self, link):
        rapid_data = link.split('#', maxsplit=3)
        self.transfer_files_repid(rapid_data, self.dir_name)

    def transfer(self, link_list):
        global logText
        link_list = link_format(link_list)
        for link in link_list:
            try:
                self.logs(END, '正在转存:' + link + '\n')
                link_type = check_link_type(link)
                if link_type == 'common':
                    self.transfer_common(link)
                elif link_type == 'rapid':
                    self.transfer_repid(link)
                else:
                    raise ValueError('未知链接类型')
            except Exception as e:
                try:
                    with open('error.txt', 'a') as f:
                        f.write(link + '\n')
                except BaseException:
                    print('export_txt error')
                self.logs(END, 'Transfer Error --- ' + str(e) + '\n\n')
                logText += ('Transfer Error --- ' + str(e) + '\n\n')
        self.logs(END, '转存完成！' + '\n')
        logText += ('已加入下载队列！请稍后查看~~~' + '\n')

    def logs(self, index, text):
        print(text)
        # self.gui.log_data_Text.insert(index, text)


def main(gui):
    try:
        gui.log_data_Text.delete(1.0, END)
        if gui.link_data_Text.get(1.0, END) == '\n' or gui.cookie_data_Text.get(1.0, END) == '\n':
            gui.log_data_Text.insert(END, 'cookie或链接不能为空！ ' + '\n\n')
            return
        dir_name = "".join(gui.dirname_data_Text.get(1.0, END).split())
        cookie = "".join(gui.cookie_data_Text.get(1.0, END).split())
        user_agent = ''
        link_list = gui.link_data_Text.get(1.0, END).split('\n')

        # pan_transfer = PanTransfer(cookie, user_agent, dir_name, gui)
        pan_transfer.transfer(link_list)
    except Exception as e:
        gui.log_data_Text.insert(END, 'Error --- ' + str(e) + '\n\n')


def startWithParams(link):
    global logText
    print('链接是:' + link)
    logText += '链接:' + link + '\n'
    try:
        dir_name = "/test"
        cookie = "Hm_lvt_e6c5e9705447b840241ebab6dbdb5fda=1691586934; Hm_lpvt_e6c5e9705447b840241ebab6dbdb5fda=1691631805; XFI=561ea998-5895-d393-14ca-ae3469b34a4b; XFCS=ADCA2EA58DE23A78A59AB2A2C7CE9805CF108594AE201073DB5ECEECF4ABE861; XFT=PZGoV2Xrmm+Xe9kgTt3UyhM2+7l4hEV0Fhq5WScuEG4=; BIDUPSID=587B3531288AE35B8894049396B95777; PSTM=1684757501; PANWEB=1; BAIDUID=587B3531288AE35BB98819A7D260A87D:SL=0:NR=10:FG=1; BDUSS=kpyT1JuZVRhcmV5M3NRfnFybk9oNHVXcE45bU80Q345NGZ0RDdKT1F1YUF3OEJrRVFBQUFBJCQAAAAAAAAAAAEAAAChXpEEeTEyMTMxNzIwMgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIA2mWSANplkT; BDUSS_BFESS=kpyT1JuZVRhcmV5M3NRfnFybk9oNHVXcE45bU80Q345NGZ0RDdKT1F1YUF3OEJrRVFBQUFBJCQAAAAAAAAAAAEAAAChXpEEeTEyMTMxNzIwMgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIA2mWSANplkT; MCITY=-131%3A; csrfToken=M54EBgFogjhlZtHSur8bUg57; Hm_lvt_7a3960b6f067eb0085b7f96ff5e660b0=1690019837,1690202507,1690374727; STOKEN=b46bdaca99dbec566886ec2f3725a03ec06546d3429f2fa926c5e8e4197f2d2d; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; newlogin=1; BA_HECTOR=040184a0042485a5ah8521am1id6h4c1o; delPer=0; PSINO=1; ZFY=RRDN8:BESu6vmjm:BXUFa9Z40SmNf309:BZG1ZIRnNLLwU:C; BAIDUID_BFESS=587B3531288AE35BB98819A7D260A87D:SL=0:NR=10:FG=1; Hm_lpvt_7a3960b6f067eb0085b7f96ff5e660b0=1691569502; H_PS_PSSID=36546_38831_39007_39114_39118_38918_26350_39138_39137_39101_39044_38951; BCLID=11781563781223004184; BCLID_BFESS=11781563781223004184; BDSFRCVID=YqFOJexroG0Jp3jfFk8-5Nkfu9NbUdrTDYrEOwXPsp3LGJLVFsQ6EG0Pts1-dEub6j30ogKK0mOTHUkF_2uxOjjg8UtVJeC6EG0Ptf8g0M5; BDSFRCVID_BFESS=YqFOJexroG0Jp3jfFk8-5Nkfu9NbUdrTDYrEOwXPsp3LGJLVFsQ6EG0Pts1-dEub6j30ogKK0mOTHUkF_2uxOjjg8UtVJeC6EG0Ptf8g0M5; H_BDCLCKID_SF=tbC8VCDKJKD3H48k-4QEbbQH-UnLqMbMWmOZ04n-ah02O4tRM4jP0Mb-jtTWKJL8BDrP0Pom3UTKsq76Wh35K5tTQP6rLf5eLRc4KKJxbP8aKJbH5tK-M6JQhUJiB5OLBan7-RvIXKohJh7FM4tW3J0ZyxomtfQxtNRJ0DnjtpChbC8lejuaj6bLeU5eetjK2CntsJOOaCkMHqQOy4oWK441D-6jJ-Th3HRp5D5k2bQhbqrP3tOK3M04K4o9-hvT-54e2p3FBUQPqUDCQft20b0yDecb0RQaJDLeon7jWhk2Dq72yhoOQlRX5q79atTMfNTJ-qcH0KQpsIJM5-DWbT8IjHCeJ6F8tRFfoCvt-5rDHJTg5DTjhPrMQHQiWMT-MTryKKJF-IO8elQc0PuhX4PE5Hrw5qQb-HnRh4oNB-3iV-OxDUvnyxAZQlbItfQxtNRJQKDE5p5hHCQFDT3obUPUDMc9LUvP22cdot5yBbc8eIna5hjkbfJBQttjQn3hfIkj2CKLtKDBbDDCjTL3-RJH-xQ0KnLXKKOLVbnFbp7ketn4hUt2yROyMxjlah57JmoW0tKXBJole-o2QhrKQf4WWb3ebTJr32Qr-qQbLCQpsIJM5b-aqt0k5fKqajtjaKviaKJEBMb1SJvDBT5h2M4qMxtOLR3pWDTm_q5TtUJMeCnTDMFhe6JLeHuDtj-DfKresJoq2RbhKROvhjRZKfKgyxoObtRxtgQjobcD3JkWKD58MPjhefCV3fOHLU3k-eT9LMnx--t58h3_XhjPKpoBQttjQn3et4jbK45tJJF5hb7TyU42hf47yboW0q4Hb6b9BJcjfU5MSlcNLTjpQT8r5MDOK5OuJRQ2QJ8BtC05hKbP; H_BDCLCKID_SF_BFESS=tbC8VCDKJKD3H48k-4QEbbQH-UnLqMbMWmOZ04n-ah02O4tRM4jP0Mb-jtTWKJL8BDrP0Pom3UTKsq76Wh35K5tTQP6rLf5eLRc4KKJxbP8aKJbH5tK-M6JQhUJiB5OLBan7-RvIXKohJh7FM4tW3J0ZyxomtfQxtNRJ0DnjtpChbC8lejuaj6bLeU5eetjK2CntsJOOaCkMHqQOy4oWK441D-6jJ-Th3HRp5D5k2bQhbqrP3tOK3M04K4o9-hvT-54e2p3FBUQPqUDCQft20b0yDecb0RQaJDLeon7jWhk2Dq72yhoOQlRX5q79atTMfNTJ-qcH0KQpsIJM5-DWbT8IjHCeJ6F8tRFfoCvt-5rDHJTg5DTjhPrMQHQiWMT-MTryKKJF-IO8elQc0PuhX4PE5Hrw5qQb-HnRh4oNB-3iV-OxDUvnyxAZQlbItfQxtNRJQKDE5p5hHCQFDT3obUPUDMc9LUvP22cdot5yBbc8eIna5hjkbfJBQttjQn3hfIkj2CKLtKDBbDDCjTL3-RJH-xQ0KnLXKKOLVbnFbp7ketn4hUt2yROyMxjlah57JmoW0tKXBJole-o2QhrKQf4WWb3ebTJr32Qr-qQbLCQpsIJM5b-aqt0k5fKqajtjaKviaKJEBMb1SJvDBT5h2M4qMxtOLR3pWDTm_q5TtUJMeCnTDMFhe6JLeHuDtj-DfKresJoq2RbhKROvhjRZKfKgyxoObtRxtgQjobcD3JkWKD58MPjhefCV3fOHLU3k-eT9LMnx--t58h3_XhjPKpoBQttjQn3et4jbK45tJJF5hb7TyU42hf47yboW0q4Hb6b9BJcjfU5MSlcNLTjpQT8r5MDOK5OuJRQ2QJ8BtC05hKbP; BDCLND=yqUC3xAwM%2Fp285h5wRstzjC2Pb9c1XDHM3KVX9cEje4%3D; Hm_lvt_e6c5e9705447b840241ebab6dbdb5fda=1691586934; Hm_lpvt_e6c5e9705447b840241ebab6dbdb5fda=1691586935; ndut_fmt=3C12889188B733CB0E81484FE28FBF88D3E1B0D4E23AD3B19282BF3A3A091852; ab_sr=1.0.1_NTU0NmYxNmQ3OTJiZDcxYTFmNDU0YjFmN2RhMzZlMWRmY2RjMTQ3ZTMyNWNjYzQwMmE2ZWIwNDY3ZDkxYjEzYWVlNTg5ZjIzMGUxOTk4MWViOGM3YjYyNGY2MDBiODcxNzZmOTk4YjhjNWQ5MDE0NWNkYTY4ZTVhZGRmMTc2MDQ1YjRiNDEyMDc2Yjk4YTQxYjIwODQxZTQzMmI0YWE2MTVlNzE3NWNkMmFkMzg4MDYzOTdmNGJhZDBkNWRkN2Iw"
        user_agent = ''
        pan_transfer = PanTransfer(cookie, user_agent, dir_name)
        link_list = link.split('\n')
        pan_transfer.transfer(link_list)
        print(logText)
        sendSuccessInfo(logText)
    except Exception as e:
        print('Error --- ' + str(e) + '\n\n')


# def gui_start():
#     init_window = Tk()
#     gui = GUI(init_window)
#     gui.set_init_window()
#     init_window.mainloop()
def sendSuccessInfo(Info):
     url = 'https://oapi.dingtalk.com/robot/send?access_token=9c5ca2900b38039e986165a8c4f0795364517440674cc874e9c134c393a93a52'
     headers = {
         'Content-Type': 'application/json'
     }
     data = {
         'msgtype': 'text',
         'text': {
             'content': Info
         }
     }
     response = requests.post(url, headers=headers, json=data)
     print(response.status_code, response.text)

# 解析命令行参数
# args = parser.parse_args()

# # 输出参数值
# if args.link:
#     startWithParams(args.link)


# gui_start()

app = Flask(__name__)

# methods: 指定请求方式
@app.route('/download', methods=['POST'])
def process_data():
	# 请求方式为post时，可以使用 request.get_json()接收到JSON数据
    data = request.get_json()  # 获取 POST 请求中的 JSON 数据
    print(data)
    # 处理数据
    # 调用do_something_with_data函数来处理接收到的数据。
    # processed_data = do_something_with_data(data)
    #
    # # 请求方得到处理后的数据
    # return jsonify(processed_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0',  port=9999, debug=True)
