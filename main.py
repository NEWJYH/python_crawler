from selenium import webdriver

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import subprocess
from webdriver_manager.core.utils import ChromeType
# import os

import requests

import asyncio

from bs4 import BeautifulSoup



COUPANG_URL = "https://www.coupang.com/"
NAVER_URL = "https://www.naver.com"


origin_headers = {
    'authority': 'www.coupang.com',
    'accept': '*/*',
    'accept-language': 'ko,ko-KR;q=0.9,en;q=0.8',
    'dnt': '1',
    'referer': 'https://www.coupang.com/np/search?component=&q=%ED%96%87%EB%B0%98&channel=user',
    'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}  

def set_chrome_driver():
  """setting chrome driver"""
  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
  path = ChromeDriverManager().install()
  print("ChromeDriverPath :", path)
  driver = webdriver.Chrome(service=Service(path), options=chrome_options)
  driver.maximize_window()
  return driver


def main():
  cookie_dict = {}
  URLS = []
  MAXPAGE  = -1
  HTMLSOURCELIST = []
  # 사용중인 모든 브라우저 종료 후 사용할 것*크롬
  subprocess.Popen(['/usr/bin/google-chrome-stable', '--remote-debugging-port=9222'])

  # 드라이버 초기화
  driver = set_chrome_driver()

  # 네이버 페이지 방문
  driver.get(NAVER_URL)
  driver.implicitly_wait(3)
  # 스크롤 내리기 
  # driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
  time.sleep(1)
  # 네이버 검색
  naver_searchbox = driver.find_element(By.ID, value="query")
  # 쿠팡 입력
  naver_searchbox.send_keys("쿠팡")
  driver.find_element(By.ID,value='search_btn').click()
  driver.implicitly_wait(2.5)
  # 쿠팡 홈페이지 방문
  select_box = driver.find_element(By.CLASS_NAME, value='nsite_tit')
  a_tag = select_box.find_element(By.TAG_NAME, "a")
  a_tag.click()
  
  # ------------- 쿠팡 
  # 새창으로 이동
  driver.switch_to.window(driver.window_handles[1])

  # 입력받기
  keyword = "노트북"
  time.sleep(0.5)

  # 쿠팡 검색창에 검색하기
  coupang_searchbox = driver.find_element(By.ID, value="headerSearchKeyword")
  coupang_searchbox.send_keys(keyword)
  coupang_searchbox.send_keys(Keys.ENTER)

  # 정렬 방법 고르기
  search_option = driver.find_element(By.CSS_SELECTOR, value ="#searchSortingOrder > ul > li:nth-child(4) > label" )
  search_option.click()
  driver.implicitly_wait(2.5)
  time.sleep(1)

  # 스크롤 내리기
  driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
  driver.implicitly_wait(2.5)

  # 페이지 얻기
  page_area = driver.find_element(By.CLASS_NAME, value='btn-page')
  a_tags = page_area.find_elements(By.TAG_NAME, value='a')
  for a in a_tags:
    MAXPAGE = int(a.text.strip())
    URLS.append(a.get_attribute('href'))

  
  # 쿠키 설정
  print("쿠키 설정합니다.")
  cookies = driver.get_cookies()
  for cookie in cookies:
    cookie_dict[cookie['name']] = cookie['value']
  
  # 헤더 설정
  print("헤더 설정합니다.")
  headers_ = driver.execute_script("var req = new XMLHttpRequest();req.open('GET', document.location, false);req.send(null);return req.getAllResponseHeaders()")
  headers = headers_.splitlines()
  for content in headers:
    index = content.find(":")
    key, value = content[:index].strip(), content[index+1:].lstrip()
    origin_headers[key] = value
  origin_headers['referer'] = driver.current_url

  # 비동기 설정
  starttime = time.time()
  loop = asyncio.get_event_loop()
  loop.run_until_complete(main_async(URLS, cookie_dict, origin_headers, HTMLSOURCELIST))
  loop.close()
  duringtime = time.time() - starttime
  print("진행 시간", duringtime)

  driver.quit()

  print(len(HTMLSOURCELIST))
  for item in HTMLSOURCELIST:
    print(item)


# 비동기 합쳐지는 곳
async def main_async(urls, cookies, headers, HTMLSOURCELIST) :

  await myRequests(urls, cookies, headers, HTMLSOURCELIST)
  

# 비동기 처리하는 부분
async def myRequests(urls, cookies, headers, HTMLSOURCELIST):
  my_res_text_list = []
  for url in urls:
    try:
      print(url)
      response = None
      response = requests.get(url=url, cookies=cookies, headers=headers)
      response.raise_for_status()
      my_res_text_list.append(response.text)
    except: 
      pass
  
  for text in my_res_text_list:
    HTMLSOURCELIST.extend(await get_target(text))

# 페이지 하나 뜯음
async def get_target(text):
  soup = BeautifulSoup(text, 'lxml')
  item_cards = soup.find(attrs={'id':'productList'}).find_all('li')
  one_page_value = []
  for item in item_cards:
    id = item.find('a')['data-item-id'].strip()
    if not id :
      continue
    name = item.find(attrs={'class':'name'}).get_text().strip()
    price = item.find(attrs={'class':'price-value'}).get_text().strip()
    rating = item.select_one('span.star')
    if rating:
      rating = rating.get_text().strip()
    else:
      rating = "0"
    rating_total = item.select_one('span.rating-total-count')
    if rating_total :
      rating_total = rating_total.get_text().strip()[1:-1]
    else:
      rating_total = "0"
    one_page_value.append(
      {
      "id": id,
      "name": name,
      "price": price if price else "",
      "rating": rating if rating else "0",
      "rating_total" : rating_total if rating_total else "0"
    }
    )
  return one_page_value


if __name__ == "__main__":
  main()
