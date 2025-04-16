# Artineo

## Activité 4 - Kinect

### Requirements

- Python 3.11.2
- `pip install -r requirements.txt`
- Modifier le fichier `POCs/kinect/dependencies/pykinect2/PyKinectRuntime.py` et remplacer les imports par : 
```
from dependencies.pykinect2 import PyKinectV2
from dependencies.pykinect2.PyKinectV2 import *
```