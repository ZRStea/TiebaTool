import tiebalib
import logging
import json
import math
import threading
import queue
import re
import time
import itertools
import jieba
# import socket

def judge_thread(thread_list):
    for thread in thread_list:
        thread["result"] = [0,0]
        thread["reason"] = []
#------处理首页相同作者贴子情况------------------
    author_counting = {}
    author_list = []
    for thread in thread_list[3:]:
        if thread["author"] not in author_counting:
            author_counting[thread["author"]] = 1
        else: author_counting[thread["author"]] += 1
    for author in author_counting:
        if author_counting[author] >= same_author_limit[0]:
            author_list.append(author)
    for author in author_list:
        if author != '----':#偶见作者全为‘----’，防止首页爆炸
            temp_thread_list = []
            for thread in thread_list:
                if thread["author"] == author:
                    temp_thread_list.append(thread)
            temp_thread_list.sort(key=lambda x:int(x["reply_num"]))
            for thread in temp_thread_list[:same_author_limit[1]]:
                thread["result"][0] += 1
                thread["reason"].append("超过同用户发贴数限制")
        else:
            logger.warning("首页出现了一次抓取错误，用户名均为'----'")
#----------处理首页贴子标题撞车---------------------
    filterpunct = lambda s: ''.join(filter(lambda x: x not in punct, s))
    punct = set(u''':!),.:;?]}¢'"、。〉》」』】〕〗〞︰︱︳﹐､﹒
 ﹔﹕﹖﹗﹚﹜﹞！），．：；？｜｝︴︶︸︺︼︾﹀﹂﹄﹏､～￠
 々‖•·ˇˉ―--′’”([{£¥'"‵〈《「『【〔〖（［｛￡￥〝︵︷︹︻
 ︽︿﹁﹃﹙﹛﹝（｛“‘-—_… ''')
    for thread_cb in itertools.combinations(thread_list,2):
        (thread1,thread2) = thread_cb
        text1 = filterpunct(thread1["topic"])
        text2 = filterpunct(thread2["topic"])
        simi_rate = calculate_similarity(text1,text2)
        if simi_rate > 0.8 and same_topic_limit:
            min_reply_thread = min(thread1,thread2,key = lambda p:p["reply_num"])
            min_reply_thread["result"][0] += 1
            min_reply_thread["reason"].append("首页标题撞车")
#-----------------------------------------------       
    for thread in thread_list:
        for dic in keywords:
            if re.search(dic["keyword"],thread["topic"]) and dic["topic"]:
                if dic["delete"]:
                    thread["result"][0] += 1
                if dic["block"]:
                    thread["result"][1] += 1
                thread["reason"].append("关键词："+dic["keyword"])
        for dic in author_keywords:
            if re.search(dic["author"],thread["author"]):
                if dic["delete"]:
                    thread["result"][0] += 1
                if dic["block"]:
                    thread["result"][1] += 1
                thread["reason"].append("ID关键词："+dic["author"])
    return thread_list
def judge_post(post_list):
    for post in post_list:
        post["result"] = [0,0]
        post["reason"] = []
        for dic in keywords:
            if re.search(dic["keyword"],post["text"]) and dic["post"]:
                if dic["delete"]:
                    post["result"][0] += 1
                if dic["block"]:
                    post["result"][1] += 1
                post["reason"].append("关键词："+dic["keyword"])
        for dic in author_keywords:
            if re.search(dic["author"],post["author"]):
                if dic["delete"]:
                    post["result"][0] += 1
                if dic["block"]:
                    post["result"][1] += 1
                post["reason"].append("ID关键词："+dic["author"])
        if post["level"] < thread_level_limit and post["floor"] == 1:#限定主题作者等级
            post["result"][0] += 1
            post["reason"].append("楼主低于指定等级")
        if len(post["smiley"]) > smiley_limit:
            post["result"][0] += 1
            post["result"][1] += 1
            post["reason"].append("表情数量超出限制")
        if post["author"] in whitelist:
            post["result"] = [0,0]
    return post_list
