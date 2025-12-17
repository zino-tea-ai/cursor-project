import json
import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Status ===")
for p in projects:
    screens_dir = f'projects/{p}/Screens'
    structured_file = f'projects/{p}/structured_descriptions.json'
    
    screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
    
    analyzed = 0
    if os.path.exists(structured_file):
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyzed = len(data)
    
    status = 'OK' if analyzed >= len(screens) else f'NEED ANALYSIS'
    print(f'{p}: {len(screens)} screens, {analyzed} analyzed - {status}')



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Status ===")
for p in projects:
    screens_dir = f'projects/{p}/Screens'
    structured_file = f'projects/{p}/structured_descriptions.json'
    
    screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
    
    analyzed = 0
    if os.path.exists(structured_file):
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyzed = len(data)
    
    status = 'OK' if analyzed >= len(screens) else f'NEED ANALYSIS'
    print(f'{p}: {len(screens)} screens, {analyzed} analyzed - {status}')



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Status ===")
for p in projects:
    screens_dir = f'projects/{p}/Screens'
    structured_file = f'projects/{p}/structured_descriptions.json'
    
    screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
    
    analyzed = 0
    if os.path.exists(structured_file):
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyzed = len(data)
    
    status = 'OK' if analyzed >= len(screens) else f'NEED ANALYSIS'
    print(f'{p}: {len(screens)} screens, {analyzed} analyzed - {status}')



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Status ===")
for p in projects:
    screens_dir = f'projects/{p}/Screens'
    structured_file = f'projects/{p}/structured_descriptions.json'
    
    screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
    
    analyzed = 0
    if os.path.exists(structured_file):
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyzed = len(data)
    
    status = 'OK' if analyzed >= len(screens) else f'NEED ANALYSIS'
    print(f'{p}: {len(screens)} screens, {analyzed} analyzed - {status}')




import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Status ===")
for p in projects:
    screens_dir = f'projects/{p}/Screens'
    structured_file = f'projects/{p}/structured_descriptions.json'
    
    screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
    
    analyzed = 0
    if os.path.exists(structured_file):
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyzed = len(data)
    
    status = 'OK' if analyzed >= len(screens) else f'NEED ANALYSIS'
    print(f'{p}: {len(screens)} screens, {analyzed} analyzed - {status}')



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Status ===")
for p in projects:
    screens_dir = f'projects/{p}/Screens'
    structured_file = f'projects/{p}/structured_descriptions.json'
    
    screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
    
    analyzed = 0
    if os.path.exists(structured_file):
        with open(structured_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyzed = len(data)
    
    status = 'OK' if analyzed >= len(screens) else f'NEED ANALYSIS'
    print(f'{p}: {len(screens)} screens, {analyzed} analyzed - {status}')



















