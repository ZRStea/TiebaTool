import time
import requests
from selenium import webdriver



def login(name, passwd):
    url = 'https://passport.baidu.com/v2/?login'
    # 这里可以用Chrome、Phantomjs等，如果没有加入环境变量，需要指定具体的位置
    driver = webdriver.Chrome()
    driver.get(url)
    print('开始登录')

    name_field = driver.find_element_by_id('TANGRAM__PSP_3__userName')
    name_field.send_keys(name)
    time.sleep(1)
    passwd_field = driver.find_element_by_id('TANGRAM__PSP_3__password')
    passwd_field.send_keys(passwd)
    time.sleep(1)
    login_button = driver.find_element_by_id('TANGRAM__PSP_3__submit')
    login_button.click()
    time.sleep(5)
    driver.quit()
    #return driver.get_cookie("BDUSS")
    return driver.get_cookies()


if __name__ == '__main__':
    username = ''
    password = ''
    cookies = login(username, password)
    login_cookie = ''
    for cookie in cookies:
        login_cookie += cookie['name'] + '=' + cookie['value'] + ';'
        
    print(login_cookie)
    TbsUrl = 'http://tieba.baidu.com/dc/common/tbs'
    headers = {"Cookie":login_cookie}
    tbs_json = requests.get(TbsUrl, headers = headers)
    print(tbs_json.text)
