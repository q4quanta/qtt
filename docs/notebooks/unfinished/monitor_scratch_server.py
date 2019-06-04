from qtt.instrument_drivers.fridge_monitor import InstrumentDataServer


class DummyServer:

    def __init__(self):
        self.test_value = 0
        data_server = InstrumentDataServer()
        data_server.rpc_functions = {'test_function': self.test_method}
        data_server.run()

    def test_method(self, value=None):
        if value:
            self.test_value = value
        else:
            self.test_value += 1
        return self.test_value


if __name__ == '__main__':
    DummyServer()