def judge_comment(comment_list):
    try:
        for comment in comment_list:
            comment["result"] = [0,0]
            comment["reason"] = []
            for dic in keywords:
                if re.search(dic["keyword"],comment["text"]) and dic["post"]:
                    if dic["delete"]:
                        comment["result"][0] += 1
                    if dic["block"]:
                        comment["result"][1] += 1
                    comment["reason"].append("关键词："+dic["keyword"])
            for dic in author_keywords:
                if re.search(dic["author"],comment["user_name"]):
                    if dic["delete"]:
                        comment["result"][0] += 1
                    if dic["block"]:
                        comment["result"][1] += 1
                    comment["reason"].append("ID关键词："+dic["author"])
            if comment["user_name"] in whitelist:
                comment["result"] = [0,0]
    except TypeError:
        logger.info("TypeError:" + str(comment))
    except Exception as e:
        logger.info("Error:" + str(comment) + str(e))
    return comment_list
def thread_spider():
    while True:
        thread_list = tiebalib.get_thread_list(aim_tieba)#爬取首页贴子列表
        thread_handler(thread_list)#判断首页贴子进行处理
        for thread in thread_list[:once_scan_num]:
            post_task_queue.put(thread)
            comment_task_queue.put(thread)
        time.sleep(spider_sleeptime)
def post_spider():
    while True:
        thread = post_task_queue.get()
        post_list = tiebalib.get_post(thread["tid"],pn=9999)
        posts_queue.put(post_list)
