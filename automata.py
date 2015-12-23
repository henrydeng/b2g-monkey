#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
The automata (finite state machine) referenced by the monkey.
"""

import os, sys, json, posixpath, time, codecs, random
from os.path import relpath
import networkx
from dom_analyzer import DomAnalyzer
from hashUtil import Hash

class Automata:
    def __init__(self):
        self._states = []
        self._edges = []
        self._initial_state = None
        self._current_state = None
        self._automata_fname = 'automata.json'
        # make a hashmap with 19 blocks for states
        self._hash = Hash(19, self)
        # make a graph for counting paths
        self._graph = networkx.DiGraph()

    def get_current_state(self):
        return self._current_state

    def get_initial_state(self):
        return self._initial_state

    def get_states(self):
        return self._states

    def get_edges(self):
        return self._edges

    def set_initial_state(self, state):
        if not state.get_id():
            state.set_id( str(len( self._states )) )  
        is_new, state_id  = self._hash.put(state)
        if is_new:
            self._states.append(state)
            self._initial_state = state
            self._current_state = state
            self._graph.add_node(state)
        return is_new, state_id

    def add_state_edge(self, state, edge):
        if not state.get_id():
            state.set_id( str(len( self._states )) )            
        is_new, state_id = self._hash.put(state)
        #change state if not new
        if is_new:
            self._states.append(state)
            self._graph.add_node(state)
        else:
            state = self.get_state_by_id(state_id)
        #add edge
        edge.set_state_to(state.get_id())
        edge.set_id( str(len( self._edges )) )
        self.add_edge(edge)
        return state, is_new

    def change_state(self, state):
        self._current_state = state

    def add_edge(self, edge):
        self._edges.append(edge)
        self._graph.add_edge( self.get_state_by_id(edge.get_state_from()),
                              self.get_state_by_id(edge.get_state_to()) )

    def get_state_by_id(self, sid):
        for s in self._states:
            if s.get_id() == sid:
                return s
        return None

    def get_edge_by_from_to(self, state_from, state_to ):
        for edge in self._edges:
            if edge.get_state_from() == state_from and edge.get_state_to() == state_to:
                return edge
        return None

    def get_shortest_path(self, target):
        shortest_paths = list( networkx.shortest_simple_paths(G, self._initial_state, target) )
        shortest_path = shortest_paths[0]
        edges = []
        for i in xrange(len(shortest_path)-1):
            edges.append( self.get_edge_by_from_to( shortest_path[i].get_id(),
                                                    shortest_path[i+1].get_id() ) )
        return edges

    def get_all_simple_states_and_traces(self):
        traces=[]
        for end_state in self._states:
            if end_state.get_clickables():
                # has clickable => not end
                continue
            for state_trace in networkx.all_simple_paths(self._graph,
                            source=self._initial_state, target=end_state ):
                edge_trace = []
                for i in xrange(len(state_trace)-1):
                    edge_trace.append( self.get_edge_by_from_to( state_trace[i].get_id(),
                                                                 state_trace[i+1].get_id() ) )
                traces.append( (state_trace, edge_trace) )
        return traces

    def save_traces(self, configuration):
        traces = self.get_all_simple_states_and_traces()
        traces_data = {
            'traces': []
        }
        for state_trace, edge_trace in traces:
            trace_data = {
                'states':[],
                'edges':[],
            }
            for s in state_trace:
                trace_data['states'].append(state.get_state_json(configuration))
                trace_data['states'].append(state_data)
            for edge in edge_trace:                
                trace_data['edges'].append(edge.get_edge_json())
            traces_data['traces'].append(trace_data)

        with codecs.open(os.path.join(configuration.get_abs_path('root'), configuration.get_traces_fname()), 'w', encoding='utf-8' ) as f:
            json.dump(traces_data, f, indent=2, sort_keys=True, ensure_ascii=False)

    def save_automata(self, configuration, automata_fname=None):
        automata_fname = configuration.get_automata_fname() if not automata_fname else automata_fname
        data = {
            'state': [],
            'edge': [], 
            # the prefix used in ids given by our monkey
            'id_prefix': DomAnalyzer.serial_prefix
        }
        for state in self._states:
            data['state'].append(state.get_state_json(configuration))
        for edge in self._edges:
            data['edge'].append(edge.get_edge_json())

        with codecs.open(os.path.join(configuration.get_abs_path('root'), configuration.get_automata_fname()), 'w', encoding='utf-8' ) as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)


class State:
    def __init__(self, dom_list, url):
        self._id = None
        #list of Statedom( dom, iframe )
        self._dom_list = dom_list
        self._prev_states = []
        self._clickables = {}
        self._url = url
        self._depth = 0
        #=============================================================================================
        #Diff: inputs information save in state, indiviual to clickables, add normalize_dom
        self._inputs = {} #dict [iframes] of inputs
        self._selects = {}
        self._candidate_clickables = {}
        self._radios = {}
        self._checkboxes = {}
        #=============================================================================================

    def add_clickable(self, clickable, iframe_key):
        # check if the clickable is duplicated
        if iframe_key in self._clickables.keys():
            if clickable.get_id():
                for c in self._clickables[iframe_key]:
                    if c.get_id() == clickable.get_id():
                        return False
            else:
                for c in self._clickables[iframe_key]:
                    if c.get_xpath() == clickable.get_xpath():
                        return False
            self._clickables[iframe_key].append( clickable )
        else:
            self._clickables[iframe_key] = [clickable]
        return True

    def get_clickable_by_id(self, c_id):
        for iframe_key in self._clickables.keys():
            for c in self._clickables[iframe_key]:
                if c.get_id() == c_id:
                    return c
        return None

    def get_clickables(self):
        return self._clickables

    def get_all_clickables_json(self):
        note = []
        for iframe_key in self._clickables.keys():
            iframe_data = {
                'clickables': []
            }
            iframe_data['iframe_list'] = iframe_key.split(';') if iframe_key else None
            for clickable in self._clickables[iframe_key]:
                clickable_data = {
                    'id': clickable.get_id(),
                    'name': clickable.get_name(),
                    'xpath': clickable.get_xpath(),
                    'tag': clickable.get_tag()
                }
                iframe_data['clickables'].append(clickable_data)
            note.append(iframe_data)
        return note

    def set_id(self, state_id):
        self._id = state_id

    def get_id(self):
        return self._id

    def add_prev_state(self, state):
        for s in self._prev_states:
            if s.get_dom() == state.get_dom():
                return False
        self._prev_states.append(state)
        return True

    def get_prev_states(self):
        return self._prev_states

    def __str__(self):
        return 'state id: %s, prev states: %s, clickables: %s' % \
               (self._id, self._prev_states, len(self._clickables))

    #=============================================================================================
    #Diff: inputs information save in state, indiviual to clickables
    def set_inputs(self, inputs):
        self._inputs = inputs

    def get_inputs(self, iframe_list):
        return self._inputs[iframe_list]

    def get_all_inputs(self):
        return self._inputs 

    def get_all_inputs_json(self):
        note = []
        for iframe_key in self._inputs.keys():
            iframe_data = {
                'inputs': []
            }
            iframe_data['iframe_list'] = iframe_key.split(';') if iframe_key else None
            for my_input in self._inputs[iframe_key]:
                input_data = {
                    'id': my_input.get_id(),
                    'name': my_input.get_name(),
                    'xpath': my_input.get_xpath(),
                    'type': my_input.get_type(),
                }
                iframe_data['inputs'].append(input_data) 
            note.append(iframe_data)
        return note

    def set_selects(self, selects):
        self._selects = selects

    def get_selects(self, iframe_list):
        return self._selects[iframe_list]

    def get_all_selects(self):
        return self._selects

    def get_all_selects_json(self):
        note = []
        for iframe_key in self._selects.keys():
            iframe_data = {
                'selects': []
            }
            iframe_data['iframe_list'] = iframe_key.split(';') if iframe_key else None
            for my_select in self._selects[iframe_key]:
                select_data = {
                    'id': my_select.get_id(),
                    'name': my_select.get_name(),
                    'xpath': my_select.get_xpath(),
                    'value': my_select.get_value()
                }
                iframe_data['selects'].append(select_data) 
            note.append(iframe_data)
        return note

    def set_inputs(self, inputs):
        self._inputs = inputs

    def set_checkboxes(self, checkboxes):
        self._checkboxes = checkboxes

    def get_checkboxes(self, iframe_list):
        return self._checkboxes[iframe_list]

    def get_all_checkboxes(self):
        return self._checkboxes

    def get_all_checkboxes_json(self):
        note = []
        for iframe_key in self._checkboxes.keys():
            iframe_data = {
                'checkboxes': []
            }
            iframe_data['iframe_list'] = iframe_key.split(';') if iframe_key else None
            for my_checkbox_field in self._checkboxes[iframe_key]:
                checkbox_field_data = {
                    'checkbox_name': my_checkbox_field.get_checkbox_name(),
                    'checkbox_list': []
                }
                for my_checkbox in my_checkbox_field.get_checkbox_list():
                    checkbox_data = {
                        'id': my_checkbox.get_id(),
                        'name': my_checkbox.get_name(),
                        'xpath': my_checkbox.get_xpath(),
                        'value': my_checkbox.get_value()
                    }
                    checkbox_field_data['checkbox_list'].append(checkbox_data)
                iframe_data['checkboxes'].append(checkbox_field_data)  
            note.append(iframe_data)
        return note

    def set_checkboxes(self, checkboxes):
        self._checkboxes = checkboxes

    def set_radios(self, radios):
        self._radios = radios

    def get_radios(self, iframe_list):
        return self._radios[iframe_list]

    def get_all_radios(self):
        return self._radios

    def get_all_radios_json(self):
        note = []
        for iframe_key in self._radios.keys():
            iframe_data = {
                'radios': []
            }
            iframe_data['iframe_list'] = iframe_key.split(';') if iframe_key else None
            for my_radio_field in self._radios[iframe_key]:
                radio_field_data = {
                    'radio_name': my_radio_field.get_radio_name(),
                    'radio_list': []
                }
                for my_radio in my_radio_field.get_radio_list():
                    radio_data = {
                        'id': my_radio.get_id(),
                        'name': my_radio.get_name(),
                        'xpath': my_radio.get_xpath(),
                        'value': my_radio.get_value()
                    }
                    radio_field_data['radio_list'].append(radio_data)
                iframe_data['radios'].append(radio_field_data) 
            note.append(iframe_data)
        return note

    def set_candidate_clickables(self, candidate_clickables):
        self._candidate_clickables = candidate_clickables

    def get_all_candidate_clickables(self):
        return self._candidate_clickables

    def get_all_candidate_clickables_json(self):
        note = []
        for iframe_key in self._candidate_clickables.keys():
            iframe_data = {
                'candidate_clickables': []
            }
            iframe_data['iframe_list'] = iframe_key.split(';') if iframe_key else None
            for c, xpath in self._candidate_clickables[iframe_key]:
                candidate_clickable = {}
                candidate_clickable['id'] = c['id'] if c.has_attr('id') else None
                candidate_clickable['name'] = c['name'] if c.has_attr('name') else None
                candidate_clickable['xpath'] = xpath
                candidate_clickable['tag'] = c.name
                iframe_data['candidate_clickables'].append(candidate_clickable)
            note.append(iframe_data)
        return note

    def get_dom_list(self):
        return self._dom_list

    def get_all_dom(self):
        dom = [ stateDom.get_dom() for stateDom in self._dom_list ]
        dom = "\n".join(dom)
        return dom

    def get_all_normalize_dom(self):
        dom = [ stateDom.get_normalize_dom() for stateDom in self._dom_list ]
        dom = "\n".join(dom)
        return dom

    def set_url(self, url):
        self._url = url

    def get_url(self):
        return self._url

    def set_depth(self, depth):
        self._depth = depth

    def get_depth(self):
        return self._depth

    def get_state_json(self, configuration):
        state_data = {
            'id': self._id,
            'url': self._url,
            'depth': self._depth,
            # output unix style path for website: first unpack dirs in get_path('dom'),
            # and then posixpath.join them with the filename
            'dom_path': posixpath.join(
                            posixpath.join(
                                *(relpath(
                                    configuration.get_path('dom'),
                                    configuration.get_path('root')
                                    ).split(os.sep) ) ), self._id + '.txt' ),
            'img_path': posixpath.join(
                            posixpath.join(
                                *(relpath(
                                    configuration.get_path('state'),
                                    configuration.get_path('root')
                                    ).split(os.sep) ) ), self._id  + '.png' ),
            'clickable': self.get_all_clickables_json(),
            'inputs': self.get_all_inputs_json(),
            'selects': self.get_all_selects_json(),
            'radios': self.get_all_radios_json(),
            'checkboxes': self.get_all_checkboxes_json()
        }
        return state_data

    def get_simple_state_json(self, configuration):
        state_data = {
            'id': self._id,
            'url': self._url,
            'img_path': posixpath.join(
                            posixpath.join(
                                *(relpath(
                                    configuration.get_path('state'),
                                    configuration.get_path('root')
                                    ).split(os.sep) ) ), self._id  + '.png' ),
            'depth': self._depth
        }
        return state_data
    #============================================================================

class StateDom:
    def __init__(self, iframe_path_list, dom, url):
        self.iframe_path_list = iframe_path_list
        self.dom = dom
        self.url = url
        self.normalize_dom = DomAnalyzer.normalize(dom)

    def get_url(self):
        return self.url

    def get_iframe_path_list(self):
        return self.iframe_path_list

    def get_dom(self):
        return self.dom

    def get_normalize_dom(self):
        return self.normalize_dom

    def is_same(self, stateDom):
        return self.url == stateDom.get_url() and \
               self.iframe_path_list == stateDom.get_iframe_path_list() and \
               DomAnalyzer.is_normalize_equal(self.normalize_dom, stateDom.get_normalize_dom())

class Edge:
    def __init__(self, state_from, state_to, clickable, \
                 inputs, selects, checkboxes, radios, iframe_key, cost = 1):
        self._id = None
        self._state_from = state_from
        self._state_to = state_to
        self._clickable = clickable
        self._inputs = inputs
        self._selects = selects
        self._checkboxes = checkboxes
        self._radios = radios
        self._iframe_list = None if not iframe_key \
            else iframe_key if type(iframe_key) == type([]) else iframe_key.split(';')

    def set_id(self, edge_id):
        self._id = edge_id

    def get_id(self):
        return self._id

    def get_state_from(self):
        return self._state_from

    def set_state_from(self, state_from):
        self._state_from = state_from

    def get_state_to(self):
        return self._state_to

    def set_state_to(self, state_to):
        self._state_to = state_to

    def set_state_to(self, state):
        self._state_to = state

    def get_clickable(self):
        return self._clickable

    def get_inputs(self):
        return self._inputs

    def get_selects(self):
        return self._selects

    def get_checkboxes(self):
        return self._checkboxes

    def get_radios(self):
        return self._radios

    def get_iframe_list(self):
        return self._iframe_list

    def get_copy(self):
        copy_edge = Edge( self._state_from, self._state_to, self._clickable.get_copy(),
                        [ i.get_copy() for i in self._inputs ], [ s.get_copy() for s in self._selects ],
                        [ c.get_copy() for c in self._checkboxes ], [ r.get_copy() for r in self._radios ],
                        self._iframe_list )
        copy_edge.set_id( self._id )
        return copy_edge       

    def get_edge_json(self):
        edge_data = {
            'from': self._state_from,
            'to': self._state_to,
            'id': self._id,
            'clickable': {
                'id': self._clickable.get_id(),
                'name': self._clickable.get_name(),
                'xpath': self._clickable.get_xpath(),
                'tag': self._clickable.get_tag()
            },
            'inputs': [],
            'selects': [],
            'checkboxes': [],
            'radios': [],
            'iframe_list': self._iframe_list
        }
        for my_input in self._inputs:
            input_data = {
                'id': my_input.get_id(),
                'name': my_input.get_name(),
                'xpath': my_input.get_xpath(),
                'type': my_input.get_type(),
                'value': my_input.get_value()
            }
            edge_data['inputs'].append(input_data)
        for select in self._selects:
            select_data = {
                'id': select.get_id(),
                'name': select.get_name(),
                'xpath': select.get_xpath(),
                'value': select.get_value(),
                'selected': select.get_selected()
            }
            edge_data['selects'].append(select_data)
        for checkbox_field in self._checkboxes:
            checkbox_field_data = {
                'checkbox_list': [],
                'checkbox_selected_list': checkbox_field.get_selected_list(),
                'checkbox_name': checkbox_field.get_checkbox_name()
            }
            for checkbox in checkbox_field.get_checkbox_list():
                checkbox_data = {
                    'id': checkbox.get_id(),
                    'name': checkbox.get_name(),
                    'xpath': checkbox.get_xpath(),
                    'value': checkbox.get_value()
                }
                checkbox_field_data['checkbox_list'].append(checkbox_data)
            edge_data['checkboxes'].append(checkbox_field_data)
        for radio_field in self._radios:
            radio_field_data = {
                'radio_list': [],
                'radio_selected': radio_field.get_selected(),
                'radio_name': radio_field.get_radio_name()
            }
            for radio in radio_field.get_radio_list():
                radio_data = {
                    'id': radio.get_id(),
                    'name': radio.get_name(),
                    'xpath': radio.get_xpath(),
                    'value': radio.get_value()
                }
                radio_field_data['radio_list'].append(radio_data)
            edge_data['radios'].append(radio_field_data)
        return edge_data