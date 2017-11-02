#! /usr/bin/env python3
#coding = utf-8
import wmi
import win32con
import win32api
import time
import psutil
import asyncio
import os
import requests
import re

local_ip = '192.168.1.100'  # 本机ip(考虑后期从ipconfig命令中摘出来)
remote_ip = '192.168.1.200'  # 远端ip(可以设置为从配置文件读取)
_drivers_start = 0  # 起始驱动器数量
b_port = []  # 非法端口黑名单
w_ip = []  # 外联事件白名单

current_time = int(time.time())  # 当前时间
netio_in = 0  # 网卡入流量
netio_out = 0  # 网卡出流量
cpu_used = 0  # cpu使用率
ram_used = 0  # 内存使用率
if_ping = 0  # 是否在线
unexpected_ports = []  # 开放的非法端口
if_cdrom = 0  # 光驱数量
diskc_used = 0  # c盘使用率
update_time = 0  # 黑/白名单更新时间(timestamp)
user_counts = 0  # 当前用户总数
current_user = ''  # 当前用户名
login_time = ''  # 当前用户登入时间
drives_plus = 0  # 磁盘总数增加
drives_minus = 0  # 磁盘总数减少
if_discs = 0  # 是否有光盘挂载
if_serials = []  # 串口信息
if_paras = []  # 并口信息
unexpected_ips = []  # 非法外联事件的目标主机列表
single_log = {}  # 当前的单条日志


# ====================以下为间隔60s的监控项========================================
@asyncio.coroutine
def net_in():  # 每分钟获得网卡出流量
    global netio_in
    while True:
        a0 = psutil.net_io_counters()[1]
        yield from asyncio.sleep(2)
        a1 = psutil.net_io_counters()[1]
        total = (a1 - a0) / (1024 * 2)
        netio_in = round(total, 2)
        # return "Out: {} kb/s".format(speed)
        # print("In: {} kb/s".format(netio_in))
        try:
            yield from asyncio.sleep(58)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def net_out():
    global netio_out
    while True:
        a0 = psutil.net_io_counters()[0]
        yield from asyncio.sleep(2)
        a1 = psutil.net_io_counters()[0]
        total = (a1 - a0) / (1024 * 2)  # 以kb为单位
        netio_out = round(total, 2)
        print("Out: {} kb/s".format(netio_out))
        try:
            yield from asyncio.sleep(58)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def cpu_info():  # 调用时返回cpu使用率
    global cpu_used
    while True:
        # a = psutil.cpu_percent(interval=1) / psutil.cpu_count()  # 是否需要除以核数？
        a = psutil.cpu_percent(interval=1)
        if a != 0.0:
            cpu_used = a
            print(cpu_used)
            try:
                yield from asyncio.sleep(58)
            except asyncio.CancelledError:
                print('Cancelled Error')
                break
        else:
            try:
                yield from asyncio.sleep(1)
            except asyncio.CancelledError:
                print('Cancelled Error')
                break


@asyncio.coroutine
def ram_info():  # 调用时刷新内存使用率
    global ram_used
    while True:
        ram_used = round(psutil.virtual_memory().percent, 2)
        try:
            yield from asyncio.sleep(58)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def ping():  # 调用时返回与主机连接状态
    global if_ping
    remote_url = 'www.baidu.com'  # 服务端ip
    while True:
        pings = os.popen("ping {}".format(remote_url))  # 针对windows
        yield from asyncio.sleep(5)
        msgs = ''.join(pings.readlines())
        error0 = "找不到主机"
        error1 = "无法访问目标主机"
        if msgs.count(error0) == 1 or msgs.count(error1) >= 2:  # 离线状态
            if_ping = 0
            print('offline')
        else:
            if_ping = 1
            print('online')
        try:
            yield from asyncio.sleep(55)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break

task60 = [net_in(), net_out(), cpu_info(), ram_info(), ping()]
# ====================以下为间隔300s的监控项========================================


