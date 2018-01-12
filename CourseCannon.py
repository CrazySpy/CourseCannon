import urllib;
import http.cookiejar;
import json;
import re;
import threading;

profileID = 50;


class Header:
    header = {
            'Connection': 'Keep-Alive',
            'Accept-Language': 'zh-CN',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/45.0.2454.101 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
            };
    def __init__(self,header = None):
        if not header == None:
            self.header = header;

    def GetHeader(self):
        return self.header;

class Opener:
    header = None;
    cookie = http.cookiejar.CookieJar();
    opener = None;

    def __init__(self,header):
        self.header = header;

        cj = self.cookie;
        pro = urllib.request.HTTPCookieProcessor(cj);
        opener = urllib.request.build_opener(pro);
        header = [];
        for key, value in self.header.GetHeader().items():
            elem = (key, value);
            header.append(elem);
        opener.addheaders = header;
        self.opener = opener;

    def GetOpener(self):
        return self.opener;

    def open(self,url,para = None):
        return self.opener.open(url,para);

class Course:
    __id = None;
    __name = None;
    __no = None; #课程序号
    __code = None; #课程代码
    __teacher = None;
    __campusName = None;
    __courseTypeName = None;

    def __init__(self,courseDetail):
        try:
            self.__id = courseDetail['id'];
            self.__no = courseDetail['no'];
            self.__name = courseDetail['name'];
            self.__code = courseDetail['code'];
            self.__teacher = courseDetail['teachers'];
            self.__campusName = courseDetail['campusName'];
            self.__courseTypeName = courseDetail['courseTypeName'];
        except:
            return;

    def GetID(self):
        return self.__id;

    def GetName(self):
        return self.__name;

    def GetCode(self):
        return self.__code;

    def GetTeacher(self):
        return self.__teacher;

    def GetCampusName(self):
        return self.__campusName;

    def GetCourseTypeName(self):
        return self.__courseTypeName;

class SSO:
    account = None;
    password = None;

    #SSOURL = 'http://sso.lixin.edu.cn/authorize.php?client_id=ufsso_supwisdom_jw&redirect_uri=http%3A%2F%2Fnewjw.lixin.edu.cn%2Fsso%2Findex&state=1q2w3e&response_type=code';
    SSOURL = 'http://newjw.lixin.edu.cn/sso/login';
    ResponseHeader = None;
    ResponseContent = None;
    LoginOpener = None;
    opener = None;


    def __init__(self,account,password):
        self.account = account;
        self.password = password;

    def Login(self):
        if self.LoginOpener:
            return;
        self.opener = Opener(Header());
        postPara = {
                'username' : self.account,
                'password' : self.password
                };
        postData = urllib.parse.urlencode(postPara).encode();
        op = self.opener.open(self.SSOURL,postData);
        self.ResponseHeader = op.info();
        self.ResponseContent = op.read().decode();

    def GetLoginedOpener(self):
        return self.opener;

    def GetResponseHeader(self,attr = None):
        if attr == None:
            return self.ResponseHeader;
        return self.ResponseHeader[attr];

class Login:
    account = None;
    password = None;

    opener = None;

    setURL = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!innerIndex.action';
    setURL2 = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!defaultPage.action?electionProfile.id=' + str(profileID);


    def __init__(self,account,password):
        self.account = account;
        self.password = password;

    def __SSOAuth(self):
        sso = SSO(self.account,self.password);
        sso.Login();
        self.opener = sso.GetLoginedOpener();

    def Login(self):
        self.__SSOAuth();

        self.opener.open(self.setURL);
        self.opener.open(self.setURL2);


    def GetLoginedOpener(self):
        return self.opener;

    def Relogin(self):
        self.Login();

    '''
    class SessionExpire(Exception):
        message = None;
        def __init__(self):
            self.message = 'Session has been expired.';
    '''
    
