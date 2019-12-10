import time
from typing import Any, List, Optional, Union

import numpy as np
from qcodes import Station, Parameter
from qcodes.instrument_drivers.ZI.ZIUHFLI import ZIUHFLI

from qtt.measurements.acquisition.interfaces import DigitizerInterface


class UhfliDigitizer(DigitizerInterface):

    def __init__(self, address: str, instrument_name: Optional[str] = None):
        """ Creates and connects the UHFLI digitizer from the given address.

        Args:
            address: Address of the physical instrument.
            instrument_name: An optional name for the underlying instrument.
        """
        super().__init__('ZIUHFLIInstrumentAdapter', address, instrument_name) 
        self.__acquisition_counter = 0

    """
    def __init__(self, digitizer: ZIUHFLI) -> None:
        Creates and connects the acquisition device from the given address.

        Args:
            station: The qcodes station.
            digitizer: The unique device identifier.
            digitizer_class_name: The class name of the digitizer.
        
        super().__init__(digitizer, ZIUHFLI)
        self._address = self._digitizer.device
        self.__acquisition_counter = 0
    """

    def start_acquisition(self) -> None:
        """ Starts the acquisition mode of the scope in the UHFLI."""
        self._digitizer.scope.set('scopeModule/mode', 1)
        self._digitizer.scope.subscribe(f'/{self._address}/scopes/0/wave')
        self._digitizer.daq.sync()
        self._digitizer.daq.setInt(f'/{self._address}/scopes/0/enable', 1)

    def acquire(self, number_of_averages: int, timeout: float = 30) -> np.ndarray:
        """ Collects records from the UHFLI.

        Args:
            number_of_averages: The number of averages taken during acquiring.
            timeout: The time the collecting of records can maximally take before raising an error.

        Returns:
            A list with the recorded scope records as data arrays.
        """
        self.__create_setpoint_data()
        return self.__get_uhfli_scope_records(number_of_averages, timeout)

    def stop_acquisition(self) -> None:
        """ Stops the acquisition mode of the scope in the UHFLI."""
        self._digitizer.daq.setInt(f'/{self._address}/scopes/0/enable', 0)
        self._digitizer.scope.finish()

    def acquire_single_sample(self, channel: int, parameter: str, partial: bool = False) -> Union[Parameter, float]:
        """ Collect a single point for each added measurement signal.

        Args:
            channel: Input channel that signal is acquired from.
            parameter: Modulation parameter, 'x', 'y', 'phi' or 'R'
            partial: If True return this method as partial, else acquire a sample and return it.

        Returns:
            This method as a partial method or single sample.

        """
        demod_parameter = getattr(self._digitizer, f'demod{channel}_{parameter}')
        return demod_parameter if partial else demod_parameter()

    def __create_setpoint_data(self) -> None:
        sample_count = self._digitizer.scope_length()
        data_array = np.array([1,]) #DataArray('ScopeTime', 'Time', unit='s', is_setpoint=True,
                                #preset_data=np.linspace(0, self.period, sample_count))
        self.__setpoint_array = data_array

    def __get_uhfli_scope_records(self, number_of_averages: int, timeout: float) -> np.ndarray:
        self._digitizer.scope.execute()

        records = 0
        progress = 0
        start = time.time()
        while records < number_of_averages or progress < 1.0:
            records = self._digitizer.scope.getInt('scopeModule/records')
            progress = self._digitizer.scope.progress()[0]
            if time.time() - start > timeout:
                error_text = f'Got {records} records after {timeout} sec. - forcing stop.'
                raise TimeoutError(error_text)

        traces = self._digitizer.scope.read(True)
        wave_nodepath = f'/{self._address}/scopes/0/wave'
        scope_traces = traces[wave_nodepath][:number_of_averages]
        return self.__convert_scope_data(scope_traces)

    def __convert_scope_data(self, scope_traces: np.ndarray) -> np.ndarray:
        data = []
        acquisition_counter = 0
        for channel_index, _ in enumerate(self.channels):
            channel_data = np.array([trace[0]['wave'][channel_index] for trace in scope_traces])
            averaged_data = np.average(channel_data, axis=0)
            # data_array = self.__convert_to_data_array(averaged_data, channel_index, acquisition_counter)
            data.append(averaged_data)
            acquisition_counter += 1
        return np.asarray(data)

    def __convert_to_data_array(self, scope_data: np.array, channel_index: int, counter: int) -> np.array:
        channel_number = channel_index + 1
        identifier = f'ScopeTrace{counter:03d}_Channel{channel_number}'
        input_parameter = getattr(self._digitizer, f'scope_channel{channel_number}_input')
        label = input_parameter().replace(' ', '_')

        return DataArray(identifier, label, unit='V', preset_data=scope_data, set_arrays=[self.__setpoint_array])
