import urllib
import http.cookiejar
import json
import re
import threading
import sys
import getopt
import logging
import getpass
import socket

logger = logging.getLogger()    # initialize logging class
logger.setLevel(logging.DEBUG)  # default log level
logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')


profileID = 0

socket.setdefaulttimeout(2)


class Header:
    header = {
            'Connection': 'Keep-Alive',
            'Accept-Language': 'zh-CN',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/45.0.2454.101 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
            }
    def __init__(self,header = None):
        if not header == None:
            self.header = header

    def GetHeader(self):
        return self.header

class Opener:
    header = None
    cookie = http.cookiejar.CookieJar()
    opener = None

    def __init__(self,header):
        self.header = header

        cj = self.cookie
        pro = urllib.request.HTTPCookieProcessor(cj)
        opener = urllib.request.build_opener(pro)
        header = []
        for key, value in self.header.GetHeader().items():
            elem = (key, value)
            header.append(elem)
        opener.addheaders = header
        self.opener = opener

    def GetOpener(self):
        return self.opener

    def open(self,url,para = None):
        return self.opener.open(url,para)

class Course:
    __id = None
    __name = None
    __no = None #课程序号
    __code = None #课程代码
    __teacher = None
    __campusName = None
    __courseTypeName = None

    def __init__(self,courseDetail):
        try:
            self.__id = courseDetail['id']
            self.__no = courseDetail['no']
            self.__name = courseDetail['name']
            self.__code = courseDetail['code']
            self.__teacher = courseDetail['teachers']
            self.__campusName = courseDetail['campusName']
            self.__courseTypeName = courseDetail['courseTypeName']
        except:
            return

    def GetID(self):
        return self.__id

    def GetName(self):
        return self.__name

    def GetCode(self):
        return self.__code

    def GetTeacher(self):
        return self.__teacher

    def GetCampusName(self):
        return self.__campusName

    def GetCourseTypeName(self):
        return self.__courseTypeName

class SSO:
    account = None
    password = None

    #SSOURL = 'http://sso.lixin.edu.cn/authorize.php?client_id=ufsso_supwisdom_jw&redirect_uri=http%3A%2F%2Fnewjw.lixin.edu.cn%2Fsso%2Findex&state=1q2w3e&response_type=code'
    SSOURL = 'http://newjw.lixin.edu.cn/sso/login'
    ResponseHeader = None
    ResponseContent = None
    LoginOpener = None
    opener = None


    def __init__(self,account,password):
        self.account = account
        self.password = password

    def Login(self):
        if self.LoginOpener:
            return
        self.opener = Opener(Header())
        postPara = {
                'username' : self.account,
                'password' : self.password
                }
        postData = urllib.parse.urlencode(postPara).encode()
        op = self.opener.open(self.SSOURL,postData)
        self.ResponseHeader = op.info()
        self.ResponseContent = op.read().decode()

    def GetLoginedOpener(self):
        return self.opener

    def GetResponseHeader(self,attr = None):
        if attr == None:
            return self.ResponseHeader
        return self.ResponseHeader[attr]

class Login:
    account = None
    password = None

    opener = None

    setURL = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!innerIndex.action'
    setURL2 = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!defaultPage.action?electionProfile.id='


    def __init__(self,account,password):
        self.account = account
        self.password = password
        self.setURL2 += str(profileID)

    def __SSOAuth(self):
        sso = SSO(self.account,self.password)
        sso.Login()
        self.opener = sso.GetLoginedOpener()

    def Login(self):
        self.__SSOAuth()

        self.opener.open(self.setURL)
        self.opener.open(self.setURL2)


    def GetLoginedOpener(self):
        return self.opener

    def Relogin(self):
        self.Login()



