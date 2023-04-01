# A rough estimation of cloud cover percentage based on cloud type in NREL weather dataset
cloud_cover_mapping = {
    0: 0, # Clear
    1: 10, # Probably Clear
    2: 90, # Fog
    3: 70, # Water
    4: 80, # Super-Cooled Water
    5: 50, # Mixed
    6: 60, # Opaque Ice
    7: 20, # Cirrus
    8: 100, # Overlapping
    9: 100, # Overshooting
    10: 50, # Unknown
    11: 10, # Dust
    12: 10, # Smoke
    -15: 50, # N/A
}

def arrays_to_string(arrays):
    lines = [' '.join(map(str, row)) for row in arrays]
    return '\n'.join(lines)