def comment_spider():
    while True:
        thread = comment_task_queue.get()
        post_list = tiebalib.get_post(thread["tid"],pn=1)
        posts_queue.put(post_list)#把第一页post也送去检查关键词
        if post_list:
            for post in post_list:
                if post["pid"] not in comment_num:
                    comment_num[post["pid"]] = post["comment_num"]
                    if post["comment_num"]:
                        pn = 1
                        while pn <= (post["comment_num"]//10+1):
                            comment_list = tiebalib.get_comment(post["tid"],post["pid"],pn)
                            comments_queue.put(comment_list)
                            pn += 1
                else:
                    if post["comment_num"] > comment_num[post["pid"]]:
                        pn = comment_num[post["pid"]]//10+1
                        while pn <= (post["comment_num"]//10+1):
                            comment_list = tiebalib.get_comment(post["tid"],post["pid"],pn)
                            comments_queue.put(comment_list)
                            pn += 1
                        comment_num[post["pid"]] = post["comment_num"]
def thread_handler(thread_list):
    result_list = judge_thread(thread_list)
    for thread in result_list:
        if (thread["pid"] not in is_succeed) and (thread["pid"] not in is_failed):
            if thread["result"][0]:
                status = tiebalib.delete_thread(thread["tid"])
                if status["no"] == 0:
                    logger.info(' '.join(thread["reason"])+" 删除主题："+thread["topic"]+"  作者："+thread["author"])
                    is_succeed.append(thread["pid"])
                else:
                    logger.info(str(status) + " 删除主题失败 " + str(thread))
                    is_failed.append(thread["pid"])
            if thread["result"][1]:
                status = tiebalib.blockid(thread["pid"], thread["author"])
                if status['errno'] == 0:
                    logger.info(' '.join(thread["reason"])+" 封禁主题："+thread["topic"]+"  作者："+thread["author"])
                    is_succeed.append(thread["pid"])
                else:
                    logger.info(str(status) + " 封禁主题失败 " + str(thread))
                    is_failed.append(thread["pid"])
def post_handler():
    while True:
        post_list = posts_queue.get()
        result_list = judge_post(post_list)
        for post in result_list:
            if (post["pid"] not in is_succeed) and (post["pid"] not in is_failed):#添加处理记录
                if post["result"][0]:
                    if post["floor"] == 1:
                        status = tiebalib.delete_thread(post["tid"])
                        if status["no"] == 0:
                            logger.info(' '.join(post["reason"])+" 删除主题："+post["text"]+"  作者："+post["author"])
                            is_succeed.append(post["pid"])
                        else:
                            logger.info(str(status)+" 删除主题失败 "+str(post))
                            is_failed.append(post["pid"])
                    else:
                        status = tiebalib.delete_post(post["tid"], post["pid"])
                        if status["no"] == 0:
                            logger.info(' '.join(post["reason"])+" 删除回复："+post["text"]+"  作者："+post["author"])
                            is_succeed.append(post["pid"])
                        else:
                            logger.info(str(status)+" 删除回复失败 " + str(post))
                            is_failed.append(post["pid"])
                if post["result"][1]:
                    status = tiebalib.blockid(post["pid"], post["author"])
                    if status['errno'] == 0:
                        logger.info(' '.join(post["reason"])+" 封禁回复："+post["text"]+"  作者："+post["author"])
                        is_succeed.append(post["pid"])
                    else:
                        logger.info(str(status)+" 封禁回复失败 "+str(post))
                        is_failed.append(post["pid"])
def comment_handler():
    while True:
        comment_list = comments_queue.get()
        result_list = judge_comment(comment_list)
        for comment in result_list:
            if comment["result"][0]:
                status = tiebalib.delete_comment(comment["tid"], comment["spid"])
                if status["no"] == 0:
                    comment_num[comment["pid"]] -= 1
                    logger.info(' '.join(comment["reason"])+" 删除楼中楼："+comment["text"]+"  作者："+comment["user_name"])
                else:
                    logger.info(str(status)+" 删除楼中楼失败 "+str(comment))
            if comment["result"][1]:
                status = tiebalib.blockid(comment["pid"], comment["user_name"])
                if status['errno'] == 0:
                    logger.info(' '.join(comment["reason"])+" 封禁楼中楼："+comment["text"]+"  作者："+comment["user_name"])
                else:
                    logger.info(str(status)+" 封禁楼中楼失败 "+str(comment))
def calculate_similarity(text1,text2):
    raw1 = jieba.cut(text1)
    raw2 = jieba.cut(text2)
    dict1 ={}
    dict2 ={}
    for i in raw1:
        if i not in dict1:
            dict1[i] = 1
        else:
            dict1[i] +=1
    for i in raw2:
        if i not in dict2:
            dict2[i] = 1
        else:
            dict2[i] +=1
    for i in dict1:
        if i not in dict2:
            dict2[i] = 0
    for i in dict2:
        if i not in dict1:
            dict1[i] = 0
    mod1 = mod2 = 0
    for i in dict1:
        mod1 += dict1[i]*dict1[i]
    for i in dict2:
        mod2 += dict2[i]*dict2[i]
    dot_product = 0
    for i in dict1:
        dot_product += dict1[i]*dict2[i]
    if mod1*mod2 != 0:
        similarity = dot_product/(math.sqrt(mod1*mod2))
    else:similarity = 0
    return similarity

from config import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s","%Y-%m-%d %H:%M:%S")
fh = logging.FileHandler('operate.log')
fh.setFormatter(formatter)
fh.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(sh)

# 使用帐号密码登陆获取到cookie
cookie_for_selenium = tiebalib.get_cookie_by_selenium(username, password)
if tiebalib.try_cookie_logined(cookie_for_selenium):
    cookie = cookie_for_selenium
    print(cookie)
else:
    logger.warning("通过selenium获取cookie失败,将使用config中的cookie")


# socket.setdefaulttimeout(15)

tiebalib.initialize(aim_tieba,cookie)
logger.info("初始化完成")

comment_num = {}#用来储存pid对应楼中楼层数
is_failed = []#储存一个post是否删除失败过
is_succeed = []#储存一个post是否删除成功过
#以上dict均以贴子pid作为key值
work_thread_list = []
post_task_queue = queue.Queue()
comment_task_queue = queue.Queue()
posts_queue = queue.Queue()
comments_queue = queue.Queue()
#爬首页线程
ts = threading.Thread(target=thread_spider,args=(),name="thread_spider")
work_thread_list.append(ts)
#爬贴子线程
for i in range(threading_num):
    ps = threading.Thread(target=post_spider,args=(),name="post_spider")
    work_thread_list.append(ps)
#爬第一页楼中楼线程
for i in range(threading_num):
    cs = threading.Thread(target=comment_spider,args=(),name="comment_spider")
    work_thread_list.append(cs)
#楼中楼处理线程
ph = threading.Thread(target=post_handler,args=(),name="post_handler")
ch = threading.Thread(target=comment_handler,args=(),name="comment_handler")
work_thread_list.append(ph)
work_thread_list.append(ch)
#启动全部工作线程
for work_thread in work_thread_list:
    work_thread.start()

while True:
    #更新关键词信息
    from keywords import *
    from author_keywords import *
    from whitelist import *
    #重启退出进程
    for index, work_thread in enumerate(work_thread_list):
        if not work_thread.isAlive():
            new_thread = threading.Thread(target=locals()[work_thread.name],args=(),name=work_thread.name)
            work_thread_list[index] = new_thread
            new_thread.start()
    time.sleep(2)
