from qtt.instrument_drivers.fridge_monitor import InstrumentDataClient


client = InstrumentDataClient(name='client')
client.connect()

client.add_full_parameter('test_function', default_value=0)

client.test_function()
client.test_function({'value': 100})
client.test_function()
client.test_function()
