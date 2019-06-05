from qtt.instrument_drivers.fridge_monitor import InstrumentDataClient


client = InstrumentDataClient(name='client')
client.connect()

client.add_get_set_parameter('test_function', default_value=0)

client.test_function(100)
client.test_function()
