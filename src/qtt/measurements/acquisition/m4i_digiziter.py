import logging
from typing import Any, List, Optional

import numpy as np
from qcodes_contrib_drivers.drivers.Spectrum.M4i import M4i

import pyspcm
from qtt.measurements.acquisition.interfaces import DigitizerInterface


class M4iDigitizer(DigitizerInterface):

    def __init__(self, station: Any, digitizer: M4i):
        super().__init__(station, digitizer, M4i)

    def initialize(self, period: float, channels: List[int], average_traces: bool,
                   number_of_segments: int, mV_range: Optional[float] = None, 
                   trigger_re_arm_compensation: Optional[int] = None,
                   trigger_re_arm_padding: Optional[bool] = False,
                   verbose: Optional[int] = 0) -> None:
        """ Initializes the M4i digitizer by applying the provided settings.

        Args:
            period: The measurement period of the seconds.
            channels: The channels to enable for readout.
            average_traces: Enables or disables the averaging of the measured data.
            number_of_segments: The number of segments of period length to fit in memory.
            trigger_re_arm_compensation: In block average mode the M4i needs a time of 40 samples + pretrigger to
                re-arm the triggering. With this option the segment size is reduced. The signal_end can be larger
                then the segment size.
        """
        self.verbose = verbose
        self.period = period
        self.mV_range = mV_range
        self.channels = channels
        self.average_traces = average_traces
        self.number_of_segments = number_of_segments
        self.trigger_re_arm_padding = trigger_re_arm_padding
        self.trigger_re_arm_compensation = trigger_re_arm_compensation
        self.memory_settings: List[int] = []
        self.__fix_m4i_acquisition()

    def start_acquisition(self) -> None:
        """ Starts the acquisition readout mode.

            This method should be called after initializing the acquisition
            device and before reading out the device with acquire.
        """
        sample_rate = self._digitizer.exact_sample_rate()
        if sample_rate == 0:
            raise ValueError('M4i sample rate is zero, please reset the digitizer!')

        maxrate = self._digitizer.max_sample_rate()
        if sample_rate > maxrate:
            raise ValueError(f'M4i sample rate is > {maxrate // 1e6} MHz, this is not supported!')

        if self.mV_range is None:
            self.mV_range = self._digitizer.range_channel_0()

        self.__select_m4i_memory_size()
        self._digitizer.initialize_channels(self.channels, mV_range=self.mV_range,
                                            memsize=self.memory_settings[0], termination=None)

    def acquire(self, number_of_averages: int, timeout: float = 30) -> np.ndarray:
        """ Reads raw-data from the acquisition device.

            This method should be called after initializing and starting the acquisition.

        Args:
            number_of_averages: The number of averages taken during acquiring.
            timeout: The maximum period in seconds to acquire records.

        Returns:
            A array with the collected scope records and with settings in the metadata.
        """
        post_trigger = self._digitizer.posttrigger_memory_size()
        raw_data = self._digitizer.blockavg_hardware_trigger_acquisition(mV_range=self.mV_range,
                                                                         nr_averages=number_of_averages,
                                                                         post_trigger=post_trigger)
        return self.__collect_data(raw_data)

    def stop_acquisition(self) -> None:
        """ Stops the acquisition readout mode.

            This function should be called after acquiring with the readout device.
        """
        pass

    def __fix_m4i_acquisition(self):
        """ Helper method to get some settings for the M4i right."""
        trigger_or_mask = self._digitizer.trigger_or_mask()
        external_trigger_mode = self._digitizer.external_trigger_mode()
        if self.verbose:
            logging.info(f'set m4i.trigger_or_mask() from {trigger_or_mask} to {pyspcm.SPC_TMASK_EXT0}')
            logging.info(f'set m4i.external_trigger_mode() from {external_trigger_mode} to {pyspcm.SPC_TM_POS}')

        self._digitizer.external_trigger_mode(pyspcm.SPC_TM_POS)
        self._digitizer.trigger_or_mask(pyspcm.SPC_TMASK_EXT0)

    def __select_m4i_memory_size(self):
        """ Selects suitable memory size for a given period.

        The selected memory size is the period times the sample rate, but rounded above to a multiple of 16.
        Additionally, extra pixels are added because of pretrigger_memsize requirements of the m4i.

        Returns:
            memsize (int): The total memory size selected.
            pre_trigger (int): The size of pretrigger selected.
            signal_start (int): The starting position of signal in pixels.
            signal_end (int): The end position of signal in pixels.
        """
        sample_rate = self._digitizer.exact_sample_rate()
        if sample_rate == 0:
            raise ValueError('Digitizer has zero sample rate! Please reset digitizer...')
        number_points_period = int(self.period * sample_rate)

        trigger_delay = getattr(self._digitizer, 'signal_delay', None)
        if trigger_delay is None or trigger_delay == 0:
            trigger_delay = 0
        else:
            logging.warn('Non-zero trigger_delay is untested!')
        trigger_delay_points = 16 * trigger_delay

        basic_pretrigger_size = 16
        base_segment_size = ceil_n(number_points_period + trigger_delay_points, 16) + basic_pretrigger_size

        memory_size = base_segment_size * self.number_of_segments
        if memory_size > self._digitizer.memory():
            raise ValueError(f'Trying to acquire too many points. Reduce sampling rate, period \
                             {self.period} or number segments {self.number_of_segments}')

        pre_trigger = ceil_n(trigger_delay * sample_rate, 16) + basic_pretrigger_size
        post_trigger = ceil_n(base_segment_size - pre_trigger, 16)

        if trigger_re_arm_compensation:
            max_segment_size_re_arm = floor_n(number_points_period - pre_trigger - 40, 16)
            if self.verbose:
                logging.info(f'Select_m4i_memsize: post_trigger {post_trigger}, \
                             max_segment_size_rearm {max_segment_size_re_arm}.')
            post_trigger = min(post_trigger, max_segment_size_re_arm)
            memsize = (pre_trigger + post_trigger) * self.number_of_segments

        signal_start = basic_pretrigger_size + int(trigger_delay_points)
        signal_end = signal_start + number_points_period

        self._digitizer.data_memory_size.set(memsize)
        self._digitizer.posttrigger_memory_size(post_trigger)
        self.memory_settings = (memory_size, pre_trigger, signal_start, signal_end)

        if self.verbose:
            logging.info(f'select_m4i_memsize {self._digitizer.name}: sample rate \
                         {sample_rate / 1e6:.3f} Mhz, period {period * 1e3} [ms]')
            logging.info(f'select_m4i_memsize {self._digitizer.name}: trace \
                         {number_points_period} points, selected memsize {memory_size}')
            logging.info(f'select_m4i_memsize {self._digitizer.name}: pre and post trigger: \
                         {self._digitizer.pretrigger_memory_size()} {self._digitizer.posttrigger_memory_size()}')
            logging.info(f'select_m4i_memsize {self._digitizer.name}: signal_start \
                         {signal_start}, signal_end {signal_end}')

    @staticmethod
    def __trigger_re_arm_padding(data: np.ndarray, signal_start: int, signal_end: int, verbose: int = 0):
        """ Pad array to specified size in last dimension."""
        number_of_samples = signal_end - signal_start
        re_arm_padding = (number_of_samples) - data.shape[-1]
        data = np.concatenate((data, np.zeros( data.shape[:-1] + (re_arm_padding, ))), axis=-1)
        if verbose:
            logging.info(f'measure_raw_segment_m4i: re-arm padding: {re_arm_padding}')

        return data

    def __collect_data(self, raw_data: np.ndarray, verbose: int = 0):
        (memory_size, _, signal_start, signal_end) = self.memory_settings
        if isinstance(raw_data, tuple):
            raw_data = raw_data[0]

        data = np.transpose(np.reshape(raw_data, [-1, len(self.channels)]))
        data = data[:, signal_start:signal_end]
        if self.trigger_re_arm_compensation and self.trigger_re_arm_padding:
            data = M4iDigitizer.__trigger_re_arm_padding(data, signal_start, signal_end, verbose)

        return data


def ceil_n(input_data, n):
    """ Return the ceiling of the input, element-wise closed to devider n."""
    return int(n * np.ceil(input_data / n))


def floor_n(x, n):
    """ Return the floor of the input, element-wise closed to devider n."""
    return int(n * np.floor( x // n))
