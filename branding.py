from pathlib import Path
from PIL import Image
def logo_image():
    with Image.open(Path(__file__).parent/'assets/logo-aprovada.png') as raw:return raw.convert('RGB')
