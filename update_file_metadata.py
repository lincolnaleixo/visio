import os
import time
from datetime import datetime
from pathlib import Path
import re

def parse_filename(filename):
    """
    Parse the filename to extract the Unix timestamp.

    Expected pattern: YYYYMMDD-HHMMSS-timestamp
    Example: 20210811-104712-1628671632
    """
    # Define the regex pattern to extract the timestamp
    pattern = r'\d{8}-\d{6}-(\d+)'
    match = re.search(pattern, filename)
    
    if not match:
        raise ValueError(f"Unable to find date-time pattern in filename: {filename}")
    
    timestamp_str = match.group(1)
    print(f"Debug: Extracted timestamp string: {timestamp_str}")
    
    try:
        timestamp = int(timestamp_str)
        # Optionally, verify if the timestamp is valid
        date_time_obj = datetime.fromtimestamp(timestamp)
    except (ValueError, OSError) as e:
        raise ValueError(f"Invalid timestamp in filename: {filename}. Error: {e}")
    
    return timestamp

def set_file_times(file_path, timestamp):
    """Set the file's modification time and access time."""
    os.utime(file_path, (timestamp, timestamp))

def process_file(file_path):
    """Process a single file, updating its metadata based on the filename."""
    filename = file_path.name
    print(f"Debug: Processing file: {filename}")
    
    try:
        timestamp = parse_filename(filename)
        set_file_times(file_path, timestamp)
        print(f"Updated metadata for {filename}")
    except ValueError as e:
        print(f"Skipping {filename}: {str(e)}")

def main():
    # Directory containing the files
    directory = Path("update_test")  # Update this path as needed
    
    if not directory.exists():
        print(f"Error: The directory '{directory}' does not exist.")
        return
    
    # Find all files matching the pattern
    files_to_process = list(directory.glob("motion_*.mp4"))  # Adjust the glob pattern if needed
    print(f"Debug: Found {len(files_to_process)} files to process")
    
    for file_path in files_to_process:
        process_file(file_path)

if __name__ == "__main__":
    main()
