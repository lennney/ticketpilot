from openai import Openai_key = None
with open(".env.local") as f:
    for line in f:
        if line.startswith("TICKETPILOT_LLM_API_KEY=***            api_key = line.strip().split("=", 1)[1]
            break

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
print("Testing API...", flush=True)
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "回复OK"}],
    max_tokens=10,
)
print("Result:", resp.choices[0].message.content, flush=True)