class Select(threading.Thread):
    opener = None;

    selectURL = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!batchOperator.action?profileId=' + str(profileID);
    courseListURL = 'http://newjw.lixin.edu.cn/webapp/std/edu/lesson/std-elect-course!data.action?profileId=' + str(profileID);
    courseList = {};

    __courseCode = None;
    def __init__(self,login,courseCode):
        threading.Thread.__init__(self);
        self.__courseCode = courseCode;
        self.opener = login.GetLoginedOpener();
        self.__GetCourseList();
        self.__flag = threading.Event();     # 用于暂停线程的标识
        self.__flag.set();       # 设置为True
        self.__running = threading.Event();      # 用于停止线程的标识
        self.__running.set();      # 将running设置为True

    def run(self):
        while self.__running.isSet():
            self.__flag.wait();
            self.__GetCourse();
            
    def pause(self):
        self.__flag.clear();
    
    def resume(self):
        self.__flag.set();

    def stop(self):
        self.__flag.set();
        self.__running.clear();

    def __Parse2JSONArray(self,expr):
        expr = expr.replace('{','{"').replace(':','":').replace(',',',"').replace('\'','"').replace('},"{"','},{"');
        expr2 = list(expr);
        nQuotation = 0;
        i = -1;
        while 1:
            i = expr.find('"',i + 1); 
            if i == -1:
                break;
            nQuotation = nQuotation + 1;
            if (nQuotation % 2 == 0 and expr[i-1] == ','):
                expr2[i] = ' ';
                nQuotation = nQuotation - 1;
 
        return "".join(expr2);

    def __GetCourseList(self):
        op = self.opener.open(self.courseListURL);
        data = op.read().decode();
        start = data.find('=') + 2;
        end = len(data);
        parsedJson = self.__Parse2JSONArray(data[start:end-1]);
        courses = json.loads(parsedJson);
        for course in courses:
            newCourse = Course(course);
            self.courseList[course['code']] = newCourse;

    #通过课程代码搜索课程数据
    def __FindCourseByCode(self,code):
        if code in self.courseList:
            return self.courseList[code];
        return False;

    def __PostCourse(self,course):
        postPara = {
                'operator0' : str(course.GetID()) + ':true:0'
                };
        postData = urllib.parse.urlencode(postPara).encode();
        while 1:
            op = self.opener.open(self.selectURL,postData);
            returnData = op.read().decode();

            findMax = re.compile('人数已满').findall(returnData);
            if findMax:
                continue;

            findError = re.compile('操作失败').findall(returnData);
            if findError:
                return 500;
            findSuccess = re.compile('选课成功').findall(returnData);
            if findSuccess:
                return 200;

            findConflict = re.compile('课程冲突').findall(returnData);
            if findConflict:
                return 501;
            
            findExpire = re.compile('expired').findall(returnData);
            if findExpire:
                return 502;

            return 1000;
        
    def __GetCourse(self):
        course = self.__FindCourseByCode(self.__courseCode);
        if not course:
            print('课程代码不存在或不可选\n');
            return;
        print('正在抢以下课程：\n课程名：%s\n任课老师：%s\n开课校区：%s\n课程类型：%s\n' % (course.GetName(),course.GetTeacher(),course.GetCampusName(),course.GetCourseTypeName()));
        endCode = -1;
        while(endCode < 0):
            try:
                endCode = self.__PostCourse(course);
            except urllib.error.HTTPError:
                #网络错误重新
                pass;
        
        if endCode == 200:
            print('%s抢课成功\n' % self.__courseCode);
        elif endCode == 500:
            print('%s操作失败\n' % self.__courseCode);
        elif endCode == 501:
            print('%s选课冲突\n' % self.__courseCode);
        elif endCode == 502:
            print('%sSession超时,正在重新登录.\n' % self.__courseCode);
            login.Relogin();
            self.opener = login.GetLoginedOpener();
        else:
            print('未知问题:%d\n' % (self.__courseCode,endCode));

def doLogin(username,password):
    while(True):
        try:
            login = Login(username,password);
            login.Login();
            return login;
        except URLError:
            print("登录超时，正在重试\n");

if __name__ == '__main__':
    print('本程序采用GPLv3协议，侵权者请注意您将负法律责任。不允许将本程序及其衍生程序进行任何商业化行为。\n');
    print('上海立信会计金融学院CrazySpy制作 2017\n');

    print('请务必输入正确的用户名和密码，本程序未完成登录错误判断部分。\n');
    username = None;
    password = None;
    if username == None or password == None:
        username = input('请输入sso用户名:\n');
        password = input('请输入sso密码:\n');
    
    login = doLogin(username,password);
      
    workingThread = [];
    courseCodes = [];
    
    for code in courseCodes:
        s = Select(login,code);
        s.start();
        workingThread.append(s);
    while(True):
        courseCode = input('请输入所要的课程的课程代码:\n');
        if(len(courseCode) == 0):
            continue;
        try:
            courseCodes.append(courseCode);
            s = Select(login,courseCode);
            s.start();
            workingThread.append(s);
        except (http.client.RemoteDisconnected,Login.SessionExpire) as e:
            print("发生错误:%s,即将重新登录并选课\n",e.message);
            for thread in workingThread:
                thread.stop();
            workingThread.clear();
            login = doLogin(username,password);
            for code in courseCodes:
                s = Select(login,code);
                s.start();
                workingThread.append(s);

            
