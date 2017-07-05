# TiebaTool
##介绍
整理了百度贴吧的常用接口，并封装成库。在此基础上实现了一个多线程吧务管理工具，可实现贴吧的回复、楼中楼、用户名的关键词过滤匹配并进行删除或封禁操作。还提供首页的相同标题贴及同一用户发贴量的控制。

## 使用方法
*安装依赖 `pip3 install jieba beautifulsoup4`

*在`config.py`中填入目标贴吧与具有管理权限的账号的贴吧Cookie，并按照说明配置相应参数

*执行`python3 run.py`

## `tiebalib`库使用说明
```
import tiebalib

#进行初始化
tiebalib.initialize("目标贴吧","cookie")

#获取tbs
tiebalib.get_tbs()

#获取贴吧贴子列表，默认第一页，返回一个list，贴子信息以dict储存
tiebalib.get_thread_list(aim_tieba = data.aim_tieba,pn=0):

#通过tid获取贴子内容，pn为页码，大于有效页码默认读取最后一页，返回一个list，回复信息以dict储存
get_post(tid,pn=9999)

#删帖和封禁功能
blockid(pid, username,reason="恶意刷屏、挖坟、水贴、抢楼、带节奏等，给予封禁处罚",day = 1)
#删除贴子（可接受tid与pid一一对应的list实现批量删除）
delete_post(tid,pid)
#删除楼中楼
delete_comment(tid,spid)
#仅通过tid删除主题贴
delete_thread(tid)
```