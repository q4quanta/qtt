""" Interface for devices to acquire data."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from qcodes import Station


class DigitizerInterface(ABC):
    """ An interface which contains the functionality for collecting data using a acquisition device."""

    def __init__(self, station: Station, digitizer: Any, digitizer_class_name: type) -> None:
        """ Creates and connects the acquisition device from the given address.

        Args:
            station: The qcodes station.
            digitizer: The unique device identifier.
            digitizer_class_name: The class name of the digitizer.
        """
        self._station = station
        self._digitizer = digitizer
        if not isinstance(digitizer, digitizer_class_name):
            ValueError(f'Invalid type of digitizer provided ({type(digitizer)} != {str(digitizer_class_name)})!')

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
