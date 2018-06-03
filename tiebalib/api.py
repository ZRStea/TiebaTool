import time
import requests
import itertools
import re
import json
import functools
import signal
from bs4 import BeautifulSoup
from html.parser import HTMLParser
import jieba
import math
import sys
import logging

fh = logging.FileHandler('error.log')
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s","%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
log = logging.getLogger(__name__)
log.addHandler(fh)

class data:
    aim_tieba = ''
    cookie = ''
    tbs = ''
    UA = 'User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)'
    fid = ''

def initialize(aim_tieba,cookie):
    data.cookie = cookie
    data.aim_tieba = aim_tieba
    data.fid = get_fid()
    data.tbs = get_tbs()

def get_tbs():
    tbs_url = "http://tieba.baidu.com/dc/common/tbs"
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    content_json = json.loads(requests.get(tbs_url, headers = headers).text)
    data.tbs = content_json['tbs']
    return content_json['tbs']

def get_fid():
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    content = requests.get('http://tieba.baidu.com/'+data.aim_tieba, headers = headers).text
    raw = re.search('"forum_id":(.*?),', content)
    if raw:
        fid =raw.group(1)
        return fid
    else:
        log.warning("获取fid失败")
        return 0

def get_thread_list(aim_tieba = data.aim_tieba,pn=0):
    try:
        threads = []
        payload = {'pn':pn, 'ie':'utf-8'}
        headers = {'Cookie':data.cookie,'User-Agent':data.UA}
        content = requests.get('http://tieba.baidu.com/f?kw='+data.aim_tieba,params=payload, headers=headers).text
        raws = re.findall('thread_list clearfix([\s\S]*?)创建时间"',content)
        for raw in raws:
            tid = re.findall('href="/p/(\d*)', raw)
            pid = re.findall('&quot;first_post_id&quot;:(.*?),', raw)
            topic = re.findall('href="/p/.*?" title="([\s\S]*?)"', raw)
            nickname = re.findall('title="主题作者: (.*?)"', raw)
            reply_num = re.findall('&quot;reply_num&quot;:(.*?),',raw)
            username = re.findall('''frs-author-name-wrap"><a rel="noreferrer"  data-field='{&quot;un&quot;:&quot;(.*?)&quot;}''',raw)
            if len(tid)==len(pid)==len(topic)==len(username)==len(reply_num):
                dic = {"tid":tid[0],"pid":pid[0],"topic":topic[0],"author":username[0].encode('utf-8').decode('unicode_escape'),"reply_num":reply_num[0],"nickname":nickname[0]}
                threads.append(dic)
        if threads == []:
            log.warning("获取首页失败")
    except Exception:
        log.exception("Exception Logged")
        return []
    return threads

def get_post(tid,pn=9999):
    try:
        url = 'http://tieba.baidu.com/p/'+tid
        headers = {'Cookie':data.cookie,'User-Agent':data.UA}
        raw = requests.get(url, params={'pn':pn}, headers=headers).text
        post_list = []
        content =BeautifulSoup(raw,'html.parser')
        # author_info = content.find_all("div",class_=re.compile("l_post l_post_bright j_l_post clearfix "))
        author_info = content.find_all("div",attrs={"class":"l_post l_post_bright j_l_post clearfix "})
        # texts = content.find_all("div",class_=re.compile("d_post_content j_d_post_content "))
        texts = content.find_all("div",class_=re.compile("d_post_content j_d_post_content "))

        if not texts:
            log.warning("抓取贴子:"+tid+" 失败,正则未匹配到贴子信息")
            return []#抓不到返回空list
        if len(author_info) == len(texts):
            posts = zip(texts,author_info)
        else:
            log.warning("抓取贴子:"+tid+" 失败,回复内容与用户信息数量不相等")
            return []#抓不到返回空list
        for post_raw in posts:
            text = ''
            for i in post_raw[0].strings:
                text = text+i
            user_sign = post_raw[0].parent.parent.parent.find_all(class_='j_user_sign')
            if user_sign:
                user_sign = user_sign[0]["src"]
            imgs = post_raw[0].find_all("img",class_="BDE_Image")
            img = []
            if imgs:
                for i in imgs:
                    img.append(i["src"])
            smileys = post_raw[0].find_all('img',class_='BDE_Smiley')
            smiley = []
            if smileys:
                for i in smileys:
                    smiley.append(i["src"])
            post_info = [post_raw[1]["data-field"],text,user_sign,img,smiley]
            t = json.loads(post_info[0])
            post = {}
            post["text"] = post_info[1].strip()#去除开头空格
            post["tid"] = tid
            post["author"] = t["author"]["user_name"]
            post["uid"] = t["author"]["user_id"]
            # post["sex"] = t["author"]["user_sex"]
            # post["exp"] = t["author"]["cur_score"]
            # post["level"] = t["author"]["level_id"]
            post["level"] = post_raw[1].find('div',attrs={'class':'d_badge_lv'}).text
            post["pid"] = t["content"]["post_id"]
            # post["date"] = t["content"]["date"]
            # post["voice"] = t["content"]["ptype"]
            post["floor"] = t["content"]["post_no"]
            # post["device"] = t["content"]["open_type"]
            post["comment_num"] = t["content"]["comment_num"]
            post["sign"] = post_info[2]
            post["imgs"] = post_info[3]
            post["smiley"] = post_info[4]
            post_list.append(post)
    except KeyError:
        log.warning("抓取贴子:"+tid+"失败，遇到KeyError")
        return []
    except Exception:
        log.exception("Exception Logged")
        return []
    return post_list