# 查询获取所有开放和已连接的非法端口 ##
@asyncio.coroutine
def get_port_list():
    global unexpected_ports
    while True:
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
        if b_port == ['黑名单文件不存在']:
            unexpected_ports = b_port
        else:
            for i in all_ports:
                if i in b_port:
                    unexpected_ports.append(i)
                    print('检测到非法端口，端口号为{}'.format(i))  # 此处到时改为发出报警信息
                else:
                    # unexpected_ports.append('000')
                    pass
        try:
            yield from asyncio.sleep(300)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break

task300 = [get_port_list()]
# ====================以下为间隔3600s的监控项========================================


@asyncio.coroutine
def cdrom():  # 判断光驱数量
    global if_cdrom
    while True:
        if wmi.WMI().Win32_CDROMDrive() == 0:
            if_cdrom = 0
        else:
            if_cdrom = wmi.WMI().Win32_CDROMDrive()
        try:
            yield from asyncio.sleep(3600)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def disk_used():  # 返回磁盘使用率
    global diskc_used
    # disks = psutil.disk_partitions()
    # disk_list = []
    # for i in range(len(psutil.disk_partitions())):
    #     disk_list.append(disks[i].mountpoint[0])

    # disk_list_test = ['C:\\', 'D:\\', 'E:\\']  # 本地磁盘有的被bitlocker锁定，故暂用disk_list_test表
    # disk_percent = {}
    # for i in disk_list_test:
    #     disk_percent[i] = psutil.disk_usage(i).percent  # 返回字典，保存每个驱动器的盘符及使用比
    while True:
        diskc_used = psutil.disk_usage('c:\\').percent
        # return diskc_used  # 返回c盘占用率
        try:
            yield from asyncio.sleep(3600)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def files_update(w_file,b_file):
    global update_time
    while True:
        try:
            yield from asyncio.sleep(3600)
        except asyncio.CancelledError:
            print('Cancellled Error')
            break
        black_lists(b_file=r'D:\git\black_list.txt')  # 更新名单
        white_lists(w_file=r'D:\git\white_list.txt')
        update_time = int(time.time())

task3600 = [cdrom(), disk_used(),files_update(w_file=r'D:\git\white_list.txt',b_file= r'D:\git\black_list.txt')]
# ====================以下为间隔20s的监控项========================================


@asyncio.coroutine
def current_users():  # 返回当前用户总数
    global user_counts
    while True:
        user_counts = len(psutil.users())
        # return user_counts
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def user_name():  # 返回当前用户名
    global current_user
    global login_time
    while True:
        current_user = psutil.users()[0].name
        login_time = int(psutil.users()[0].started)
        # return current_user
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def disk_number_compares():  # 比较磁盘数量
    global drives_plus
    global drives_minus
    while True:
        a = len(wmi.WMI().Win32_LogicalDisk())
        if a - _drivers_start > 0:
            drives_plus = 1
            drives_minus = 0
            win32api.MessageBox(win32con.NULL, '驱动器数量增加！', 'Alert', win32con.MB_OK)
        elif a - _drivers_start < 0:
            drives_minus = 1
            drives_plus = 0
            win32api.MessageBox(win32con.NULL, '驱动器数量减少！', 'Alert', win32con.MB_OK)
        elif a - _drivers_start == 0:  # 驱动器数量未变化
            drives_plus = 0
            drives_minus = 0
        else:
            pass
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def if_disc():  # 判断是否有光盘(针对单光驱)
    global if_discs
    while True:
        # 模拟命令行获取磁盘信息
        val0 = os.popen('ECHO LIST VOLUME|DISKPART').readlines()  # 需要程序以管理员身份运行!!
        # ROM_new = 'no'
        # 逐行解析信息，找寻驱动器的相关信息
        val1 = ''.join(val0)
        a = re.search('ROM', val1)
        if re.search('ROM', val1):  # type(re.search('ROM', line)) == 'NoneType'
            if re.search(r'ROM(\s+)0 B', val1) is None:  # 匹配形如"ROM     0 B"字段
                if_discs = 1  # 此时有盘
                print('Disc detected')
            else:
                if_discs = 0  # 此时无盘
                print('No disc ')
        elif a is None:  # 此时无光驱
            if_discs = 0
            print('No disc ')
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def if_serial(): # 判断是否有串口设备
    global if_serials
    while True:
        c = wmi.WMI().Win32_SerialPort()
        if c == []:
            if_serials = []
        else:
            for i in c:
                if_serials.append(c.interface.Description.encode('utf-8'))
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def if_para(): # 判断是否有并口设备
    global if_paras
    while True:
        c = wmi.WMI().Win32_ParallelPort()
        if c == []:
            if_paras = []
        else:
            for i in c:
                if_paras.append(c.interface.Description.encode('utf-8'))
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break


