from selenium import webdriver

def try_cookie_logined(cookie):# 测试cookie是否可用
    TbsUrl = 'http://tieba.baidu.com/dc/common/tbs'
    headers = {"Cookie":cookie}
    tbs_json = requests.get(TbsUrl, headers = headers)
    tbs_json = json.loads(tbs_json.text)
    return True if tbs_json['is_login'] == 1 else False

def get_cookie_by_selenium(username, password): # 获取Cookies
    url = 'https://passport.baidu.com/v2/?login'
    # 如果没有加入环境变量，需要指定具体的位置
    # driver = webdriver.Chrome(executable_path='/Users/resolvewang/Documents/program/driver/chromedriver')
    driver = webdriver.Chrome()
    driver.get(url)
    log.info('开始登录')

    name_field = driver.find_element_by_id('TANGRAM__PSP_3__userName')
    name_field.send_keys(username)
    time.sleep(1)
    passwd_field = driver.find_element_by_id('TANGRAM__PSP_3__password')
    passwd_field.send_keys(password)
    time.sleep(1)
    login_button = driver.find_element_by_id('TANGRAM__PSP_3__submit')
    login_button.click()
    time.sleep(5)
    #return driver.get_cookie("BDUSS")
    login_cookie = ''
    for cookie in driver.get_cookies():
        login_cookie += cookie['name'] + '=' + cookie['value'] + ';'
    driver.quit()
    return login_cookie if try_cookie_logined(login_cookie) else log.warning("登陆失败")