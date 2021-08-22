# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import logging
import pymongo
import requests


class MongoPipeline(object):

    def __init__(self, mongo_uri, mongo_db, collection_name):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.collection_name = collection_name

    @classmethod
    def from_crawler(cls, crawler):
        # pull in information from settings.py
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE'),
            collection_name=crawler.settings.get('COLLECTION_NAME')
        )

    def open_spider(self, spider):
        # initializing spider
        # opening db connection
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        # clean up when spider is closed
        self.client.close()

    def process_item(self, items, spider):
        # how to handle each post
        self.db[self.collection_name].insert(dict(items))
        logging.debug("Post added to MongoDB")
        return items


class MattermostNotifier(object):

    def __init__(self, channel_url):
        self.channel_url = channel_url

    @classmethod
    def from_crawler(cls, crawler):
        # pull in information from settings.py
        return cls(
            channel_url=crawler.settings.get('CHANNEL_URL'),
        )

    def process_item(self, items, spider):
        headers = {'Content-Type': 'text/plain'}
        message = items['events']
        data = '{"text": ' + f'"{message}"' + ' }'
        data = data.encode()
        logging.info(f'Handle send message to mattermost. {data}')
        for i in range(5):
            logging.info(f'Retry time {i}')
            res = requests.post(self.channel_url, headers=headers, data=data)
            if res.status_code == 200:
                logging.info("Success send message to mattermost")
                break
            else:
                logging.info(f'Retry send message to mattermost{res}')
        return items

    def close_spider(self, spider):
        pass
