# Scout SDK (Python)

```python
from scout_sdk import ScoutClient, ScoutConfig

client = ScoutClient(ScoutConfig(api_key="sk-..."))
resp = client.send_message(chatbot_id="...", content="Hello")
print(resp)
```