def get_user_detail(username):
    payload = {'ie':'utf-8'}
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    content = requests.get('http://www.baidu.com/p/'+username+'/detail',params=payload, headers=headers).content.decode('utf-8')
    raws = re.findall('<span class=profile-attr>个人简介</span> <span class=profile-cnt>(.*?)</span>',content)
    if raws: return raws[0]
    else:return "这个人并没有个人简介"

def get_page_num(tid):
    url = 'http://tieba.baidu.com/p/'+tid
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    raw = requests.get(url, params={'pn':1}, headers=headers).text
    num = re.findall('回复贴，共<span class="red">(.*?)</span>页</li>', raw)
    return num[0]

def get_comment(tid,pid,pn):
    try:
        posts = []
        headers = {'Cookie':data.cookie,'User-Agent':data.UA}
        url = 'http://tieba.baidu.com/p/comment?tid='+str(tid)+'&pid='+str(pid)+'&pn='+str(pn)
        raw = requests.get(url, headers=headers).text
        content =BeautifulSoup(raw,'html.parser')
        comments = content.find_all("li",class_=re.compile("lzl_single_post"))
        for comment in comments:
            post = json.loads(comment['data-field'])
            post["text"] = comment.find("span",class_="lzl_content_main").text.strip(' ')
            post["time"] = comment.find("span",class_='lzl_time').text
            post["tid"] = tid
            post["pid"] = pid
            posts.append(post)
        return posts
    except KeyError:
        log.warning("爬取楼中楼出现KeyError，tid:"+tid+"pid:"+pid)
    except Exception:
        log.exception("Exception Logged") 
        return []
def blockid(pid, username,reason="恶意刷屏、挖坟、水贴、抢楼、带节奏等，给予封禁处罚",day = 1):
    data.tbs = get_tbs()
    url = 'http://tieba.baidu.com/pmc/blockid'
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    payload = {'day':day,'ie':'utf8','fid':data.fid,'tbs':data.tbs, 'user_name[]':username,'pid[]':pid,'reason':reason}
    r = requests.post(url, data = payload, headers = headers)
    status = json.loads(r.text)
    return status

def delete_post(tid,pid):#批量删帖接口
    url = 'http://tieba.baidu.com/bawu2/postaudit/audit'
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    payload = {'ie':'utf8','kw':data.aim_tieba,'tids[]':tid,'pids[]':pid,'flag':2,'type':1}
    r = requests.post(url, data = payload, headers = headers)
    status = json.loads(r.text)
    return status
def delete_comment(tid,spid):
    data.tbs = get_tbs()
    url = 'http://tieba.baidu.com/f/commit/post/delete'
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    payload = {'ie':'utf8','kw':data.aim_tieba,'tid':tid,'pid':spid,'tbs':data.tbs,'fid':data.fid}
    r = requests.post(url, data = payload, headers = headers)
    status = json.loads(r.text)
    return status
def delete_thread(tid):#管理工具删整贴接口
    url = 'http://tieba.baidu.com/bawu2/postaudit/audit'
    headers = {'Cookie':data.cookie,'User-Agent':data.UA}
    payload = {'ie':'utf8','kw':data.aim_tieba,'tids[]':tid,'flag':2,'type':0}
    r = requests.post(url, data = payload, headers = headers)
    status = json.loads(r.text)
    return status





