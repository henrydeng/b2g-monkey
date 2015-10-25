#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Module docstring
"""

import os, json, posixpath, time
from os.path import relpath
from configuration import B2gConfiguration
from automata import Automata, State
from clickable import Clickable, FormField, InputField
from executor import B2gExecutor
from crawler import B2gCrawler
from visualizer import Visualizer
from dom_analyzer import DomAnalyzer
from test_generator import TestGenerator



def main():
    config = B2gConfiguration('Contacts', 'contacts')
    config.set_max_depth(3)
    #config = load_config(os.path.join('trace/20151024005306/config.json'))
    #automata = load_automata(os.path.join('trace/20151024005306/automata.json'))
    executor = B2gExecutor(config.get_app_name(), config.get_app_id())
    #tg = TestGenerator(automata, config, executor)
    #edges = tg.path_to_state(automata.get_state_by_id('5'))
    '''
    edges = []
    edges.append(
        (automata.get_initial_state(), automata.get_state_by_id('1'), automata.get_initial_state().get_clickable_by_id('add-contact-button'), 1)
    )
    edges.append(
        (automata.get_state_by_id('1'), automata.get_state_by_id('4'), automata.get_state_by_id('1').get_clickable_by_id('add-new-address'), 1)
    )
    edges.append(
        (automata.get_state_by_id('4'), automata.get_state_by_id('5'), automata.get_state_by_id('4').get_clickable_by_id('b2g-monkey-45'), 1)
    )

    executor.restart_app()
    for (state_from, state_to, clickable, cost) in edges:
        time.sleep(config.get_sleep_time())
        executor.empty_form(clickable)
        executor.fill_form(clickable)
        raw_input()
        executor.fire_event(clickable)
    '''
    crawler = B2gCrawler(config, executor)
    automata = crawler.run()
    save_automata(automata, config)
    Visualizer.generate_html('web', os.path.join(config.get_path('root'), config.get_automata_fname()))
    save_config(config, 'config.json')


def save_automata(automata, configuration):
        data = {
            'state': [],
            'edge': [],
            'id_prefix': DomAnalyzer.serial_prefix  # the prefix used in ids given by our monkey
        }
        for state in automata.get_states():
            state_data = {
                'id': state.get_id(),
                # output unix style path for website: first unpack dirs in get_path('dom'),
                # and then posixpath.join them with the filename
                'dom_path': posixpath.join(
                    posixpath.join(
                        *(relpath(
                            configuration.get_path('dom'),
                            configuration.get_path('root')
                            ).split(os.sep))
                    ),
                    state.get_id() + '.txt'
                ),
                'img_path': posixpath.join(
                    posixpath.join(
                        *(relpath(
                            configuration.get_path('state'),
                            configuration.get_path('root')
                            ).split(os.sep))
                    ),
                    state.get_id() + '.png'
                ),
                'clickable': []
            }
            for clickable in state.get_clickables():
                clickable_data = {
                    'id': clickable.get_id(),
                    'xpath': clickable.get_xpath(),
                    'tag': clickable.get_tag(),
                    'img_path': posixpath.join(
                        posixpath.join(
                            *(relpath(
                                configuration.get_path('clickable'),
                                configuration.get_path('root')
                                ).split(os.sep))
                        ),
                        state.get_id() + '-' + clickable.get_id() + '.png'
                    ),
                    'form': []
                }
                for form in clickable.get_forms():
                    form_data = {
                        'id': form.get_id(),
                        'xpath': form.get_xpath(),
                        'input': []
                    }
                    for my_input in form.get_inputs():
                        input_data = {
                            'id': my_input.get_id(),
                            'xpath': my_input.get_xpath(),
                            'type': my_input.get_type(),
                            'value': my_input.get_value()
                        }
                        form_data['input'].append(input_data)
                    clickable_data['form'].append(form_data)
                state_data['clickable'].append(clickable_data)
            data['state'].append(state_data)
        for (state_from, state_to, clickable, cost) in automata.get_edges():
            edge_data = {
                'from': state_from.get_id(),
                'to': state_to.get_id(),
                'clickable': clickable.get_id()
            }
            data['edge'].append(edge_data)

        with open(os.path.join(configuration.get_abs_path('root'), configuration.get_automata_fname()), 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)


def save_config(config, fname):
    config_data = {}
    config_data['max_depth'] = config.get_max_depth()
    config_data['max_states'] = config.get_max_states()
    config_data['max_time'] = config.get_max_time()
    config_data['sleep_time'] = config.get_sleep_time()
    config_data['app_name'] = config.get_app_name()
    config_data['app_id'] = config.get_app_id()
    config_data['automata_fname'] = config.get_automata_fname()
    config_data['root_path'] = posixpath.join(
        posixpath.join(*(config.get_path('root').split(os.sep)))
    )
    config_data['dom_path'] = posixpath.join(
        posixpath.join(*(config.get_path('dom').split(os.sep)))
    )
    config_data['state_path'] = posixpath.join(
        posixpath.join(*(config.get_path('state').split(os.sep)))
    )
    config_data['clickable_path'] = posixpath.join(
        posixpath.join(*(config.get_path('clickable').split(os.sep)))
    )
    with open(os.path.join(config.get_abs_path('root'), fname), 'w') as f:
        json.dump(config_data, f, indent=2, sort_keys=True, ensure_ascii=False)


def load_automata(fname):
    t_start = time.time()
    assert os.path.isfile(fname) and os.path.exists(fname)
    automata = Automata()
    with open(fname) as f:
        data = json.load(f)
        for state in data['state']:
            with open(os.path.join(os.path.dirname(os.path.realpath(fname)), state['dom_path']), 'r') as df:
                s = State(df.read())
                s.set_id(state['id'])
                for clickable in state['clickable']:
                    c = Clickable(clickable['id'], clickable['xpath'], clickable['tag'])
                    for form in clickable['form']:
                        f = FormField(form['id'], form['xpath'])
                        for the_input in form['input']:
                            f.add_input(InputField(the_input['id'], the_input['xpath'], the_input['type'], the_input['value']))
                        c.add_form(f)
                    s.add_clickable(c)
                automata.add_state(s)
        for edge in data['edge']:
            from_state = automata.get_state_by_id(edge['from'])
            to_state = automata.get_state_by_id(edge['to'])
            clickable = from_state.get_clickable_by_id(edge['clickable'])
            assert from_state and to_state and clickable
            automata.add_edge(from_state, to_state, clickable)
    print 'automata loaded. loading time: %f sec' % (time.time() - t_start)
    return automata


def load_config(fname):
    t_start = time.time()
    with open(fname) as f:
        data = json.load(f)
        config = B2gConfiguration(data['app_name'], data['app_id'])
        config.set_max_depth(int(data['max_depth']))
        config.set_max_states(int(data['max_states']))
        config.set_sleep_time(int(data['sleep_time']))
        config.set_max_time(int(data['max_time']))
        # ignore the rest ('automata_fname', 'root_path', 'dom_path', 'state_path', 'clickable_path')
        print 'config loaded. loading time: %f sec' % (time.time() - t_start)
    return config



if __name__ == '__main__':
    main()
