#! /usr/bin/env python3
# coding = utf-8
"""
监控系统状态,如磁盘大小，cpu使用率，网卡速率等
参数动态更新，需要生成json时直接取值，不用现调方法
"""
import wmi
import win32con
import win32api
import time
import psutil
import asyncio
import os
import requests
import re

# disks = wmi.WMI().Win32_LogicalDisk()  # 调用此方法获得硬盘信息

_drivers_start = len(wmi.WMI().Win32_LogicalDisk())  # 起始磁盘数量
total_rams = 0  # 内存总容量
# c盘大小
diskc = 0
# c盘使用率
diskc_used = 0
# 驱动器数量变化
drives_plus = 0  # 驱动器数量较初始增加则为1，否则为0。
drives_minus = 0  # 驱动器数量较初始减少则为1，否则为0。
# 是否有光驱
if_cdrom = 0
# 是否有光盘
if_discs = 0
# 判断是否在线
if_ping = 1
# 连接数
connect_num = 1
# CPU使用率
cpu_used = 0
# 内存使用率
ram_used = 0
# 网卡上行速率
netio_out = 0
# 网卡下行速率
netio_in = 0
# 当前用户总数
user_counts = 1
# 当前用户名
current_user = 1
# 串口设备名称

# 并口设备名称

# 危险端口访问(本机/远端)
dangerous_port = []


async def t20():  # 每20秒调用一次下列函数，刷新变量
    while True:
        global user_counts
        global current_user
        current_users()  # 检查当前用户数
        user_name()  # 当前用户名
        disk_number_compares()  # 驱动器数
        if_disc()  # 是否有光盘挂载
        get_ip_list()  # 检测外联事件
        try:
            await asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


async def t60():  # 每60秒调用一次下列函数，刷新变量
    while True:
        cpu_info()
        ram_info()
        net_out()
        net_in()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


def disk_numbers():  # 返回磁盘数量
    global drive_nums
    drive_nums = len(wmi.WMI().Win32_LogicalDisk())
    return drive_nums


def ram():  # 获取总内存大小
    global total_rams
    a = psutil.virtual_memory().total / (1024 ** 3)  # 内存取GB大小
    total_rams = round(a, 1)
    return total_rams


def disk_c():
    global diskc
    diskc = round(psutil.disk_usage(r'c:\\').total / (1024 ** 3), 1)  # 获取C盘大小，单位为GB
    return diskc


# 查询获取所有开放和已连接的非法端口 ##
def get_port_list():
    global unexpected_ports
    unexpected_ports = []
    all_ports = []
    # 查询所有的开放端口信息
    result = os.popen('netstat -an').readlines()
    # 逐行解析获取端口号
    for every in result:
        if 'TCP' in every:
            num = (re.findall(':[\d]* ', every))
            num = num[0]
            sourceport = num[1:-1]
            all_ports.append(sourceport)
        if 'UDP' in every:
            num = (re.findall(':[\d]* ', every))
            num = num[0]
            sourceport = num[1:-1]
            all_ports.append(sourceport)
    all_ports = sorted(list(set(all_ports)))
    for i in all_ports:
        if i in black_lists():
            unexpected_ports.append(i)
            print('检测到非法端口，端口号为{}'.format(i))  # 此处到时改为发出报警信息
        else:
            pass


def get_ip_list():
    global unexpected_ips
    unexpected_ips = []
    all_ips = []
    # 查询所有已连接的IP
    result = os.popen('netstat -an').readlines()
    # 逐行解析获取IP地址
    for every in result:
        if 'ESTABLISHED' in every:
            ip = re.search(r'TCP\s+(\d+[.]\d+[.]\d+[.]\d+)[:]\d+\s+(\d+[.]\d+[.]\d+[.]\d+)[:]\d+', every)
            if ip is None:
                pass
            else:
                all_ips.append(ip.group(2))
        else:
            pass
    # all_ports = sorted(list(set(all_ports)))
    for i in all_ips:
        if i not in white_lists():
            unexpected_ips.append(i)
            print('检测到外联事件,目标主机为{}\n'.format(i))  # 此处到时改为发出报警信息
        else:
            pass


black_file = r'C:\Users\hui\Desktop\project\python2017\black_list.txt'


def black_lists():  # 用于生成黑名单，实现危险端口探测功能(若本地已开放端口在黑名单中，则触发报警)
    # global list0
    with open(black_file, 'r') as f:  # 二进制读
        bts = f.read()
    list0 = bts.split(' ')
    return list0


