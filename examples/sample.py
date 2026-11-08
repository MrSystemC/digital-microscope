def analyze(data):
    """Simple analyzer."""
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(item.get("name"))
    return result

class Microscope:
    def __init__(self, zoom=1):
        self.zoom = zoom

    def focus(self, target):
        return f"Focused on {target} at {self.zoom}x"
