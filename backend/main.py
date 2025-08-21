from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4.1-mini",
    input="Tell me about the themes in 'Pride and Prejudice' by Jane Austen.",
    max_output_tokens=500,
    store=False
)
print(response.output[0].content[0].text)