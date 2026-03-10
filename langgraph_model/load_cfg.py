import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

DATAPATH = os.getenv('DATAPATH', 'data/')

MODEL_NAME = os.getenv('MODEL_NAME','Doubao-DeepSeek-V3')
BASE_URL = os.getenv('BASE_URL','http://oneapi-dev.skytech.io/v1')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

STREAM_MODE = "messages"