#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
The automata (finite state machine) referenced by the monkey.
"""

from dom_analyzer import DomAnalyzer


class Automata:
    def __init__(self):
        self._states = []
        self._edges = []
        self._initial_state = None
        self._current_state = None

    def get_current_state(self):
        return self._current_state

    def get_initial_state(self):
        return self._initial_state

    def get_states(self):
        return self._states

    def get_edges(self):
        return self._edges

    def add_state(self, state):
        # check if the automata is empty
        if not self._initial_state:
            self._initial_state = state
            self._current_state = state
        else:
            # check if the dom is duplicated
            for s in self._states:
                if DomAnalyzer.is_equal(s.get_dom(), state.get_dom()):
                    return s, False
        state_id = state.get_id() if state.get_id() else str(len(self._states))
        state.set_id(state_id)
        self._states.append(state)
        return state, True

    def change_state(self, state):
        self._current_state = state

    def add_edge(self, state_from, state_to, clickable, cost=1):
        edge = (state_from, state_to, clickable, cost)
        self._edges.append(edge)

    def get_state_by_id(self, sid):
        for s in self._states:
            if s.get_id() == sid:
                return s
        return None

    def get_shortest_path(self, target):
        # Breath First Search
        explored = []
        frontier = [self._initial_state]
        unexplored = [s for s in self._states if s != self._initial_state]
        incoming_edges = {}
        current_state = None

        while (current_state != target) and frontier:
            current_state = frontier.pop(0)
            explored.append(current_state)
            for e in self._edges:  # edge = (state_from, state_to, clickable, cost)
                if e[0] == current_state and e[1] in unexplored:
                    frontier.append(e[1])
                    unexplored.remove(e[1])
                    incoming_edges[e[1]] = e
        edges = []
        if current_state == target:
            while current_state != self._initial_state:
                edges.insert(0, incoming_edges[current_state])
                current_state = incoming_edges[current_state][0]
        else:
            raise ValueError('Automata.get_shortest_path(): No path found when trying to reach state: %s' % target)

        return edges


class State:
    def __init__(self, dom):
        self._id = None
        self._dom = dom
        self._prev_states = []
        self._clickables = []
        self._forms = []

    def add_clickable(self, clickable):
        if clickable in self._clickables:
            return False
        self._clickables.append(clickable)
        return True

    def set_id(self, state_id):
        self._id = state_id

    def add_prev_state(self, state):
        for s in self._prev_states:
            if s.get_dom() == state.get_dom():
                return False
        self._prev_states.append(state)
        return True

    def get_clickables(self):
        return self._clickables

    def get_clickable_by_id(self, cid):
        for c in self._clickables:
            if c.get_id() == cid:
                return c
        return None

    def get_prev_states(self):
        return self._prev_states

    def get_id(self):
        return self._id

    def get_dom(self):
        return self._dom

    def get_forms(self):
        if not self._forms:
            for c in self._clickables:
                for f in c.get_forms():
                    is_existed = False
                    for existing_form in self._forms:
                        if f.get_xpath() == existing_form.get_xpath():
                            is_existed = True
                            break
                    if not is_existed:
                        self._forms.append(f)
        return self._forms

    def add_form(self, form):
        for f in self._forms:
            if f.get_xpath() == form.get_xpath():
                return False
        self._forms.append(form)
        return True

    def get_form_by_id(self, fid):
        for f in self._forms:
            if f.get_id() == fid:
                return f
        return None

    def __str__(self):
        return 'state id: %s, prev states: %s, clickables: %s' % \
               (self._id, self._prev_states, len(self._clickables))