white_file = r'C:\Users\hui\Desktop\project\python2017\white_list.txt'


def white_lists():  # 用于生成白名单，实现外联事件探测功能(若本机访问的目标机器的IP不在白名单中，则触发报警)
    with open(white_file, 'r') as f:  # 二进制读
        bts = f.read()
    list0 = bts.split(' ')
    return list0


def current_users():  # 返回当前用户总数
    global user_counts
    user_counts = len(psutil.users())
    return user_counts


def user_name():  # 返回当前用户名
    global current_user
    current_user = psutil.users()[0].name
    return current_user


def disk_number_compares():  # 比较磁盘数量
    global drives_plus
    global drives_minus
    a = disk_numbers()
    if a - _drivers_start > 0:
        drives_plus = 1
        drives_minus = 0
        win32api.MessageBox(win32con.NULL, '驱动器数量增加！', 'Alert', win32con.MB_OK)
    elif a - _drivers_start < 0:
        drives_minus = 1
        drives_plus = 0
        win32api.MessageBox(win32con.NULL, '驱动器数量减少！', 'Alert', win32con.MB_OK)
    elif a - _drivers_start == 0:
        drives_plus = 0
        drives_minus = 0
    else:
        pass


def cpu_info():  # 调用时返回cpu使用率
    global cpu_used
    if psutil.cpu_percent(interval=1) == 0.0:  # 采到的结果为0.0时，重新收集
        time.sleep(1)
        return cpu_info()
    else:
        cpu_used = psutil.cpu_percent(interval=1) / psutil.cpu_count()
        return cpu_used


def ram_info():
    global ram_used
    ram_used = round(psutil.virtual_memory().percent, 2)
    return ram_used  # 返回内存占用率


def disk_used():  # 返回磁盘使用率
    global diskc_used
    disks = psutil.disk_partitions()
    disk_list = []
    for i in range(len(psutil.disk_partitions())):
        disk_list.append(disks[i].mountpoint[0])

    # disk_list_test = ['C:\\', 'D:\\', 'E:\\']  # 本地磁盘有的被bitlocker锁定，故暂用disk_list_test表
    # disk_percent = {}
    # for i in disk_list_test:
    #     disk_percent[i] = psutil.disk_usage(i).percent  # 返回字典，保存每个驱动器的盘符及使用比
    diskc_used = psutil.disk_usage('c:\\').percent
    return diskc_used  # 返回c盘占用率


def cdrom():  # 判断光驱数量
    global if_cdrom
    if wmi.WMI().Win32_CDROMDrive() == 0:
        if_cdrom = 0
    else:
        if_cdrom = wmi.WMI().Win32_CDROMDrive()


def if_disc():  # 判断是否有光盘(针对单光驱)
    global if_discs
    # 模拟命令行获取磁盘信息
    val0 = os.popen('ECHO LIST VOLUME|DISKPART').readlines()
    # ROM_new = 'no'
    # 逐行解析信息，找寻驱动器的相关信息
    val1 = ''.join(val0)
    a = re.search('ROM', val1)
    if re.search('ROM', val1):  # type(re.search('ROM', line)) == 'NoneType'
        if re.search(r'ROM(\s+)0 B', val1) is None:  # 匹配形如"ROM     0 B"字段
            if_discs = 1  # 此时有盘
        else:
            if_discs = 0  # 此时无盘
    elif a is None:  # 此时无光驱
        if_discs = 0


def connections():
    global connect_num
    connect_num = len(psutil.net_connections())
    return connect_num  # 返回连接数


def get_ip():  # 从指定的配置文件中读取本地ip和服务器ip
    # with open(r'D:\python2017\local.ini', 'r') as settings:
    #     settings = settings.readlines()
    # if settings[0][-1] == '\n':  # windows下可能出现换行符‘\n’
    #     localIP = settings[0][0:-1]
    # else:
    #     localIP = settings[0]
    #
    # if settings[1][-1] == '\n':
    #     serverIP = settings[1][0:-1]
    # else:
    #     serverIP = settings[1]
    # # return [localIP, serverIP]
    return ['192.168.1.100', '192.168.1.1']


# def current_time():  # 生成当前时间，格式形如 '2017-09-22/18:56:43'
#     return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def current_time():
    return int(time.time())  # 返回取整的时间戳


async def net_out():
    global netio_out
    a0 = psutil.net_io_counters()[0]
    await asyncio.sleep(1)
    a1 = psutil.net_io_counters()[0]
    total = (a1 - a0) / (1024 * 1)  # 以kb为单位
    netio_out = round(total, 2)
    return print("Out: {} kb/s".format(netio_out))


