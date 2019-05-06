import os
from itertools import cycle

import matplotlib.pyplot as plt
import numpy as np
from qcodes import Instrument, ManualParameter, Station
from qcodes.instrument_drivers.ZI.ZIHDAWG8 import ZIHDAWG8
from qcodes.utils.validators import Numbers
from qilib.data_set import DataSet, DataArray
from scipy.signal import sawtooth

from qtt.instrument_drivers.virtualAwg.virtual_awg import VirtualAwg
from qtt.measurements.acquisition import UHFLIScopeReader, load_configuration
from qtt.measurements.post_processing import SignalProcessorRunner, ProcessSawtooth2D


color_cycler = cycle('bgrcmk')


def plot_1D_dataset(plot, record, label_x, label_y):
    plot.clf()
    plot.xlabel(label_x)
    plot.ylabel(label_y)

    plot.plot(record[0].set_arrays[0].flatten(), record[0].flatten(), color=next(color_cycler), label=record[0].name)
    plot.plot(record[1].set_arrays[0].flatten(), record[1].flatten(), color=next(color_cycler), label=record[1].name)
    plot.legend(loc='upper left')
    plot.draw()
    plot.pause(0.001)


## INITIALIZE THE HARDWARE SETTINGS

class HardwareSettings(Instrument):

    def __init__(self, name='settings'):
        super().__init__(name)
        awg_gates = {'P1': (0, 0), 'P2': (0, 1)}
        awg_markers = {'m4i_mk': (0, 4, 0)}
        self.awg_map = {**awg_gates, **awg_markers}

        for awg_gate in self.awg_map:
            parameter_name = 'awg_to_{}'.format(awg_gate)
            parameter_label = '{} (factor)'.format(parameter_name)
            self.add_parameter(parameter_name, parameter_class=ManualParameter,
                               initial_value=1000, label=parameter_label, vals=Numbers(1, 1000))

settings = HardwareSettings()


resolution = [64, 64]

width_0 = 30/32
width = [width_0, width_0]


## INITIALIZE THE SCOPE

device_id = 'dev2338'
scope_reader = UHFLIScopeReader(device_id)
uhfli = scope_reader.adapter.instrument

file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uhfli.dat')
# configuration = load_configuration(file_path)
# scope_reader.initialize(configuration)



# INITIALIZE THE AWG

awg = ZIHDAWG8(name='HDAWG8', device_id='dev8048')

grouping_1x8 = 2
awg.set_channel_grouping(grouping_1x8)

output4_marker1 = 4
awg.triggers_out_4_source(output4_marker1)

awg_sampling_rate_9_37MHz = 7
awg.awgs_0_time(awg_sampling_rate_9_37MHz)


# PREPARE ACQUISITION

uhfli_sample_rate = 7.3e6
gates = [{'P1': 1}, {'P2': 1}]
sweep_ranges = [1000, 1000]


signal_processor = SignalProcessorRunner()
signal_processor.add_signal_processor(ProcessSawtooth2D())

scope_reader.number_of_averages = 1
scope_reader.input_range = (1, 1)

nearest_uhfli_sample_rate = scope_reader.get_nearest_sample_rate(uhfli_sample_rate)
scope_reader.sample_rate = nearest_uhfli_sample_rate
scope_reader.period = resolution[0] * resolution[1] / nearest_uhfli_sample_rate

scope_reader.enabled_channels = (1, 2)
scope_reader.set_input_signal(1, 'Signal Input 1')
scope_reader.set_input_signal(2, 'Signal Input 2')

scope_reader.trigger_enabled = True
scope_reader.trigger_channel = 'Trig Input 1'
scope_reader.trigger_level = 0.500
scope_reader.trigger_slope = 'Rise'
scope_reader.trigger_delay = 0


# INITIALIZE THE VIRTUAL AWG

period = resolution[0] * resolution[1] / nearest_uhfli_sample_rate
virtual_awg = VirtualAwg([awg], settings)

cable_compensation = 0.0305
marker_delay = (0.5 + (1 - width_0) - cable_compensation) * period
virtual_awg.digitizer_marker_delay(marker_delay)

marker_uptime = 0.5 * period
virtual_awg.digitizer_marker_uptime(marker_uptime)

_ = virtual_awg.sweep_gates_2d(gates, sweep_ranges, period, resolution, width=width_0)
keys = [list(item.keys())[0] for item in gates]
virtual_awg.enable_outputs(keys)
virtual_awg.run()


# ACQUISITION

data_set = DataSet()
data_set.user_data = {'width': width, 'resolution': resolution}

scope_reader.start_acquisition()

# _ = scope_reader.acquire()
acquired_data = scope_reader.acquire()


# STOP ACQUISITION

scope_reader.stop_acquisition()
keys = [list(item.keys())[0] for item in gates]
virtual_awg.disable_outputs(keys)
virtual_awg.stop()


# PLOT DATA

plt.figure(100)
plot_1D_dataset(plt, acquired_data, 'Time [sec.]', 'Amplitude [V]')
plt.show()

data_set.add_array(acquired_data[0])
data_set.add_array(acquired_data[1])
processed_data_set = signal_processor.run(data_set)


def plot_2d_result(processed_2d_data, figure_number=100):
    plt.figure(figure_number)
    plt.clf()
    plt.imshow(processed_2d_data)
    plt.show()

[plot_2d_result(data_array) for data_array in processed_data_set.data_arrays.values()]
