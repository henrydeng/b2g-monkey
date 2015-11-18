#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Module docstring
"""

from abc import ABCMeta, abstractmethod
from bs4 import BeautifulSoup


class AbstractNormalizer():
    __metaclass__ = ABCMeta

    @abstractmethod
    def normalize(self, dom):
        pass


class AttributeNormalizer(AbstractNormalizer):
    def __init__(self, attr_list=None, mode='white_list'):
        self.attr_list = attr_list
        self.mode = mode

    def normalize(self, dom):
        soup = BeautifulSoup(dom, 'html.parser')
        for tag in soup.find_all():
            filtered_attrs = {}
            if self.mode == 'white_list':
                for attr in tag.attrs:
                    if self.attr_list and (attr in self.attr_list):
                        filtered_attrs[attr] = tag[attr]
            else:  # black_list
                for attr in tag.attrs:
                    if attr not in self.attr_list:
                        filtered_attrs[attr] = tag[attr]
            tag.attrs = filtered_attrs
        return str(soup).replace('\n', '')

    def __str__(self):
        return 'AttributeNormalizer: attr_list: %s, mode: %s' % (self.attr_list, self.mode)


class TagContentNormalizer(AbstractNormalizer):
    def __init__(self, tag_list=None):
        self.tag_list = tag_list

    def normalize(self, dom):
        soup = BeautifulSoup(dom, 'html.parser')
        for tag in soup.find_all():
            if self.tag_list and (tag.name in self.tag_list):
                tag.clear()
        return str(soup).replace('\n', '')

    def __str__(self):
        return 'TagContentNormalizer: tag_list: %s' % self.tag_list


class TagNormalizer(AbstractNormalizer):
    def __init__(self, tag_list=None):
        self.tag_list = tag_list

    def normalize(self, dom):
        soup = BeautifulSoup(dom, 'html.parser')
        for tag in soup.find_all():
            if self.tag_list and (tag.name in self.tag_list):
                tag.decompose()
        return str(soup).replace('\n', '')

    def __str__(self):
        return 'TagNormalizer: tag_list: %s' % self.tag_list


# remove tag with:
# 1. matched name, attr and startswith value
# 2. matched name, and tag content contains value without given attr
class TagWithAttributeNormalizer(AbstractNormalizer):
    def __init__(self, name, attr, value):
        self.name = name
        self.attr = attr
        self.value = value

    def normalize(self, dom):
        soup = BeautifulSoup(dom, 'html.parser')
        for tag in soup.find_all(self.name):
            if self.attr and self.attr in tag.attrs:
                if tag[self.attr].startswith(self.value):
                    tag.decompose()
            elif not self.attr:  # self.attr is None
                if self.value in tag.strings:
                    tag.decompose()
        return str(soup).replace('\n', '')

    def __str__(self):
        return 'TagWithAttributeNormalizer: tag: %s, attr: %s, value: %s' % self.name, self.attr, self.value
