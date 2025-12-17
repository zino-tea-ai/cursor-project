import json
import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Quality Check ===\n")
for p in projects:
    ai_file = f'projects/{p}/ai_analysis.json'
    if os.path.exists(ai_file):
        size_kb = os.path.getsize(ai_file) / 1024
        with open(ai_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        if results:
            first_key = list(results.keys())[0]
            first_item = results[first_key]
            has_highlights = 'design_highlights' in first_item and len(first_item.get('design_highlights', [])) > 0
            has_insight = 'product_insight' in first_item and (first_item.get('product_insight', {}).get('cn') or first_item.get('product_insight', {}).get('en'))
            has_naming = 'naming' in first_item and first_item.get('naming', {}).get('cn')
            
            status = "NEW" if (has_highlights and has_insight and has_naming) else "OLD"
            print(f"{p}:")
            print(f"  Size: {size_kb:.1f}KB")
            print(f"  Count: {len(results)}")
            print(f"  Has naming: {has_naming}")
            print(f"  Has design_highlights: {has_highlights}")
            print(f"  Has product_insight: {has_insight}")
            print(f"  Status: {status}")
            print()



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Quality Check ===\n")
for p in projects:
    ai_file = f'projects/{p}/ai_analysis.json'
    if os.path.exists(ai_file):
        size_kb = os.path.getsize(ai_file) / 1024
        with open(ai_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        if results:
            first_key = list(results.keys())[0]
            first_item = results[first_key]
            has_highlights = 'design_highlights' in first_item and len(first_item.get('design_highlights', [])) > 0
            has_insight = 'product_insight' in first_item and (first_item.get('product_insight', {}).get('cn') or first_item.get('product_insight', {}).get('en'))
            has_naming = 'naming' in first_item and first_item.get('naming', {}).get('cn')
            
            status = "NEW" if (has_highlights and has_insight and has_naming) else "OLD"
            print(f"{p}:")
            print(f"  Size: {size_kb:.1f}KB")
            print(f"  Count: {len(results)}")
            print(f"  Has naming: {has_naming}")
            print(f"  Has design_highlights: {has_highlights}")
            print(f"  Has product_insight: {has_insight}")
            print(f"  Status: {status}")
            print()



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Quality Check ===\n")
for p in projects:
    ai_file = f'projects/{p}/ai_analysis.json'
    if os.path.exists(ai_file):
        size_kb = os.path.getsize(ai_file) / 1024
        with open(ai_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        if results:
            first_key = list(results.keys())[0]
            first_item = results[first_key]
            has_highlights = 'design_highlights' in first_item and len(first_item.get('design_highlights', [])) > 0
            has_insight = 'product_insight' in first_item and (first_item.get('product_insight', {}).get('cn') or first_item.get('product_insight', {}).get('en'))
            has_naming = 'naming' in first_item and first_item.get('naming', {}).get('cn')
            
            status = "NEW" if (has_highlights and has_insight and has_naming) else "OLD"
            print(f"{p}:")
            print(f"  Size: {size_kb:.1f}KB")
            print(f"  Count: {len(results)}")
            print(f"  Has naming: {has_naming}")
            print(f"  Has design_highlights: {has_highlights}")
            print(f"  Has product_insight: {has_insight}")
            print(f"  Status: {status}")
            print()



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Quality Check ===\n")
for p in projects:
    ai_file = f'projects/{p}/ai_analysis.json'
    if os.path.exists(ai_file):
        size_kb = os.path.getsize(ai_file) / 1024
        with open(ai_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        if results:
            first_key = list(results.keys())[0]
            first_item = results[first_key]
            has_highlights = 'design_highlights' in first_item and len(first_item.get('design_highlights', [])) > 0
            has_insight = 'product_insight' in first_item and (first_item.get('product_insight', {}).get('cn') or first_item.get('product_insight', {}).get('en'))
            has_naming = 'naming' in first_item and first_item.get('naming', {}).get('cn')
            
            status = "NEW" if (has_highlights and has_insight and has_naming) else "OLD"
            print(f"{p}:")
            print(f"  Size: {size_kb:.1f}KB")
            print(f"  Count: {len(results)}")
            print(f"  Has naming: {has_naming}")
            print(f"  Has design_highlights: {has_highlights}")
            print(f"  Has product_insight: {has_insight}")
            print(f"  Status: {status}")
            print()




import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Quality Check ===\n")
for p in projects:
    ai_file = f'projects/{p}/ai_analysis.json'
    if os.path.exists(ai_file):
        size_kb = os.path.getsize(ai_file) / 1024
        with open(ai_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        if results:
            first_key = list(results.keys())[0]
            first_item = results[first_key]
            has_highlights = 'design_highlights' in first_item and len(first_item.get('design_highlights', [])) > 0
            has_insight = 'product_insight' in first_item and (first_item.get('product_insight', {}).get('cn') or first_item.get('product_insight', {}).get('en'))
            has_naming = 'naming' in first_item and first_item.get('naming', {}).get('cn')
            
            status = "NEW" if (has_highlights and has_insight and has_naming) else "OLD"
            print(f"{p}:")
            print(f"  Size: {size_kb:.1f}KB")
            print(f"  Count: {len(results)}")
            print(f"  Has naming: {has_naming}")
            print(f"  Has design_highlights: {has_highlights}")
            print(f"  Has product_insight: {has_insight}")
            print(f"  Status: {status}")
            print()



import os

projects = ['Calm_Analysis', 'Flo_Analysis', 'MyFitnessPal_Analysis', 'Runna_Analysis', 'Strava_Analysis']

print("=== Analysis Quality Check ===\n")
for p in projects:
    ai_file = f'projects/{p}/ai_analysis.json'
    if os.path.exists(ai_file):
        size_kb = os.path.getsize(ai_file) / 1024
        with open(ai_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        if results:
            first_key = list(results.keys())[0]
            first_item = results[first_key]
            has_highlights = 'design_highlights' in first_item and len(first_item.get('design_highlights', [])) > 0
            has_insight = 'product_insight' in first_item and (first_item.get('product_insight', {}).get('cn') or first_item.get('product_insight', {}).get('en'))
            has_naming = 'naming' in first_item and first_item.get('naming', {}).get('cn')
            
            status = "NEW" if (has_highlights and has_insight and has_naming) else "OLD"
            print(f"{p}:")
            print(f"  Size: {size_kb:.1f}KB")
            print(f"  Count: {len(results)}")
            print(f"  Has naming: {has_naming}")
            print(f"  Has design_highlights: {has_highlights}")
            print(f"  Has product_insight: {has_insight}")
            print(f"  Status: {status}")
            print()



















