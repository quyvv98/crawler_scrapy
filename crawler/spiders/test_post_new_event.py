import json
import logging
from crawler.items import NewEvents
import scrapy
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup


class NewEventSpider(scrapy.Spider):
    name = 'example_post_new_event'
    allowed_domains = ["vsd.vn"]
    domain = "https://vsd.vn"
    origin_page = "https://vsd.vn/vi//alo/ISSUER"
    current_date = datetime.today().strftime('%d/%m/%Y')
    cookies = {
        'lang': 'vi',
        '__VPToken': 'CfDJ8Nm1C6sP5ylPtyYhD-tg5z2SkDxl6cSVsqblbj9mPGgBN8oJg4q1PX6nwUe5follMiLiOnQFXgzsYpW5jcRnFPkV3ML6vaSSnwVHIoDGCokcB9p3yj8X1ckgubQDsLvsm2Tw2Jpv6UJFvqlw6J01Y1k',
        '__atuvc': '14%7C34',
        '__atuvs': '612686f9e4a748fe000',
    }

    headers = {
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
        'Accept': '*/*',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua-mobile': '?0',
        '__VPToken': 'CfDJ8Nm1C6sP5ylPtyYhD-tg5z2ZdsfBKKdnY6qVTILQggfE5ICDLp22g5MNemTEzfFhnLxpzTjufcs0sslwQtdeRvhS1TyJGvc42WTDeQQPTZgSty9k5m9ACXltVUtT2WCiMOGhLwHP32ZmIVfarewvMmA',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://vsd.vn',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    def start_requests(self):
        # yield scrapy.Request(url=self.origin_page, callback=self.parse)

        data = '{"CurrentPage":6}'
        yield scrapy.Request(self.origin_page, callback=self.parse, method="POST", headers=self.headers,
                             body=json.dumps(data),
                             cookies=self.cookies)

    def parse(self, response):
        logging.info("Start parse response")

        message_events = NewEvents()
        events = []
        # list_new = response.css('#d_list_news').css('li')
        list_new = response.css('.list-news')
        if len(list_new) == 0:
            return
        news = list_new[0].css('li')
        for new_event in news:
            event = {'title': new_event.css('a::text').get(),
                     'link': self.domain + new_event.css('a').attrib['href'],
                     'date': new_event.css('.time-news::text').get()
                     }
            events.append(event)
        message_events['events'] = self.format_message_to_mattermost(events)

        yield message_events

        data = '{"CurrentPage":6}'

        response = requests.post('https://vsd.vn/vi//alo/ISSUER', headers=self.headers, cookies=self.cookies, data=data)
        html_file = BeautifulSoup(response.text, "html.parser")
        news = html_file.select_one('ul.list-news').select('li')
        for new in news:
            link_element = new.select_one('a')
            link = link_element['href']
            title = link_element.get_text()
            date = new.select_one('.time-news').get_text()
            print(link, news)
        message_events['events'] = response.text
        yield message_events

    @staticmethod
    def extract_date(date):
        get_date = re.search("([0-9]{2}/[0-9]{2}/[0-9]{4})", date)
        return get_date[0]

    def format_message_to_mattermost(self, events):
        message = f' ##### New events Test sample post. Time: {self.current_date} \n'
        if len(events) == 0:
            message += "Dont't have new events."
            return message
        message += "| STT  | Title | Date |  Link  | \n"
        message += "| :--: |:--:|:--:| :---: | \n"
        for i, event in enumerate(events, 1):
            title = event['title']
            link = event['link']
            date = event['date']
            message += f'| {i}  | {title} | {date} | {link} | \n'
        return message
