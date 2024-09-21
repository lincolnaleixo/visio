import av
import numpy as np
import os
import platform
from multiprocessing import Pool
import subprocess
import cv2
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_file_times(file_path):
    """
    Retrieve the access and modification times of the file.
    """
    stats = os.stat(file_path)
    access_time = stats.st_atime
    modification_time = stats.st_mtime
    return access_time, modification_time

def set_file_times(file_path, access_time, modification_time):
    """
    Set the access and modification times of the file.
    """
    os.utime(file_path, (access_time, modification_time))

def process_video(video_path, output_subdir):
    """
    Process a single video file:
    - Detect motion and create an output video with motion segments.
    - Preserve metadata (access and modification times).
    - Delete the original video file after processing.
    """
    # Open the video file using PyAV
    with av.open(video_path) as container:
        stream = container.streams.video[0]
        stream.codec_context.thread_type = av.codec.context.ThreadType.AUTO
        stream.codec_context.thread_count = 0  # Use all available threads

        # Get video properties
        fps = float(stream.average_rate)
        frame_count = stream.frames
        duration = float(stream.duration * stream.time_base)

        # Initialize background subtractor
        fgbg = cv2.createBackgroundSubtractorMOG2()

        # Parameters for motion detection sensitivity
        min_contour_area = int(os.getenv('MIN_CONTOUR_AREA', 500))

        # Lists to hold motion frames and intervals
        motion_frames = []
        current_frame = 0

        # Process each frame for motion detection
        for frame in container.decode(stream):
            # Convert PyAV frame to numpy array
            img = frame.to_ndarray(format='bgr24')
            current_time = current_frame / fps

            # Convert frame to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply background subtraction
            fgmask = fgbg.apply(gray)

            # Threshold the mask to get binary image
            _, fgmask = cv2.threshold(fgmask, 244, 255, cv2.THRESH_BINARY)

            # Find contours in the thresholded frame
            contours, _ = cv2.findContours(
                fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            # Check if any contour is large enough to be considered motion
            motion_detected = any(cv2.contourArea(contour) > min_contour_area for contour in contours)

            # Record the time if motion is detected
            if motion_detected:
                motion_frames.append(current_time)

            current_frame += 1

    # Process motion frames to create intervals
    intervals = []
    if motion_frames:
        start_time = motion_frames[0]
        end_time = motion_frames[0]
        for t in motion_frames[1:]:
            if t - end_time <= 1 / fps * 5:
                end_time = t
            else:
                intervals.append((start_time, end_time))
                start_time = t
                end_time = t
        intervals.append((start_time, end_time))

        # Add buffer to each interval
        buffer = float(os.getenv('BUFFER_TIME', 2))  # seconds
        for i in range(len(intervals)):
            start, end = intervals[i]
            start = max(0, start - buffer)
            end = min(duration, end + buffer)
            intervals[i] = (start, end)

        # Merge overlapping intervals
        intervals = merge_intervals(intervals)

        # Generate a list of start and end times for ffmpeg
        intervals_str = ''
        for start, end in intervals:
            intervals_str += f"between(t,{start},{end})+"
        intervals_str = intervals_str.rstrip('+')

        # Use ffmpeg to extract and concatenate clips
        filter_complex = f"[0:v]select='{intervals_str}',setpts=N/FRAME_RATE/TB[v];[0:a]aselect='{intervals_str}',asetpts=N/SR/TB[a]"
        output_filename = os.path.join(output_subdir, f"motion_{os.path.basename(video_path)}")
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-loglevel', 'quiet',  # Suppress ffmpeg output
            output_filename
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Motion video saved as {output_filename}")

        # Retrieve original file's timestamps
        access_time, modification_time = get_file_times(video_path)

        # Apply timestamps to the output file
        set_file_times(output_filename, access_time, modification_time)
        print(f"Metadata applied to {output_filename}")

        # Delete the original video file
        os.remove(video_path)
        print(f"Original video deleted: {video_path}")
    else:
        print(f"No motion detected in {video_path}")
        # Delete the original video file even if no motion was detected
        os.remove(video_path)
        print(f"Original video deleted: {video_path}")

def merge_intervals(intervals):
    """
    Merge overlapping intervals.
    """
    merged = []
    for interval in sorted(intervals):
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            merged[-1] = (
                merged[-1][0],
                max(merged[-1][1], interval[1]),
            )
    return merged

def process_video_wrapper(args):
    """
    Wrapper function for multiprocessing to handle exceptions and timing.
    """
    video_path, output_subdir = args
    filename = os.path.basename(video_path)
    print(f"Starting to process: {filename}")
    start_time = time.time()
    try:
        process_video(video_path, output_subdir)
        end_time = time.time()
        processing_time = end_time - start_time
        return filename, f"Processed successfully in {processing_time:.2f} seconds"
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        return filename, f"Error: {str(e)} (after {processing_time:.2f} seconds)"

def delete_empty_dirs(input_folder):
    """
    Recursively delete empty directories within the input folder.
    This function traverses the directory tree in a bottom-up manner.
    """
    for root, dirs, files in os.walk(input_folder, topdown=False):
        # Do not delete the root input folder itself
        if root == str(input_folder):
            continue

        # Check if the directory is empty
        if not dirs and not files:
            try:
                os.rmdir(root)
                print(f"Deleted empty directory: {root}")
            except OSError as e:
                print(f"Failed to delete directory {root}: {e}")

def main():
    """
    Main function to orchestrate video processing and directory cleanup.
    """
    # Define input and output directories using pathlib for better path handling
    input_folder = Path(os.getenv('INPUT_FOLDER', 'videos'))
    output_folder = Path(os.getenv('OUTPUT_FOLDER', 'output'))

    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)

    # Supported video file extensions
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mpeg')

    # Collect all video file paths recursively
    video_paths = []
    for video_file in input_folder.rglob('*'):
        if video_file.is_file() and video_file.suffix.lower() in video_extensions:
            # Determine the relative path to maintain directory structure
            relative_path = video_file.parent.relative_to(input_folder)
            
            # Create corresponding directory in the output folder
            output_subdir = output_folder / relative_path
            output_subdir.mkdir(parents=True, exist_ok=True)
            
            # Append tuple of (input video path, corresponding output subdirectory)
            video_paths.append((str(video_file), str(output_subdir)))

    total_videos = len(video_paths)
    processed_videos = 0

    print(f"Starting to process {total_videos} videos...")

    start_time_all = time.time()

    # Adjust the number of processes as needed; consider CPU cores and I/O constraints
    with Pool(processes=min(4, os.cpu_count())) as pool:
        for filename, status in pool.imap_unordered(process_video_wrapper, video_paths):
            processed_videos += 1
            print(f"[{processed_videos}/{total_videos}] {filename}: {status}")

    end_time_all = time.time()
    total_processing_time = end_time_all - start_time_all

    print(f"\nAll videos processed. Total: {total_videos}")
    print(f"Total processing time: {total_processing_time:.2f} seconds")

    # Delete empty directories in the input folder after processing all videos
    print("\nStarting to delete empty directories...")
    delete_empty_dirs(str(input_folder))
    print("Empty directories deletion completed.")

if __name__ == '__main__':
    main()
