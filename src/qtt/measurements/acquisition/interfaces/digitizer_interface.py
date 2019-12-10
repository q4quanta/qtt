""" Interface for devices to acquire data."""

from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np
from qcodes import Station
from qilib.utils import PythonJsonStructure
from qilib.configuration_helper import InstrumentAdapterFactory

class DigitizerInterface(ABC):
    """ An interface which contains the functionality for collecting data using a acquisition device."""

    def __init__(self, instrument_adapter_class_name: str, address: str,
                 instrument_name: Optional[str] = None) -> None:
        """ Creates and connects the acquisition device from the given address.

        Args:
            instrument_adapter_class_name: Name of the InstrumentAdapter subclass.
            address: Address of the physical instrument.
            instrument_name: An optional name for the underlying instrument.
        """
        self._adapter = InstrumentAdapterFactory.get_instrument_adapter(instrument_adapter_class_name,
                                                                        address, instrument_name)
        self._digitizer = self._adapter.instrument

    @property
    def adapter(self):
        """ Returns the instrument adapter"""
        return self._adapter

    @property
    def digitizer(self):
        return self._digitizer

    @abstractmethod
    def start_acquisition(self) -> None:
        """ Starts the acquisition readout mode.

            This method should be called after initializing the acquisition
            device and before reading out the device with acquire.
        """

    @abstractmethod
    def acquire(self, number_of_averages: int, timeout: float = 30) -> np.ndarray:
        """ Reads raw-data from the acquisition device.

            This method should be called after initializing and starting the acquisition.

        Args:
            number_of_averages: The number of averages taken during acquiring.
            timeout: The maximum period in seconds to acquire records.

        Returns:
            A array with the collected scope records and with settings in the metadata.
        """

    @abstractmethod
    def stop_acquisition(self) -> None:
        """ Stops the acquisition readout mode.

            This function should be called after acquiring with the readout device.
        """
