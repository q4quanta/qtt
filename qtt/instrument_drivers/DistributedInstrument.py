from qcodes import Instrument
from functools import partial
from zmqrpc.ZmqRpcClient import ZmqRpcClient
from zmqrpc.ZmqRpcServer import ZmqRpcServerThread

# -----------------------------------------------------------------------------


class InstrumentDataClient(Instrument):
    '''
    A proxy client for collecting instrument measurable quantities
    from a server.

    Args:
        name (str): the name of the instrument.
        address (str): the ip-address of the server.
        port (int): the port number of the proxy server.
        user (str): a username for protection.
        password (str): a password for protection.
    '''

    def __init__(self, name, address='localhost', port=8080, user=None,
                 password=None, **kwargs):
        super().__init__(name, **kwargs)
        self._client_ = ZmqRpcClient(["tcp://{0}:{1}".format(address, port)],
                                     username=user, password=password)

    def __proxy_wrapper__(self, command_name, default_value, sec_time_out=3):
        try:
            return self._client_.invoke(command_name, None, sec_time_out)
        except:
            return default_value

    def add_measurable_quantity(self, name='quantity', unit='arb.',
                                default_value=None, doc_string='Unknown'):
        '''Adds a instument function to the dataclient.'''
        command = partial(self.__proxy_wrapper__, command_name=name,
                          default_value=default_value)
        self.add_parameter(name, unit=unit, get_cmd=command,
                           docstring=doc_string)


# -----------------------------------------------------------------------------


class InstrumentDataServer():
    '''
    Represents a server proxy for sending instrument measurable quantities
    to a client.

    Args:
        functions (dict): the instrument functions.
        address (str): the ip-address of the server.
        port (int): the port number of the proxy server.
        user (str): a username for protection.
        password (str): a password for protection.
    '''

    def __init__(self, functions, address='*', port=8080, user=None,
                 password=None):
        self._server_ = ZmqRpcServerThread("tcp://{0}:{1}".format(
                                           address, port),
                                           rpc_functions=functions,
                                           username=user,
                                           password=password)

    def run(self):
        '''Start the server proxy on the set adrress and port-number.'''
        print(' Enabled instrument server...')
        print(' Press CTRL+C to quit!')
        try:
            self._server_.start()
            while(True):
                continue
        except KeyboardInterrupt:
            print(' Done')
        finally:
            self._server_.stop()
            self._server_.join()

# -----------------------------------------------------------------------------