@asyncio.coroutine
def get_ip_list():  # 检测非法外联时间
    global unexpected_ips
    while True:
        unexpected_ips = []
        all_ips = []
        # 查询所有已连接的IP
        result = os.popen('netstat -an').readlines()
        # 逐行解析获取IP地址
        for every in result:
            if 'ESTABLISHED' in every:
                ip = re.search(r'TCP\s+(\d+[.]\d+[.]\d+[.]\d+)[:]\d+\s+(\d+[.]\d+[.]\d+[.]\d+)[:]\d+', every)
                if ip is None:
                    # unexpected_ips.append('')
                    pass
                else:
                    all_ips.append(ip.group(2))
            else:
                pass
        for i in all_ips:
            if i not in w_ip:
                unexpected_ips.append(i)
                print('检测到外联事件,目标主机为{}\n'.format(i))  # 此处到时改为发出报警信息
            else:
                pass
        try:
            yield from asyncio.sleep(20)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break

task20 = [current_users(),user_name(), disk_number_compares(), if_disc(), if_serial(), if_para(), get_ip_list()]


# ====================以下为10s事件，生成单条日志，保存至本地文件，同时发json至服务端========================================
@asyncio.coroutine
def MSG():  # 生成日志信息
    global single_log
    while True:
        single_log = {}
        single_log['TIME'] = current_time
        single_log['IP'] = local_ip
        single_log['netio_in'] = netio_in
        single_log['netio_out'] = netio_out
        single_log['cpu_used'] = cpu_used
        single_log['ram_used'] = ram_used
        single_log['if_ping'] = if_ping
        single_log['unexpected_ports'] = unexpected_ports
        single_log['if_cdrom'] = if_cdrom
        single_log['diskc_used'] = diskc_used
        single_log['update_time'] = update_time
        single_log['user_counts'] = user_counts
        single_log['current_user'] = current_user
        single_log['login_time'] = login_time
        single_log['drives_plus'] = drives_plus
        single_log['drives_minus'] = drives_minus
        single_log['if_discs'] = if_discs
        single_log['if_serials'] = if_serials
        single_log['if_paras'] = if_paras
        single_log['unexpected_ips'] = unexpected_ips

        with open(r'D:\logs\%s_status.txt' % local_ip, 'a+') as f:  # 文件名形如D:\logs\192.168.1.1_status.txt
            msg = '{}{}'.format(single_log, '\n')
            f.write(msg)
        url_test = 'http://localhost:8000/status/'  # 用于测试的接收端地址
        # infos = requests.post(url='{}{}{}'.format('http://', serverIP, '/status/'))
        infos = requests.post(url=url_test, data=single_log)
        with open(r'D:\logs\%s_status.html' % local_ip, 'wb+') as f:  # 将请求的返回内容保存为html
            f.write(infos.text.encode("GBK", "ignore"))
        try:
            yield from asyncio.sleep(10)
        except asyncio.CancelledError:
            print('Cancelled Error')
            break

task10 = [MSG()]


