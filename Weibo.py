import requests
from lxml import etree
import time
import sys
import csv
import re
import pymysql
import warnings
class SinaSpider():
    def __init__(self):
        self.baseurl1 = 'https://s.weibo.com/top/summary?cate=realtimehot'
        self.baseurl2 = 'https://s.weibo.com/hot?q=%23标题%23&xsort=hot&suball=1&tw=hotweibo&Refer=weibo_hot'
        self.headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"}
        #请按需启用
        self.cookies = {
            'SINAGLOBAL':'3425149804340.5127.1511698722545',
            'SCF':'AhV9Z-4tJwVkNFrGthhvNm_x39FZCK4BZHjkj08D8o5Cgpzui04kaaa8ipXIwuoHxevdW0uDILuBcQ3RF57Kp3E.',
            'SUHB':'0vJIH202zM5n6n',
            '_ga':'GA1.2.1102205272.1532400939',
            '__gads=ID':'8a8fc94b6e112587:',
            'T':'1532400941:',
            'S':'ALNI_MZSip3yAcV9nXkaVu5EOBsiT8HaJg',
            '_td':'97d32d4b-5846-41cc-b2cc-4b5b71935569',
            'td_cookie': '18446744071956944427',
            'SUB': '_2AkMrHAVsdcPxrAZZnvwWymjhb41H-jyYyWyaAn7uJhMyAxh77loSqSdutBF-XFQDb5B_nDjr1RoLSC5sCszikua6',
            'SUBP': '0033WrSXqPxfM72wWs9jqgMF55529P9D9W5CWEbMke59zuGIDcHxSI4b5JpV2hef1hBXS0.7S-WpMC4odcXt',
            'UOR': ',,zh.wikipedia.org',
            '_s_tentry': '-',
            'Apache': '6367147457855.326.1549157043017',
            'ULV': '1549157043045:13:2:1:6367147457855.326.1549157043017:1549069563135',
            'WBtopGlobal_register_version': 'ae9a9ec008078a68',
            'login_sid_t': '2e19afd3860591477eeee89f240a9b94',
            'cross_origin_proto': 'SSL',
            'WBStorage': '1dbe672167e426cb',
        }
        self.db = pymysql.connect(
            "127.0.0.1",
            "root",
            "root",
            "spiderdb",
            charset="utf8")
        # 游标对象
        self.cursor = self.db.cursor()
    def getPage(self):
        head = self.headers
        #请求热搜榜地址
        hotSearchR = requests.get(url=self.baseurl1,headers = self.headers,cookies=self.cookies)
        hotSearchR.encoding='utf-8'
        #获得热搜榜地址响应页面
        hotSearchP = hotSearchR.text
        self.parsePage(hotSearchP,head)

    #可优化:增量爬取榜单
    def parsePage(self,hotSearchP,head):
        parseP = etree.HTML(hotSearchP)
        hotSearchList = parseP.xpath('//td/a/text()')
        if hotSearchList == []:
            print('xpath错误')
        #获取到热搜列表,遍历.同时再发get请求给baseurl2,然后组成新列表再处理.
        #准备url列表
        getList2 = []
        #拼接url
        hotUrlhead = 'https://s.weibo.com/hot?q=%23'
        hotUrltail = '%23&xsort=hot&suball=1&tw=hotweibo&Refer=weibo_hot'
        for s in hotSearchList:
            # print(s)
            url=hotUrlhead+str(s)+hotUrltail
            getList2.append(url)
        #测试热门url列表,通过
        print('共有%d'%len(getList2)+'个话题,准备爬取')
        time.sleep(1)
        self.parsePage2(getList2,head,s)

    #解析热门url列表
    def parsePage2(self,hotWBList,head,s):
        #批量爬取，遍历热搜榜url,使用enumerate同时获取索引和元素
        for topic,url in enumerate(hotWBList):
            Pagespider = requests.get(url=url,headers = head,cookies=self.cookies)
            Pagespider.encoding = 'utf-8'
            PagespiderP = Pagespider.text
            testXPath = etree.HTML(PagespiderP)
            #获取该页面的页数
            divPage = testXPath.xpath('//*[@id="pl_feedlist_index"]/div/div/span/ul/li')
            # print(divPage)
            #将话题标题从URL链接中提取出来
            name = hotWBList[topic]
            name = re.sub("[A-Za-z0-9\?\=\:\_\.\&\!\%\[\]\,\。\[/]", "",name)
            print('正在爬取的话题是\n %s' % name)
            print(len(divPage))
            #判断页数
            if len(divPage) == 0:
                print('警告,本话题只有1页。')
                # xpath匹配外部div
                divList = testXPath.xpath('//*[@id="pl_feedlist_index"]/div/div/div')
                st = 1
                p = False
                self.parsePage3(divList,name,p,st)
                print('单页结束')
            # 多页就爬每一页
            else:
                print('有多页数据。')
                #遍历页数列表
                for p,k in enumerate(range(1,len(divPage)+1)):
                    address = url + '&page=' + str(k)
                    print('正在爬取第%d页'%p)
                    time.sleep(1)
                    #再对每页发请求
                    Page2spider = requests.get(url=address, headers=head,cookies=self.cookies)
                    Page2spider.encoding = 'utf-8'
                    Page2spiderP = Page2spider.text
                    testXPath2 = etree.HTML(Page2spiderP)
                    # 可重用
                    l = []
                    divList = testXPath2.xpath('//*[@id="pl_feedlist_index"]/div/div/div')
                    st = False
                    self.parsePage3(divList,name,p,st)

    #页面解析函数,p和st是为了处理json中的页数,必传
    def parsePage3(self,divList,name,p=0,st=0):
        for element in divList:
            #用户名
            uname = element.xpath('./div[@class="card-feed"]/div/p/@nick-name')
            if len(uname) == 2:
                uname = uname[0]
            #评论,点赞,转发外部div
            uactive = element.xpath('./div[@class="card-act"]/ul/li/a')
            uList = element.xpath('./div[@class="card-act"]/ul/li/a/text()')
            # 使用列表推导式去除多余' '，收藏
            uList = [x for x in uList if x != ' ' and x != '收藏']
            # 转发与评论分开
            usend = uList[0]
            ucomment = uList[1]
            #点赞
            for content in uactive:
                ugood = content.xpath('./em/text()')
            #微博链接
            uhref = element.xpath('./div[@class="card-feed"]/div/p[@class="from"]/a/@href')
            if len(uhref) == 2:
                uhref = uhref[0]
                notice = '该用户发表了视频或图片'
            else:
                uhref = uhref
                notice = ''
            if st == 1:
                d = {
                    '话题': name,
                    '页数': st,
                    '用户名': uname,
                    '链接': uhref,
                    '转发': usend,
                    '评论': ucomment,
                    '点赞': ugood,
                    '备注': notice,
                }
            else:
                page = p
                d = {
                    '话题': name,
                    '页数': page + 1,
                    '用户名': uname,
                    '链接': uhref,
                    '转发': usend,
                    '评论': ucomment,
                    '点赞': ugood,
                    '备注': notice,
                }
            #请根据自身需要启用
            # self.saveMysql(d)
            # self.savePage(d)

    #保存到json
    def savePage(self,d):
        with open("./Sinadata/weibo.json", "a", encoding="utf-8") as f:
            f.write(str(d) + '\n')
    #保存到Mysql
    def saveMysql(self,d):
        list2 = list(d.values())
        print(list2)
        warnings.filterwarnings("ignore")
        ins = 'insert into sina(\
                  name,page,uname,uhref,usend,ucomment,ugood,notice) \
                  values(%s,%s,%s,%s,%s,%s,%s,%s)'
        self.cursor.execute(ins, list2)
        self.db.commit()
        input('ss')
    def workOn(self):
        print('正在爬取')
        self.getPage()
        sys.exit('爬取完毕,程序结束')

if __name__ == '__main__':
    spider = SinaSpider()
    spider.workOn()
