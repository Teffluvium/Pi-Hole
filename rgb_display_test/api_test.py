import requests

from pihole6api import PiHole6Client

url = "http://localhost"
password = "2A+EambjgEiPTnfo1nodZ5nagEBm++MHXFVQZKMl8vE="

client = PiHole6Client(url, password)

# history = client.metrics.get_history()
# print(history)  # {'history': [{'timestamp': 1740120900, 'total': 0, 'cached': 0 ...}]}

# queries = client.metrics.get_queries()
# print(queries)

print()
stats = client.metrics.get_stats_summary()
# stats = client.metrics.get_stats_query_types()
_ = [print(f"{k}: {v}") for k,v in stats.items()]
print(stats)