# ====================此函数用于初始化及将所有的异步函数加入队列========================================
def black_lists(b_file):  # 用于生成黑名单，实现危险端口探测功能(若本地已开放端口在黑名单中，则触发报警)
    global b_port
    try:
        with open(b_file, 'r') as f:  # 二进制读
            bts = f.read()
        b_port = bts.split(' ')
        return b_port
    except Exception as ret:
        print(ret)
        b_port = ['黑名单文件不存在']
        return b_port

# white_file = r'C:\Users\hui\Desktop\project\python2017\white_list.txt'


def white_lists(w_file):  # 用于生成白名单，实现外联事件探测功能(若本机访问的目标机器的IP不在白名单中，则触发报警)
    global w_ip
    try:
        with open(w_file, 'r') as f:  # 二进制读
            bts = f.read()
        w_ip = bts.split(' ')
        return w_ip
    except Exception as ret:
        print(ret)
        w_ip = ['白名单文件不存在']
        return w_ip


def start0():  # 初始化
    global _drivers_start
    black_lists(b_file=r'D:\git\black_list.txt')  # 导入黑名单
    white_lists(w_file=r'D:\git\white_list.txt')  # 导入白名单
    _drivers_start = len(wmi.WMI().Win32_LogicalDisk())  # 生成初始磁盘总数，用于后续判断u盘动作
    print(_drivers_start)


def start1():
    loop = asyncio.get_event_loop()
    tasks = task10 + task20 + task60 + task300 + task3600
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()

# ====================以下为脚本开始时执行的函数========================================
start0()
start1()



































