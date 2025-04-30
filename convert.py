import os
import time
import subprocess
from PIL import Image
import pillow_heif
import shutil

try:
    import pyheif
    PYHEIF_AVAILABLE = True
except ImportError:
    PYHEIF_AVAILABLE = False

FIX_ORIENTATION = True
input_folder = 'input'
output_folder = 'output'
temp_folder = 'temp_ffmpeg'

os.makedirs(output_folder, exist_ok=True)
os.makedirs(temp_folder, exist_ok=True)

supported_formats = ['.png', '.gif', '.tiff', '.bmp', '.ico', '.ppm', '.pbm', '.pgm', '.apng',
                     '.jpeg', '.jpg', '.jfif', '.heic']

files = [f for f in os.listdir(input_folder)
         if os.path.splitext(f.lower())[1] in supported_formats]

total_files = len(files)
start_time = time.time()
errors = []

def correct_orientation(img):
    try:
        exif = img.getexif()
        orientation = exif.get(274)
        if orientation == 3:
            img = img.rotate(180, expand=True)
        elif orientation == 6:
            img = img.rotate(270, expand=True)
        elif orientation == 8:
            img = img.rotate(90, expand=True)
    except Exception as e:
        print(f"EXIF processing error: {e}")
    return img

def process_heic_heif_pillow(file_path):
    try:
        heif_file = pillow_heif.read_heif(file_path)
        return Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
    except Exception:
        return None

def process_heic_pyheif(file_path):
    try:
        heif_file = pyheif.read(file_path)
        return Image.frombytes("RGB", (heif_file.width, heif_file.height), heif_file.data, "raw")
    except Exception:
        return None

def process_heic_ffmpeg(file_path, output_temp_path):
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', file_path, output_temp_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_temp_path):
            return Image.open(output_temp_path)
    except Exception as e:
        print(f"FFmpeg failed: {e}")
    return None

for i, file in enumerate(files):
    file_path = os.path.join(input_folder, file)
    base_name, ext = os.path.splitext(file)
    ext = ext.lower().lstrip('.')  # e.g., "heic"
    output_file_name = f"{base_name}({ext}).jpg"
    output_path = os.path.join(output_folder, output_file_name)

    try:
        img = None

        if ext == 'heic':
            img = process_heic_heif_pillow(file_path)

            if not img and PYHEIF_AVAILABLE:
                print(f"Trying pyheif for {file}")
                img = process_heic_pyheif(file_path)

            if not img:
                print(f"Trying ffmpeg for {file}")
                temp_jpg = os.path.join(temp_folder, f"{base_name}_temp.jpg")
                img = process_heic_ffmpeg(file_path, temp_jpg)

            if not img:
                raise Exception("HEIC file could not be processed by any method.")

        else:
            img = Image.open(file_path)

        if FIX_ORIENTATION:
            img = correct_orientation(img)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output_path, 'JPEG', quality=95)

        elapsed = time.time() - start_time
        avg = elapsed / (i + 1)
        remaining = avg * (total_files - i - 1)
        print(f"Processed: {i+1}/{total_files}, Remaining: {remaining:.2f}s")

    except Exception as e:
        print(f"Error processing {file}: {str(e)}")
        errors.append(f"{file}: {str(e)}")

shutil.rmtree(temp_folder, ignore_errors=True)

end_time = time.time()
print(f'\nCompleted. Successfully processed {total_files - len(errors)} of {total_files} files in {end_time - start_time:.2f}s.')

if errors:
    print('\nErrors:')
    for e in errors:
        print(f' - {e}')
