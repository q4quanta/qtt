from qtt.instrument_drivers.fridge_monitor import InstrumentDataServer
from qcodes import Instrument


class DummyInstrument(Instrument):

    def __init__(self, name):
        super().__init__(name)
        self.__value = 0
        self.add_parameter('dummy', set_cmd=self.set_value, get_cmd=self.get_value)

    def set_value(self, value):
        self.__value = value

    def get_value(self):
        return self.__value


class DummyServer:

    def __init__(self):
        self.instrument = DummyInstrument('dummy')

        data_server = InstrumentDataServer()
        data_server.rpc_functions = {'test_function': self.test_function}
        data_server.run()

    def test_function(self, argument=None):
        if argument:
            self.instrument.dummy(argument)
        return self.instrument.dummy()


if __name__ == '__main__':
    DummyServer()
