import logging
from crawler.items import NewEvents
import scrapy
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup


class NewEventSpider(scrapy.Spider):
    name = 'new_event'
    allowed_domains = ["vsd.vn"]

    def __init__(self, name=None, **kwargs):
        super().__init__(name)
        self.cookies, self.token = '', ''
        self.domain = "https://vsd.vn"
        self.origin_page = "https://vsd.vn/vi//alo/ISSUER"
        self.page = 1
        self.current_date = datetime.today().strftime('%d/%m/%Y')
        # self.current_date = '20/08/2021'
        self.events = []

    def start_requests(self):
        request = scrapy.Request(url=self.origin_page, callback=self.parse)
        yield request

    def parse(self, response):
        logging.info("Start parse response")

        # get cookies
        self.detectToken(response)

        message_events = NewEvents()
        list_new = response.css('.list-news')
        if len(list_new) == 0:
            return
        news = list_new[0].css('li')

        is_current_date = False
        for new_event in news:
            event = {'title': new_event.css('a::text').get(),
                     'link': self.domain + new_event.css('a').attrib['href'],
                     'date': new_event.css('.time-news::text').get()
                     }

            is_current_date = self.filter_events(event)
            if not is_current_date:
                break

        has_error = False
        if is_current_date:
            self.page += 1
            try:
                has_error = self.update_list_news_data()
            except:
                has_error = True
        message_events['events'] = self.format_message_to_mattermost(has_error)
        yield message_events

    @staticmethod
    def extract_date(date):
        get_date = re.search("([0-9]{2}/[0-9]{2}/[0-9]{4})", date)
        return get_date[0]

    def format_message_to_mattermost(self, has_error):
        message = f' ##### New events. Time: {self.current_date}. Total records: {len(self.events)}\n'
        for i, event in enumerate(self.events, 1):
            title = event['title']
            link = event['link']
            message += f'{i}: [{title}]({link}) \n'
        if has_error:
            message += f'Check missing events in [Page {self.page}](https://vsd.vn/vi//alo/ISSUER{self.page})\n'
        return message

    def update_list_news_data(self):

        cookies = {
            '__VPToken': self.cookies,
        }

        headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'Accept': '*/*',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua-mobile': '?0',
            '__VPToken': self.token,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://vsd.vn',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        data = '{"CurrentPage":' + str(self.page) + ' }'

        response = requests.post(
            self.origin_page, data=data, cookies=cookies, headers=headers)
        if response.status_code != 200:
            return True
        html_file = BeautifulSoup(response.text, "html.parser")
        news = html_file.select_one('ul.list-news').select('li')
        is_current_date = False
        for new in news:

            link_element = new.select_one('a')
            event = {'title': link_element.get_text(),
                     'link': self.domain + link_element['href'],
                     'date': new.select_one('.time-news').get_text()
                     }
            is_current_date = self.filter_events(event)
            if not is_current_date:
                break

        if is_current_date:
            self.page += 1
            self.update_list_news_data()
        return False

    def filter_events(self, event):
        date_str = self.extract_date(event['date'])
        if date_str >= self.current_date:
            self.events.append(event)
            return True
        return False

    def detectToken(self, response):
        # get cookies
        cookies = response.headers.getlist('Set-Cookie')[0].decode("utf-8")
        has_token = re.search("__VPToken=.+?;", cookies)
        if has_token:
            self.cookies = cookies.split(';')[0].split('=')[1]
        self.token = response.css('head').css('meta')[-1].attrib['content']

        # get token
        metas = response.css('head').css('meta')
        for meta in metas:
            if 'name' in meta.attrib and meta.attrib['name'] == '__VPToken':
                self.token = meta.attrib['content']