# class send_logs(object):  # 单例模式写日志
#     def __new__(cls, *args, **kwargs):
#         if not hasattr(cls, "instance"):
#             cls.instance = super(send_logs, cls).__new__(cls)
#         return cls.instance
#
#     def __init__(self):
#         self.localIP = local_ip
#         self.serverIP = remote_ip
#
#     @property
#     def MSG(self):  # 生成日志信息
#         single_log = {}
#         single_log['TIME'] = current_time
#         single_log['IP'] = self.localIP
#         single_log['netio_in'] = netio_in
#         single_log['netio_out'] = netio_out
#         single_log['cpu_used'] = cpu_used
#         single_log['ram_used'] = ram_used
#         single_log['if_ping'] = if_ping
#         single_log['unexpected_ports'] = unexpected_ports
#         single_log['if_cdrom'] = if_cdrom
#         single_log['diskc_used'] = diskc_used
#         single_log['update_time'] = update_time
#         single_log['user_counts'] = user_counts
#         single_log['current_user'] = current_user
#         single_log['login_time'] = login_time
#         single_log['drives_plus'] = drives_plus
#         single_log['drives_minus'] = drives_minus
#         single_log['if_discs'] = if_discs
#         single_log['if_serials'] = if_serials
#         single_log['if_paras'] = if_paras
#         single_log['unexpected_ips'] = unexpected_ips
#         # single_log = {'IP': {}, 'RAM': {}, 'RAM_AVAI': {}, 'HARD_DISK': {}, 'HARD_DISK_AVAI': {}, 'CPU': {}}
#         return single_log
#
#     # current_time = int(time.time())  # 当前时间
#     # netio_in = 0  # 网卡入流量
#     # netio_out = 0  # 网卡出流量
#     # cpu_used = 0  # cpu使用率
#     # ram_used = 0  # 内存使用率
#     # if_ping = 0  # 是否在线
#     # unexpected_ports = []  # 开放的非法端口
#     # if_cdrom = 0  # 光驱数量
#     # diskc_used = 0  # c盘使用率
#     # update_time = 0  # 黑/白名单更新时间(timestamp)
#     # user_counts = 0  # 当前用户总数
#     # current_user = ''  # 当前用户名
#     # login_time = ''  # 当前用户登入时间
#     # drives_plus = 0  # 磁盘总数增加
#     # drives_minus = 0  # 磁盘总数减少
#     # if_discs = 0  # 是否有光盘挂载
#     # if_serials = []  # 串口信息
#     # if_paras = []  # 并口信息
#     # unexpected_ips = []  # 非法外联事件的目标主机列表
#
#
#
#     def logs_create(self):  # 创建日志
#         with open(r'D:\logs\%s_status.txt' % self.localIP, 'a+') as f:  # 文件名形如192.168.1.1_status.txt
#             msg = '{}{}'.format(self.MSG, '\n')
#             f.write(msg)
#             # 内容形如{'IP': '192.168.2.200', 'RAM': 15.9, 'RAM_AVAI': 51.1, 'HARD_DISK': 119.5, 'HARD_DISK_AVAI': 71.7, 'CPU': 33.9}
#
#     def send(self):
#         url_test = 'http://localhost:8000/status/'  # 用于测试的接收端地址
#         # infos = requests.post(url='{}{}{}'.format('http://', self.serverIP, '/status/'))
#         infos = requests.post(url=url_test, data=self.MSG)
#         with open(r'D:\logs\%s_status.html' % self.localIP, 'wb+') as f:  # 将请求的返回内容保存为html
#             f.write(infos.text.encode("GBK", "ignore"))
#
#
# # ====================以下函数用于将上述监控项加入队列========================================
#
#
#
#
#
#
#
#
#
#
#
# def round0():
#     loop = asyncio.get_event_loop()
#     tasks = [net_in()]
#     loop.run_until_complete(asyncio.wait(tasks))
#     loop.close()
#
#
# # async def net_in():
# #     while True:
# #         global netio_in
# #         a0 = psutil.net_io_counters()[1]
# #         await asyncio.sleep(2)
# #         a1 = psutil.net_io_counters()[1]
# #         total = (a1 - a0) / (1024 * 2)
# #         netio_in = round(total, 2)
# #         # return "Out: {} kb/s".format(speed)
# #         # print("In: {} kb/s".format(netio_in))
# #         await asyncio.sleep(58)
# #
# #
# # async def net_out():
# #     while True:
# #         global netio_out
# #         a0 = psutil.net_io_counters()[0]
# #         await asyncio.sleep(2)
# #         a1 = psutil.net_io_counters()[0]
# #         total = (a1 - a0) / (1024 * 2)  # 2秒内包数的变化
# #         netio_in = round(total, 2)
# #         # return "Out: {} kb/s".format(speed)
# #         print("In: {} kb/s".format(netio_in))
# #         try:
# #             await asyncio.sleep(8)  # 每60秒钟刷新一次
# #         except asyncio.CancelledError:
# #             print('Cancelled Error')
# #             break
#
#
# async def show_out():
#     while True:
#         print(netio_in)
#         try:
#             await asyncio.sleep(5)
#         except asyncio.CancelledError:
#             print('Cancelled Error')
#             break
#
# def disk_numbers():  # 返回磁盘数量
#     global drive_nums
#     drive_nums = len(wmi.WMI().Win32_LogicalDisk())
#     return drive_nums
#
# def time_count():
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     tasks = [net_out(), net_in()]  # 将任务加入队列
#     loop.run_until_complete(asyncio.wait(tasks))
#     loop.close()
#
#
# asyncio def disk_number_compares():  # 比较磁盘数量
#     global drives_plus
#     global drives_minus
#     a = disk_numbers()
#     if a - _drivers_start > 0:
#         drives_plus = 1
#         drives_minus = 0
#         win32api.MessageBox(win32con.NULL, '驱动器数量增加！', 'Alert', win32con.MB_OK)
#     elif a - _drivers_start < 0:
#         drives_minus = 1
#         drives_plus = 0
#         win32api.MessageBox(win32con.NULL, '驱动器数量减少！', 'Alert', win32con.MB_OK)
#     elif a - _drivers_start == 0:
#         drives_plus = 0
#         drives_minus = 0
#     else:
#         pass