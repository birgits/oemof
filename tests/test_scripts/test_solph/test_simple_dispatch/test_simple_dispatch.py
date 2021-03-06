# -*- coding: utf-8 -*-

""" This example shows how to create an energysystem with oemof objects and
solve it with the solph module. Results are plotted with outputlib.

Data: example_data.csv
"""

import os
import pandas as pd
from oemof.network import Node
from oemof.solph import (Sink, Source, Transformer, Bus, Flow, Model,
                         EnergySystem)
from oemof.outputlib import processing, views


def test_dispatch_example(solver='cbc', periods=24*5):
    """Create an energy system and optimize the dispatch at least costs."""

    datetimeindex = pd.date_range('1/1/2012', periods=periods, freq='H')
    energysystem = EnergySystem(timeindex=datetimeindex)
    Node.registry = energysystem
    filename = os.path.join(os.path.dirname(__file__), 'input_data.csv')
    data = pd.read_csv(filename, sep=",")

    # ######################### create energysystem components ################

    # resource buses
    bcoal = Bus(label='coal', balanced=False)
    bgas = Bus(label='gas', balanced=False)
    boil = Bus(label='oil', balanced=False)
    blig = Bus(label='lignite', balanced=False)

    # electricity and heat
    bel = Bus(label='bel')
    bth = Bus(label='bth')

    # an excess and a shortage variable can help to avoid infeasible problems
    excess_el = Sink(label='excess_el', inputs={bel: Flow()})
    # shortage_el = Source(label='shortage_el',
    #                      outputs={bel: Flow(variable_costs=200)})

    # sources
    wind = Source(label='wind', outputs={bel: Flow(actual_value=data['wind'],
                  nominal_value=66.3, fixed=True)})

    pv = Source(label='pv', outputs={bel: Flow(actual_value=data['pv'],
                nominal_value=65.3, fixed=True)})

    # demands (electricity/heat)
    demand_el = Sink(label='demand_el', inputs={bel: Flow(nominal_value=85,
                     actual_value=data['demand_el'], fixed=True)})

    demand_th = Sink(label='demand_th',
                     inputs={bth: Flow(nominal_value=40,
                                       actual_value=data['demand_th'],
                                       fixed=True)})

    # power plants
    pp_coal = Transformer(label='pp_coal',
                          inputs={bcoal: Flow()},
                          outputs={bel: Flow(nominal_value=20.2,
                                                   variable_costs=25)},
                          conversion_factors={bel: 0.39})

    pp_lig = Transformer(label='pp_lig',
                         inputs={blig: Flow()},
                         outputs={bel: Flow(nominal_value=11.8,
                                                  variable_costs=19)},
                         conversion_factors={bel: 0.41})

    pp_gas = Transformer(label='pp_gas',
                         inputs={bgas: Flow()},
                         outputs={bel: Flow(nominal_value=41,
                                                  variable_costs=40)},
                         conversion_factors={bel: 0.50})

    pp_oil = Transformer(label='pp_oil',
                         inputs={boil: Flow()},
                         outputs={bel: Flow(nominal_value=5,
                                                  variable_costs=50)},
                         conversion_factors={bel: 0.28})

    # combined heat and power plant (chp)
    pp_chp = Transformer(label='pp_chp',
                         inputs={bgas: Flow()},
                         outputs={bel: Flow(nominal_value=30,
                                                  variable_costs=42),
                                        bth: Flow(nominal_value=40)},
                         conversion_factors={bel: 0.3, bth: 0.4})

    # heatpump with a coefficient of performance (COP) of 3
    b_heat_source = Bus(label='b_heat_source')

    heat_source = Source(label='heat_source', outputs={b_heat_source: Flow()})

    cop = 3
    heat_pump = Transformer(label='heat_pump',
                            inputs={bel: Flow(),
                                            b_heat_source: Flow()},
                            outputs={bth: Flow(nominal_value=10)},
                            conversion_factors={
                                        bel: 1/3, b_heat_source: (cop-1)/cop})

    # ################################ optimization ###########################

    # create optimization model based on energy_system
    optimization_model = Model(es=energysystem)

    # solve problem
    optimization_model.solve(solver=solver)

    # write back results from optimization object to energysystem
    optimization_model.results()

    # ################################ results ################################

    # generic result object
    results = processing.results(om=optimization_model)

    # subset of results that includes all flows into and from electrical bus
    # sequences are stored within a pandas.DataFrames and scalars e.g.
    # investment values within a pandas.Series object.
    # in this case the entry data['scalars'] does not exist since no investment
    # variables are used
    data = views.node(results, 'bel')

    # generate results to be evaluated in tests
    results= data['sequences'].sum(axis=0).to_dict()

    test_results = {
        (('wind', 'bel'), 'flow'): 1773,
        (('pv', 'bel'), 'flow'): 605,
        (('bel', 'demand_el'), 'flow'): 7440,
        (('bel', 'excess_el'), 'flow'): 139,
        (('pp_chp', 'bel'), 'flow'): 666,
        (('pp_lig', 'bel'), 'flow'): 1210,
        (('pp_gas', 'bel'), 'flow'): 1519,
        (('pp_coal', 'bel'), 'flow'): 1925,
        (('pp_oil', 'bel'), 'flow'): 0,
        (('bel', 'heat_pump'), 'flow'): 118,
    }

    for key in test_results.keys():
        a = int(round(results[key]))
        b = int(round(test_results[key]))
        assert a == b, "\n{0}: \nGot: {1}\nExpected: {2}".format(key, a, b)
