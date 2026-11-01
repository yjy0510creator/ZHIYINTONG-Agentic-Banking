"""Initialize empty local schema, without seed transactions or financial writes."""
from dotenv import load_dotenv
load_dotenv()
from services.api_v3 import db,audit
from services.intelligence import initialize
initialize()
print('SQLite schema ready; audit chain tip:',audit.verify())
