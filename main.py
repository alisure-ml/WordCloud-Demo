# coding:utf-8
import re
import os
import xml
import time
import json
import jieba
import string
import requests
import numpy as np
import collections
from PIL import Image
import multiprocessing
from xml.dom import minidom
import matplotlib.pyplot as plt
import urllib.request as request
from alisuretool.Tools import Tools
from wordcloud import WordCloud, STOPWORDS


class DataBilibili(object):

    def __init__(self, mid="392836434", page=1, pagesize=10):
        self.mid = mid
        self.page = page
        self.pagesize = pagesize
        self.save_path = "./data/{}_{}_{}.pkl".format(self.mid, self.page, self.pagesize)
        pass

    def get_mid_data(self):
        mid_url = "http://api.bilibili.com/x/web-interface/card?mid={}".format(self.mid)
        mid_data = requests.get(mid_url).text
        mid_data = json.loads(mid_data)
        return mid_data

    def get_video_aid_list(self):
        _url = "http://space.bilibili.com/ajax/member/getSubmitVideos?mid={}&pagesize={}&page={}".format(
            self.mid, self.pagesize, self.page)
        video_data = requests.get(_url).text
        video_data = json.loads(video_data)

        video_list = video_data["data"]["vlist"]
        video_aid_list = [video_one["aid"] for video_one in video_list]
        return video_aid_list

    @staticmethod
    def get_video_cid_list(video_aid_list):
        video_info_list, video_cid_list = [], []
        for aid in video_aid_list:
            one_url = "http://api.bilibili.com/archive_stat/stat?aid={}&type=jsonp".format(aid)
            data = requests.get(one_url).text
            one_data = json.loads(data)
            video_info_list.append(one_data)

            cid_url = "https://api.bilibili.com/x/player/pagelist?aid={}&jsonp=jsonp".format(aid)
            data = requests.get(cid_url).text
            cid_data = json.loads(data)
            video_cid_list.append(cid_data)
            pass
        return video_cid_list

    @staticmethod
    def get_video_danmaku_list(video_cid_list):
        video_danmaku_list = []
        for cid_data in video_cid_list:
            danmaku = []
            cid_data = cid_data["data"]
            danmaku_dict = {}
            for cid_one in cid_data:
                cid = cid_one["cid"]
                danmaku_url = "https://comment.bilibili.com/{}.xml".format(cid)
                xml_data = requests.get(danmaku_url).content.decode('utf-8')
                DOM = minidom.parseString(xml_data)
                collection = DOM.documentElement

                danmaku_dict["chatserver"] = collection.getElementsByTagName("chatserver")[0].childNodes[0].data
                danmaku_dict["chatid"] = collection.getElementsByTagName("chatid")[0].childNodes[0].data
                danmaku_dict["mission"] = collection.getElementsByTagName("mission")[0].childNodes[0].data
                danmaku_dict["maxlimit"] = collection.getElementsByTagName("maxlimit")[0].childNodes[0].data
                danmaku_dict["state"] = collection.getElementsByTagName("state")[0].childNodes[0].data
                danmaku_dict["real_name"] = collection.getElementsByTagName("real_name")[0].childNodes[0].data
                danmaku_dict["source"] = collection.getElementsByTagName("source")[0].childNodes[0].data
                danmaku_dict["d"] = []
                d_list = collection.getElementsByTagName("d")
                for d in d_list:
                    danmaku_dict["d"].append(d.childNodes[0].data)
                    pass

                danmaku.append(danmaku_dict)
                pass
            video_danmaku_list.append(danmaku)
        return video_danmaku_list

    def main(self, save=True):
        Tools.print("begin get_mid_data")
        mid_data = self.get_mid_data()
        Tools.print("begin get_video_aid_list")
        video_aid_list = self.get_video_aid_list()
        Tools.print("begin get_video_cid_list")
        video_cid_list = self.get_video_cid_list(video_aid_list)
        Tools.print("begin get_video_danmaku_list")
        video_danmaku_list = self.get_video_danmaku_list(video_cid_list)
        if save:
            Tools.print("begin save to {}".format(self.save_path))
            Tools.write_to_pkl(Tools.new_dir(self.save_path), video_danmaku_list)
        return video_danmaku_list

    pass


class MyWordCloud(object):

    def __init__(self, data_file="", stop_words_file="./source/chineseStopWords.txt"):
        self.data_file = data_file
        self.stop_words_file = stop_words_file

        self.data = Tools.read_from_pkl(self.data_file)
        self.data = [one[0]["d"] for one in self.data]
        self.data = [i for one in self.data for i in one]

        self.stop_words = list(set(self.get_stop_words() + list(STOPWORDS)))
        pass

    def get_stop_words(self):
        with open(self.stop_words_file, "r") as f:
            result = f.readlines()
            result = [one.strip() for one in result]
        return result

    @staticmethod
    def is_chinese(word):
        for ch in word:
            if not ('\u4e00' <= ch <= '\u9fff'):
                return False
        return True

    def get_word(self):
        # 分词
        words = []
        for sentence in self.data:
            word = list(jieba.cut(sentence))
            words.extend(word)
            pass

        # 统计
        count = collections.Counter(words)

        # 去停用词
        result = {}
        for key in count.keys():
            # if key not in self.stop_words:
            #     if self.is_chinese(key):
            #         result[key] = count[key]
            if self.is_chinese(key):
                result[key] = count[key]
            pass

        result = sorted(result.items(), key=lambda d: d[1], reverse=True)
        result = [one[0] for one in result]
        return result

    def generate_cloud(self, words, result_file, temp, font_path="./source/微软vista雅黑.ttf"):
        word_str = " ".join(words)
        if temp:
            alice_mask = np.array(Image.open(temp))
            wc = WordCloud(font_path=font_path, background_color="white",
                           max_words=2000, mask=alice_mask, stopwords=self.stop_words)
        else:
            wc = WordCloud(font_path=font_path, background_color='white', width=500,
                           height=350, max_font_size=50, min_font_size=10, mode='RGBA', stopwords=self.stop_words)
            pass
        wc.generate(word_str)
        wc.to_file(result_file)
        pass

    def main(self, result_file="./result/wordcloud.png",
             temp="./source/temp.png", font_path="./source/微软vista雅黑.ttf"):
        Tools.print("begin get words")
        words = self.get_word()
        Tools.print("begin generate cloud")
        self.generate_cloud(words, result_file=result_file, temp=temp, font_path=font_path)
        pass

    pass


if __name__ == '__main__':
    data_bilibili = DataBilibili(mid="392836434", page=1, pagesize=10)
    _video_danmaku_list = data_bilibili.main(save=True)
    word_cloud = MyWordCloud(data_file=data_bilibili.save_path)
    word_cloud.main(result_file=Tools.new_dir("./result/wordcloud.png"), temp="./source/temp.png")
    Tools.print("Over")
