from together import Together

# Initialize client with API key
client = Together(api_key="99119015c00e5e948acff2763710ed0cd93b9dad1b3bbe4b794c120f5d01675f")

# Make a request to the Llama-3.3-70B-Instruct-Turbo-Free model
response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    messages=[{"role": "user", "content": "What are some fun things to do in New York?"}],
)

# Print the response
print(response.choices[0].message.content)
