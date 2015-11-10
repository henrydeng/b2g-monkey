#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Module docstring
"""

import os, datetime, json
from abc import ABCMeta


class Configuration:
    __metaclass__ = ABCMeta

    def __init__(self):
        self._invariants = []
        self._max_depth = 3
        self._max_states = 10
        self._max_time = 2000
        self._sleep_time = 2

    def set_max_depth(self, depth):
        self._max_depth = depth

    def get_max_depth(self):
        return self._max_depth

    def set_max_states(self, state_num):
        self._max_states = state_num

    def get_max_states(self):
        return self._max_states

    def set_max_time(self, time_in_second):
        self._max_time = time_in_second

    def get_max_time(self):
        return self._max_time

    def set_sleep_time(self, time_in_second):
        self._sleep_time = time_in_second

    def get_sleep_time(self):
        return self._sleep_time


class B2gConfiguration(Configuration):
    def __init__(self, app_name, app_id):
        super(B2gConfiguration, self).__init__()
        self._app_name = app_name
        self._app_id = app_id
        self._automata_fname = 'automata.json'
        self._root_path = os.path.join('trace', datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        self._file_path = {
            'root': self._root_path,
            'dom': os.path.join(self._root_path, 'dom'),
            'state': os.path.join(self._root_path, 'screenshot', 'state'),
            'clickable': os.path.join(self._root_path, 'screenshot', 'clickable'),
        }
        for key, value in self._file_path.iteritems():
            abs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), value)
            if not os.path.exists(abs_path):
                os.makedirs(abs_path)

    def set_app_name(self, app_name):
        self._app_name = app_name

    def get_app_name(self):
        return self._app_name

    def set_app_id(self, app_id):
        self._app_id = app_id

    def get_app_id(self):
        return self._app_id

    def get_automata_fname(self):
        return self._automata_fname

    def get_abs_path(self, my_type):
        abs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self._file_path[my_type])
        return abs_path

    def get_path(self, my_type):
        return self._file_path[my_type]


#==============================================================================================================================
# Selenium Web Driver
#==============================================================================================================================
class SeleniumConfiguration(Configuration):
    def __init__(self, browserID, url):
        super(SeleniumConfiguration, self).__init__()
        self._browserID = browserID
        self._url = url
        self._automata_fname = 'automata.json'
        self._root_path = os.path.join('trace', datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        self._file_path = {
            'root': self._root_path,
            'dom': os.path.join(self._root_path, 'dom'),
            'state': os.path.join(self._root_path, 'screenshot', 'state'),
            'clickable': os.path.join(self._root_path, 'screenshot', 'clickable'),
        }
        for key, value in self._file_path.iteritems():
            abs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), value)
            if not os.path.exists(abs_path):
                os.makedirs(abs_path)

        self._domains = []

    def get_automata_fname(self):
        return self._automata_fname

    def get_abs_path(self, my_type):
        abs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self._file_path[my_type])
        return abs_path

    def get_path(self, my_type):
        return self._file_path[my_type]

    #=============================================================================================
    #Diff: browser use url & browserID not app
    def set_browserID(self, app_name):
        self._browserID = browserID

    def get_browserID(self):
        return self._browserID

    def set_url(self, app_id):
        self._url = _url

    def get_url(self):
        return self._url

    def set_domains(self, domains):
        self._domains = domains

    def get_domains(self):
        return self._domains

    #=============================================================================================
#==============================================================================================================================