async def net_in():
    global netio_in
    a0 = psutil.net_io_counters()[1]
    await asyncio.sleep(1)
    a1 = psutil.net_io_counters()[1]
    total = (a1 - a0) / (1024 * 1)
    netio_in = round(total, 2)
    # return "Out: {} kb/s".format(speed)
    print("In: {} kb/s".format(netio_in))


async def ping():  # ping服务端
    global if_ping
    remote_url = 'www.baidu.com'
    pings = os.popen("ping {}".format(remote_url))  # 针对windows
    await asyncio.sleep(5)
    msgs = ''.join(pings.readlines())
    error0 = "找不到主机"
    error1 = "无法访问目标主机"
    if msgs.count(error0) == 1 or msgs.count(error1) >= 2:  # 离线状态
        if_ping = 0
        return print('offline')
    else:
        if_ping = 1
        return print('online')


#
# def time_count():
#     a = time.time()
#     loop = asyncio.get_event_loop()
#     tasks = [net_out(), net_in()]
#     loop.run_until_complete(asyncio.wait(tasks))
#     loop.close()
#     b = time.time()
#     return print(b-a)
#
# time_count()

def time_count():
    a = time.time()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [net_out(), net_in(), ping()]  # 将任务加入队列
    try:
        loop.run_until_complete(asyncio.wait(tasks))
    except Exception as ret:
        print(ret)
        loop.close()

    b = time.time()
    return print(b - a)


def t20():
    a = time.time()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.wait(task20))
    loop.close()
    b = time.time()
    return print(b-a)


# def t60():
#     a = time.time()
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(asyncio.wait(task60))
#     loop.close()
#     b = time.time()
#     return print(b - a)
#
#
# def t300():
#     a = time.time()
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(asyncio.wait(task300))
#     loop.close()
#     b = time.time()
#     return print(b - a)
#
#
# def t3600():
#     a = time.time()
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(asyncio.wait(task3600))
#     loop.close()
#     b = time.time()
#     return print(b - a)


class send_logs(object):  # 单例模式写日志
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(send_logs, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.localIP = get_ip()[0]
        self.serverIP = get_ip()[1]

    @property
    def MSG(self):  # 生成日志信息
        single_log = {}
        single_log['TIME'] = current_time()
        single_log['IP'] = self.localIP
        single_log['RAM'] = total_rams
        single_log['RAM_AVAI'] = ram_used
        single_log['HARD_DISK'] = round(disk_c(), 1)
        single_log['HARD_DISK_AVAI'] = disk_used()
        single_log['CPU'] = cpu_info()
        # single_log = {'IP': {}, 'RAM': {}, 'RAM_AVAI': {}, 'HARD_DISK': {}, 'HARD_DISK_AVAI': {}, 'CPU': {}}
        return single_log

    def logs_create(self):  # 创建日志
        with open(r'D:\logs\%s_status.txt' % self.localIP, 'a+') as f:  # 文件名形如192.168.1.1_status.txt
            msg = '{}{}'.format(self.MSG, '\n')
            f.write(
                msg)  # 内容形如{'IP': '192.168.2.200', 'RAM': 15.9, 'RAM_AVAI': 51.1, 'HARD_DISK': 119.5, 'HARD_DISK_AVAI': 71.7, 'CPU': 33.9}

    def send(self):
        url_test = 'http://localhost:8000/status/'  # 用于测试的接收端地址
        # infos = requests.post(url='{}{}{}'.format('http://', self.serverIP, '/status/'))
        infos = requests.post(url=url_test, data=self.MSG)
        with open(r'D:\logs\%s_status.html' % self.localIP, 'wb+') as f:  # 将请求的返回内容保存为html
            f.write(infos.text.encode("GBK", "ignore"))

# 20秒周期的任务
task20 = [current_users(), user_name(), disk_number_compares(), if_disc(), get_ip_list()]
# 60秒周期的任务
task60 = [cpu_info(), ram_info(), net_in(), net_out()]
# 300秒周期的任务
task300 = [get_port_list()]
# 3600秒周期的任务
task3600 = [disk_used(), cdrom()]

# def main():
#     while True:
#         a = send_logs()
#         a.logs_create()
#         print('Log has been send')
#         a.send()
#         time.sleep(10)
#
# main()
oldloop = asyncio.get_event_loop()
while True:
    time_count()
asyncio.set_event_loop(oldloop)
