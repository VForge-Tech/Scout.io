# Scout SDK (JS)

```js
import { ScoutClient } from "scout-sdk";

const client = new ScoutClient({ apiKey: "sk-..." });
const resp = await client.sendMessage("chatbot-id", "Hello");
console.log(resp);
```