class Select(threading.Thread):
    '''
    noexcept类
    '''
    opener = None

    replaceList = ['思考:信息'] # 因为课程信息使用的不是json，而是一个js对象数组，我使用了Parse2JsonStr的函数，但是有的课程中有“:”，这样导致这个函数不能正确工作，因此需要手动将这些课程的敏感名称替换掉

    selectURL = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!batchOperator.action?profileId='
    courseListURL = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!data.action?profileId='
    courseList = {}

    __courseCode = None
    def __init__(self,login,courseCode):
        self.selectURL += str(profileID)
        self.courseListURL += str(profileID)

        threading.Thread.__init__(self)
        self.__courseCode = courseCode
        self.opener = login.GetLoginedOpener()
        self.__GetCourseList()
        self.__flag = threading.Event()     # 用于暂停线程的标识
        self.__flag.set()       # 设置为True
        self.__running = threading.Event()      # 用于停止线程的标识
        self.__running.set()      # 将running设置为True

    def run(self):
        while self.__running.isSet():
            self.__flag.wait()
            try:
                self.__GetCourse()
            except Exception as e:
                continue
            
    def pause(self):
        self.__flag.clear()
    
    def resume(self):
        self.__flag.set()

    def stop(self):
        self.__flag.set()
        self.__running.clear()

    def __Parse2JSONStr(self,expr):
        for keyword in self.replaceList:
            expr = expr.replace(keyword, '')
        expr = expr.replace('{','{"').replace(':','":').replace(',',',"').replace('\'','"').replace('},"{"','},{"')
        expr2 = list(expr)
        nQuotation = 0
        i = -1
        while 1:
            i = expr.find('"',i + 1) 
            if i == -1:
                break
            nQuotation = nQuotation + 1
            if (nQuotation % 2 == 0 and expr[i-1] == ','):
                expr2[i] = ' '
                nQuotation = nQuotation - 1
 
        return "".join(expr2)

    def __GetCourseList(self):
        op = self.opener.open(self.courseListURL)
        data = op.read().decode()
        start = data.find('=') + 2
        end = len(data)
        parsedJson = self.__Parse2JSONStr(data[start:end-1])
        courses = json.loads(parsedJson)
        for course in courses:
            newCourse = Course(course)
            self.courseList[course['code']] = newCourse

    #通过课程代码搜索课程数据
    def __FindCourseByCode(self,code):
        if code in self.courseList:
            return self.courseList[code]
        return False

    def __PostCourse(self,course):
        postPara = {
                'operator0' : str(course.GetID()) + ':true:0'
                }
        postData = urllib.parse.urlencode(postPara).encode()
        while 1:
            try:
                op = self.opener.open(self.selectURL,postData)
            except Exception as e:
                continue
            
            returnData = op.read().decode()

            findMax = re.compile('人数已满').findall(returnData)
            if findMax:
                continue

            findSuccess = re.compile('选课成功').findall(returnData)
            if findSuccess:
                return (True, '')

            brTag = returnData.find('</br>') #</br>标签作为返回信息的一个标志
            for i in range(brTag, 0, -1):
                if returnData[i] == '\t':
                    error = returnData[i + 1:brTag]
                    break

            return (False, error)


    def __GetCourse(self):
        course = self.__FindCourseByCode(self.__courseCode)
        if not course:
            logging.warning('课程代码不存在或不可选')
            return
        print('正在抢以下课程：\n课程名：%s\n任课老师：%s\n开课校区：%s\n课程类型：%s\n' % (course.GetName(),course.GetTeacher(),course.GetCampusName(),course.GetCourseTypeName()))
        
        selectSuccess = False
        while not selectSuccess:
            try:
                selectSuccess, error = self.__PostCourse(course)
            except Exception as e:
                #网络错误重新
                continue

            if selectSuccess:
                logging.info('%s抢课成功' % self.__courseCode)
                self.stop()
            else:
                logging.error('对于%s,%s' % (self.__courseCode, error))
                if re.compile('expired').findall(error):
                    login.Relogin()
                    self.opener = login.GetLoginedOpener()
                else:
                    logging.warning('对于%s的抢课已经停止' % (self.__courseCode))
                    self.stop()
                    break


def doLogin(username,password):
    while(True):
        try:
            login = Login(username,password)
            login.Login()
            return login
        except Exception as e:
            logging.error(e);


if __name__ == '__main__':
    username = None
    password = None
    courseCodes = []   #要抢的课程列表


    opts, args = getopt.getopt(sys.argv[1:], "-h-u:-p:-i:-c:", ['username=', 'password=', 'pid=', 'help', 'course='])
    for opt_name, opt_val in opts:
        if opt_name in ('-u', '--username'):
            username = opt_val
        elif opt_name in ('-p', '--password'):
            password = opt_val
        elif opt_name in ('-i', '--pid'):
            profileID = opt_val
        elif opt_name in ('-c', '--course'):
            courseCodes = opt_val.split(',')
        elif opt_name in ('-h', '--help'):
            print('使用方法：CourseCannon.py [选项] [参数]')
            print('{:15s}: {}'. format('-h', '显示帮助。(另--help)'))
            print('{:15s}: {}'. format('-u username', '输入用户名(另--username=x)'))
            print('{:15s}: {}'. format('-p password', '输入密码(另--password=x)'))
            print('{:15s}: {}'. format('-i profileId', '输入 profile id. (另--pid=x)'))
            print('{:15s}: {}'. format('-c courses', '输入想要抢的课程，以123,34,555这种格式 (另--course=x)'))
            sys.exit()

    print('本程序采用GPLv3协议，侵权者请注意您将负法律责任。不允许将本程序及其衍生程序进行任何商业化行为。\n')
    print('上海立信会计金融学院CrazySpy制作 2018\n')

    print('请务必输入正确的用户名和密码，本程序未完成登录错误判断部分。\n')


    if (username is None) or (password is None):
        username = input('请输入sso用户名:\n')
        password = getpass.getpass('请输入sso密码:\n')

    if profileID == 0:
        profileID = int(input('请输入profileID:'))
    
    login = doLogin(username,password)
      
    workingThread = [] #当前抢课线程池
    
    
    for code in courseCodes:
        s = Select(login,code)
        s.start()
        workingThread.append(s)
        
    while 1:
        courseCode = input('请输入所要的课程的课程代码:\n')
        if(len(courseCode) == 0): continue
        courseCodes.append(courseCode)
        s = Select(login,courseCode)
        s.start()
        workingThread.append(s)

