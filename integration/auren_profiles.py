"""Task-owned public names, shared with the interface; stable adapter IDs remain unchanged."""
import json
from pathlib import Path
DEFINITIONS=json.loads((Path(__file__).resolve().parents[1]/'src/lib/utils/aurenProfiles.json').read_text())
def profile_name(task, profile):
 return next((p['name'] for p in DEFINITIONS.get(task,{}).get('profiles',[]) if p['id']==profile), None)
