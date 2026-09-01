from dotenv import load_dotenv
from google import genai

# Load variables from .env
load_dotenv()

# Create Gemini client
client = genai.Client()

# Send a small test request
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Reply with exactly: Gemini connection successful."
)

print("Gemini Response:")
print(response.text)