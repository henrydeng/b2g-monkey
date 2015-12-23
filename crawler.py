#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Module docstring
"""

import os, sys, json, posixpath, time, datetime, codecs, logging, random, copy
from abc import ABCMeta, abstractmethod
from automata import Automata, State, StateDom, Edge
from visualizer import Visualizer
from dom_analyzer import DomAnalyzer
from configuration import MutationMethod
from mutation import Mutation
from bs4 import BeautifulSoup
#=============================================================================================
#Diff: check url domain
from urlparse import urlparse
import itertools
#=============================================================================================

class Crawler:
    __metaclass__ = ABCMeta

    @abstractmethod
    def run(self):
        pass

#==============================================================================================================================
# Selenium Web Driver
#==============================================================================================================================
class SeleniumCrawler(Crawler):
    def __init__(self, configuration, executor, automata, databank):
        self.configuration = configuration
        self.executor = executor
        self.automata = automata
        #list of event:(state, clickable, inputs, selects, iframe_list)
        self.event_history = []
        self.databank = databank
    
    def run(self):
        self.executor.start()
        self.executor.goto_url()
        initial_state = self.get_initail_state()
        self.run_script_before_crawl(initial_state)
        self.crawl(1)
        return self.automata

    def run_mutant(self):
        self.mutation_history = []
        self.mutation_cluster = {}
        self.mutation = Mutation(self.configuration.get_mutant_trace(), self.databank)
        self.mutation_traces = self.make_mutation_traces()
        # use a int to select sample of mutation traces
        self.mutation_traces = random.sample(self.mutation_traces, min(2, len(self.mutation_traces)))
        logging.info(' total %d mutation traces ', len(self.mutation_traces))
        for n in xrange(len(self.mutation_traces)):
            logging.info(" start run number %d mutant trace", n)
            self.executor.start()
            self.executor.goto_url()    
            initial_state = self.get_initail_state()
            self.run_mutant_script(initial_state, self.mutation_traces[n])
            self.close()
        self.save_mutation_history()

    #=============================================================================================
    # DEFAULT CRAWL
    #=============================================================================================
    def crawl(self, depth, prev_state=None):
        if depth > self.configuration.get_max_depth():
            return
        current_state = self.automata.get_current_state()
        logging.info(' now depth(%s) - max_depth(%s); current state: %s', depth, self.configuration.get_max_depth(), current_state.get_id() )
        for clickables, iframe_key in DomAnalyzer.get_clickables(current_state, prev_state if prev_state else None):
            inputs = current_state.get_inputs(iframe_key)
            selects = current_state.get_selects(iframe_key)
            checkboxes = current_state.get_checkboxes(iframe_key)
            radios = current_state.get_radios(iframe_key)

            for clickable in clickables:
                new_edge = Edge(current_state.get_id(), None, clickable, inputs, selects, checkboxes, radios, iframe_key)
                self.make_value(new_edge)
                logging.info('state %s fire element in iframe(%s)',current_state.get_id(), iframe_key)
                self.click_event_by_edge(new_edge)

                dom_list, url, is_same = self.is_same_state_dom(current_state)
                if is_same:
                    continue
                if self.is_same_domain(url):
                    logging.info(' change dom to: %s', self.executor.get_url())
                    # check if this is a new state
                    temp_state = State(dom_list, url)
                    new_state, is_newly_added = self.automata.add_state(temp_state)
                    self.automata.add_edge(new_edge, new_state.get_id())
                    # save this click edge
                    current_state.add_clickable(clickable, iframe_key)
                    '''TODO: value of inputs should connect with edges '''
                    if is_newly_added:
                        logging.info('add new state %s of : %s', new_state.get_id(), url )
                        self.save_state(new_state, depth)
                        self.event_history.append( new_edge )
                        if depth < self.configuration.get_max_depth():
                            self.automata.change_state(new_state)
                            self.crawl(depth+1, current_state)
                        self.event_history.pop()
                    self.automata.change_state(current_state)
                else:
                    logging.info(' out of domain: %s', url)
                logging.info('==========< BACKTRACK START >==========')
                logging.info('==<BACKTRACK> depth %s -> backtrack to state %s',depth ,current_state.get_id() )
                self.backtrack(current_state)
                self.configuration.save_config('config.json')
                self.automata.save_automata(self.configuration)
                Visualizer.generate_html('web', os.path.join(self.configuration.get_path('root'), self.configuration.get_automata_fname()))
                logging.info('==========< BACKTRACK END   >==========')
        logging.info(' depth %s -> state %s crawl end', depth, current_state.get_id())

    #=============================================================================================
    # BACKTRACK
    #=============================================================================================
    def backtrack(self, state):
        #if url are same, guess they are just javascipt edges
        if self.executor.get_url() == state.get_url():
            #first, just refresh for javascript button
            logging.info('==<BACKTRACK> : try refresh')
            self.executor.refresh()
            dom_list, url, is_same = self.is_same_state_dom(state)
            if is_same:
                return True

        #if can't , try go back form history
        logging.info('==<BACKTRACK> : try back_history ')
        self.executor.back_history()
        dom_list, url, is_same = self.is_same_state_dom(state)
        if is_same:
            return True

        #if can't , try do last edge of state history
        if self.event_history:
            logging.info('==<BACKTRACK> : try last edge of state history')
            self.executor.forward_history()
            self.click_event_by_edge( self.event_history[-1] )
            dom_list, url, is_same = self.is_same_state_dom(state)
            if is_same:
                return True

        #if can't, try go through all edge
        logging.info('==<BACKTRACK> : start form base ur')
        self.executor.goto_url()
        for history_edge in self.event_history:
            self.click_event_by_edge( history_edge )
        dom_list, url, is_same = self.is_same_state_dom(state)
        if is_same:
            return True

        #if can't, restart and try go again
        logging,info('==<BACKTRACK> : retart driver')
        edges = self.automata.get_shortest_path(state)
        self.executor.restart_app()
        self.executor.goto_url()
        for edge in edges:
            self.click_event_by_edge(edge)
            #check again if executor really turn back. if not, sth error, stop
            state_to = self.automata.get_state_by_id( edge.get_state_to() )
            dom_list, url, is_same = self.is_same_state_dom(state_to)
            if not is_same:
                try:
                    err = State(dom_list, url)
                    with open('debug_origin_'+state_to.get_id()+'.txt', 'w') as f:
                        f.write(state_to.get_all_dom())
                    with open('debug_restart_'+state_to.get_id()+'.txt', 'w') as f:
                        f.write(err.get_all_dom())
                    with open('debug_origin_nor_'+state_to.get_id()+'.txt', 'w') as f:
                        f.write( state_to.get_all_normalize_dom() )
                    with open('debug_restart_nor_'+state_to.get_id()+'.txt', 'w') as f:
                        f.write( err.get_all_normalize_dom() )
                    logging.error('==<BACKTRACK> cannot traceback to %s \t\t__from crawler.py backtrack()', state_to.get_id() )
                except Exception as e:  
                    logging.info('==<BACKTRACK> save diff dom : %s', str(e))

        dom_list, url, is_same = self.is_same_state_dom(state)
        return is_same

#=========================================================================================
# TODO FOR MUTATION
#=========================================================================================
    def make_mutation_traces(self):
        self.mutation.make_data_set()
        self.mutation.set_method(self.configuration.get_mutation_method())
        self.mutation.make_mutation_traces()
        return self.mutation.get_mutation_traces()

    def run_mutant_script(self, prev_state, mutation_trace):
        depth = 0
        edge_trace = []
        state_trace = [prev_state]
        cluster_value = ''
        for edge in self.configuration.get_mutant_trace():
            new_edge = edge.get_copy()
            new_edge.set_state_from( prev_state.get_id() )
            self.make_mutant_value(new_edge, mutation_trace[depth])
            self.click_event_by_edge(new_edge)
            self.event_history.append(new_edge)

            dom_list, url, is_same = self.is_same_state_dom(prev_state)
            if not is_same: 
                logging.info(' change dom to: %s', url)
            # check if this is a new state
            temp_state = State(dom_list, url)
            new_state, is_newly_added = self.automata.add_state(temp_state)
            self.automata.add_edge(new_edge, new_state.get_id())
            # save this click edge
            prev_state.add_clickable(edge.get_clickable(), new_edge.get_iframe_list())
            if is_newly_added:
                logging.info(' add new state %s of: %s', new_state.get_id(), url)
                self.save_state(new_state, depth+1)
                self.automata.change_state(new_state)
            # save the state, edge
            state_trace.append( new_state )
            edge_trace.append( new_edge )
            cluster_value += prev_state.get_id() + new_state.get_id()
            # prepare for next edge
            prev_state = new_state
            depth += 1

        self.mutation_history.append( (edge_trace, state_trace, cluster_value ) )

    def cluster_mutation_trace(self):
        # first cluster default trace as 0
        cluster_value = ''
        for edge in self.configuration.get_mutant_trace():
            cluster_value += edge.get_state_from() + edge.get_state_to()
        self.mutation_cluster[cluster_value] = []
        #then cluster other mutation traces
        for edge_trace, state_trace, cluster_value in self.mutation_history:
            if cluster_value in self.mutation_cluster:
                self.mutation_cluster[cluster_value].append( (edge_trace, state_trace, cluster_value) )
            else:
                self.mutation_cluster[cluster_value] = [ (edge_trace, state_trace, cluster_value) ]

    def save_mutation_history(self):
        self.cluster_mutation_trace()
        traces_data = {
            'traces': []
        }
        for cluster_key, mutation_traces in self.mutation_cluster.items():
            for edge_trace, state_trace, cluster_value in mutation_traces:
                trace_data = {
                    'edges':[],
                    'states':[],
                    'cluster_value': cluster_key
                }
                for edge in edge_trace:                
                    trace_data['edges'].append(edge.get_edge_json())
                traces_data['traces'].append(trace_data)
                for state in state_trace:
                    trace_data['states'].append(state.get_simple_state_json(self.configuration))

        with codecs.open(os.path.join(self.configuration.get_abs_path('root'), 'mutation_traces.json'), 'w', encoding='utf-8' ) as f:
            json.dump(traces_data, f, indent=2, sort_keys=True, ensure_ascii=False)

#=========================================================================================
# BASIC CRAWL
#=========================================================================================
    def get_initail_state(self):
        logging.info(' get initial state')
        dom_list, url = self.get_dom_list()
        initial_state = State( dom_list, url )
        is_new, state = self.automata.set_initial_state(initial_state)
        if is_new:
            self.save_state(initial_state, 0)
        time.sleep(self.configuration.get_sleep_time())
        return state

    def run_script_before_crawl(self, prev_state):
        for edge in self.configuration.get_before_script():
            self.click_event_by_edge(edge)
            self.event_history.append(edge)

            dom_list, url, is_same = self.is_same_state_dom(prev_state)
            if is_same:
                continue
            logging.info(' change dom to: ', self.executor.get_url())
            # check if this is a new state
            temp_state = State(dom_list, url)
            new_state, is_newly_added = self.automata.add_state(temp_state)
            self.automata.add_edge(edge, new_state.get_id())
            # save this click edge
            prev_state.add_clickable(edge.get_clickable(), edge.get_iframe_list())
            if is_newly_added:
                logging.info(' add new state %s of: %s', new_state.get_id(), url)
                self.save_state(new_state, 0)
                self.automata.change_state(new_state)
            prev_state = new_state

#=========================================================================================
# EVENT
#=========================================================================================
    def click_event_by_edge(self, edge):
        self.executor.switch_iframe_and_get_source( edge.get_iframe_list() )
        self.executor.fill_selects( edge.get_selects() )
        self.executor.fill_inputs_text( edge.get_inputs() )
        self.executor.fill_checkboxes( edge.get_checkboxes() )
        self.executor.fill_radios( edge.get_radios() )
        self.executor.fire_event( edge.get_clickable() )
        time.sleep(self.configuration.get_sleep_time())

    def close(self):
        self.executor.close()

    def make_value(self, edge):
        for input_field in edge.get_inputs():
            data_set = input_field.get_data_set(self.databank)
            #check data set
            value = random.choice(data_set) if data_set \
                else ''.join( [random.choice(string.lowercase) for i in xrange(8)] )
            input_field.set_value(value)

        for select_field in edge.get_selects():
            data_set = select_field.get_data_set(self.databank)
            #check data set
            selected = random.choice(data_set) if data_set \
                else min(max(3, option_num/2), option_num)
            select_field.set_selected(selected)

        for checkbox_field in edge.get_checkboxes():
            data_set = checkbox_field.get_data_set(self.databank)
            #check data set
            selected_list = random.choice(data_set).split('/') if data_set \
                else random.sample( xrange(len(checkbox_field.get_checkbox_list())), random.randint(0, len(checkbox_field.get_checkbox_list())) )
            checkbox_field.set_selected_list(selected_list)

        for radio_field in edge.get_radios():
            data_set = radio_field.get_data_set(self.databank)
            #check data set
            selected = random.choice(data_set) if data_set \
                else andom.randint(0, len(radio_field.get_radio_list()))
            radio_field.set_selected(selected)

    def make_mutant_value(self, edge, edge_value):
        for input_field in edge.get_inputs():
            input_field.set_value(edge_value.get_inputs()[input_field.get_id()])

        for select_field in edge.get_selects():
            select_field.set_selected(edge_value.get_selects()[select_field.get_id()])

        for checkbox_field in edge.get_checkboxes():
            checkbox_field.set_selected_list(edge_value.get_checkboxes()[checkbox_field.get_checkbox_name()])

        for radio_field in edge.get_radios():
            radio_field.set_selected(edge_value.get_radios()[radio_field.get_radio_name()])

#=========================================================================================
# DECISION
#=========================================================================================
    def is_same_domain(self, url):
        base_url = urlparse( self.configuration.get_url() )
        new_url = urlparse( url )
        if base_url.netloc == new_url.netloc:
            return True
        else:
            for d in self.configuration.get_domains():
                d_url = urlparse(d)
                if d_url.netloc == new_url.netloc:
                    return True
            return False

    def is_same_state_dom(self, cs):
        dom_list, url = self.get_dom_list()
        cs_dom_list = cs.get_dom_list()
        if url != cs.get_url():
            return dom_list, url, False
        elif len( cs_dom_list ) != len( dom_list ):
            return dom_list, url, False
        else:
            for dom, cs_dom in itertools.izip(dom_list, cs_dom_list):
                if not dom.is_same(cs_dom):
                    return dom_list, url, False                    
        return dom_list, url, True

#=========================================================================================
# STATE
#=========================================================================================
    def save_dom(self, state):
        try:
            with codecs.open(os.path.join(self.configuration.get_abs_path('dom'), state.get_id() + '.txt'), 'w' ) as f:
                f.write(state.get_all_dom())
            with codecs.open(os.path.join(self.configuration.get_abs_path('dom'), state.get_id() + '_nor.txt'), 'w' ) as f:
                f.write(state.get_all_normalize_dom())
            with codecs.open(os.path.join(self.configuration.get_abs_path('dom'), state.get_id() + '_inputs.txt'), 'w', encoding='utf-8' ) as f:
                json.dump(state.get_all_inputs_json(), f, indent=2, sort_keys=True, ensure_ascii=False)
            with codecs.open(os.path.join(self.configuration.get_abs_path('dom'), state.get_id() + '_selects.txt'), 'w', encoding='utf-8' ) as f:
                json.dump(state.get_all_selects_json(), f, indent=2, sort_keys=True, ensure_ascii=False)
            with codecs.open(os.path.join(self.configuration.get_abs_path('dom'), state.get_id() + '_clicks.txt'), 'w', encoding='utf-8') as f:
                json.dump(state.get_all_candidate_clickables_json(), f, indent=2, sort_keys=True, ensure_ascii=False)
        except Exception as e:  
            logging.error(' save dom : %s \t\t__from crawler.py save_dom()', str(e))

    #Diff: save state's information(inputs, selects, screenshot, [normalize]dom/iframe)
    def save_state(self, state, depth):
        candidate_clickables = {}       
        inputs = {}
        selects = {}
        checkboxes = {}
        radios = {}
        for stateDom in state.get_dom_list():
            iframe_path_list = stateDom.get_iframe_path_list()
            dom = stateDom.get_dom()
            iframe_key = ';'.join(iframe_path_list) if iframe_path_list else None
            candidate_clickables[iframe_key] = DomAnalyzer.get_candidate_clickables_soup(dom)
            inputs[iframe_key] = DomAnalyzer.get_inputs(dom)
            selects[iframe_key] = DomAnalyzer.get_selects(dom)
            checkboxes[iframe_key] = DomAnalyzer.get_checkboxes(dom)
            radios[iframe_key] = DomAnalyzer.get_radios(dom)
        state.set_candidate_clickables(candidate_clickables)
        state.set_inputs(inputs)
        state.set_selects(selects)
        state.set_checkboxes(checkboxes)
        state.set_radios(radios)
        state.set_depth(depth)

        # save this state's screenshot and dom
        path = os.path.join(self.configuration.get_abs_path('state'), state.get_id() + '.png')
        self.executor.get_screenshot(path)
        self.save_dom(state)

    def get_dom_list(self):
        #save dom of iframe in list of StateDom [iframe_path_list, dom, url/src, normalize dom]
        dom_list = []
        new_dom = self.executor.switch_iframe_and_get_source()
        url = self.executor.get_url()
        soup = BeautifulSoup(new_dom, 'html.parser')
        for frame in self.configuration.get_frame_tags():
            for iframe_tag in soup.find_all(frame):
                iframe_xpath = DomAnalyzer._get_xpath(iframe_tag)
                iframe_src = iframe_tag['src'] if iframe_tag.has_attr('src') else None
                try: #not knowing what error in iframe_tag.clear(): no src
                    if self.configuration.is_dom_inside_iframe():
                        self.get_dom_of_iframe(dom_list, [iframe_xpath], iframe_src)
                    iframe_tag.clear()
                except Exception as e:
                    logging.error(' get_dom_of_iframe: %s \t\t__from crawler.py get_dom_list() ', str(e))
        dom_list.append( StateDom(None, str(soup), url) )
        return dom_list, url

    def get_dom_of_iframe(self, dom_list, iframe_xpath_list, src):
        dom = self.executor.switch_iframe_and_get_source(iframe_xpath_list)
        soup = BeautifulSoup(dom, 'html.parser')
        for frame in self.configuration.get_frame_tags():
            for iframe_tag in soup.find_all(frame):
                iframe_xpath = DomAnalyzer._get_xpath(iframe_tag)
                iframe_xpath_list.append(iframe_xpath)
                iframe_src = iframe_tag['src'] if iframe_tag.has_attr('src') else None
                try:
                    self.get_dom_of_iframe(dom_list, iframe_xpath_list, iframe_src)      
                    iframe_tag.clear()
                except Exception as e:
                    logging.error(' get_dom_of_iframe: %s \t\t__from crawler.py get_dom_list() ', str(e))
        dom_list.append( StateDom(iframe_xpath_list, str(soup), src) )
