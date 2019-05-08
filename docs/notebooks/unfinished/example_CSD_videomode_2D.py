import numpy as np

from PyQt5.QtWidgets import QApplication
from qcodes import Instrument, ManualParameter, Station
from qcodes.instrument_drivers.ZI.ZIHDAWG8 import WARNING_ANY, ZIHDAWG8
from qcodes.utils.validators import Numbers

from qtt.instrument_drivers.virtualAwg.virtual_awg import VirtualAwg
from qtt.measurements.acquisition import UHFLIScopeReader
from qtt.measurements.videomode import VideoMode


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


## INITIALIZE THE SCOPE

device_id = 'dev2338'
scope_reader = UHFLIScopeReader(device_id)


# INITIALIZE THE AWG

awg = ZIHDAWG8(name='HDAWG8', device_id='dev8048')
# awg.warnings_as_errors.append(WARNING_ANY)

grouping_1x8 = 2
awg.set_channel_grouping(grouping_1x8)

output4_marker1 = 4
awg.triggers_out_4_source(output4_marker1)

awg_sampling_rate_586KHz = 12
awg.awgs_0_time(awg_sampling_rate_586KHz)


# PREPARE ACQUISITION

scope_reader.input_range = (1, 1)

uhfli_sample_rate = 220e3
nearest_uhfli_sample_rate = scope_reader.get_nearest_sample_rate(uhfli_sample_rate)
scope_reader.sample_rate = nearest_uhfli_sample_rate

scope_reader.trigger_enabled = True
scope_reader.trigger_channel = 'Trig Input 1'
scope_reader.trigger_level = 0.500
scope_reader.trigger_slope = 'Rise'
scope_reader.trigger_delay = 0


# INITIALIZE THE VIRTUAL AWG

virtual_awg = VirtualAwg([awg], settings)

width = 30/32
resolution = [64, 64]
cable_compensation = 0.0305
period = resolution[0] * resolution[1] / nearest_uhfli_sample_rate
marker_delay = (0.5 + (1 - width) - cable_compensation) * period
virtual_awg.digitizer_marker_delay(marker_delay)

marker_uptime = 0.1 * period
virtual_awg.digitizer_marker_uptime(marker_uptime)


# STATION

class FakeGates:
    def allvalues(self):
        return {}

station = Station(virtual_awg, scope_reader.adapter.instrument)
station.gates = FakeGates()


# VIDEO MODE

app = QApplication([])

sweep_gates = [{'P1': 1}, {'P2': 1}]
sweep_ranges = [1000, 1000]
scope = (scope_reader, [(1, 'Signal Input 1'), (2, 'Signal Input 2')])

vm = VideoMode(station, sweep_gates, sweep_ranges, minstrument=scope, resolution=resolution)
vm.updatebg()

app.exec_()
