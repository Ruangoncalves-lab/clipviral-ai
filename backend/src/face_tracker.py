import os
import logging

logger = logging.getLogger("face_tracker")

try:
    import cv2
except ImportError:
    cv2 = None
    logger.warning("OpenCV is not installed. Face tracking will fall back to center crop.")

def detect_and_track_faces(video_path: str, start_time: float, duration: float):
    """
    Analyzes the video clip to detect faces.
    Returns:
        layout: 'single' | 'split'
        speaker_coords: list of dicts, e.g. [{'x': 100, 'w': 200}, ...]
    """
    if cv2 is None:
        logger.info("OpenCV not imported, using centered crop fallback.")
        return 'single', [{'x': 0.0, 'w': 0.0}]
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Could not open video file: {video_path}")
        return 'single', [{'x': 0.0, 'w': 0.0}]
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Fallback default coordinates
    center_coords = [{'x': float(width / 2), 'w': 0.0}]
    
    # Load Haar Cascade
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            logger.error("Haar Cascade Classifier failed to load XML config.")
            cap.release()
            return 'single', center_coords
    except Exception as e:
        logger.error(f"Failed to load Haar Cascade: {e}")
        cap.release()
        return 'single', center_coords
        
    # Seek to start_time
    start_frame = int(start_time * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    max_frames = int(duration * fps)
    sampled_frames = 0
    frame_skip = 10  # Sample every 10 frames
    
    detected_faces_list = []
    
    while sampled_frames < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        if sampled_frames % frame_skip == 0:
            try:
                # Resize frame to speed up face detection
                target_w = 640
                scale = target_w / width
                target_h = int(height * scale)
                resized = cv2.resize(frame, (target_w, target_h))
                
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                
                for (x, y, w, h) in faces:
                    # Map back to original resolution
                    orig_x = int(x / scale)
                    orig_y = int(y / scale)
                    orig_w = int(w / scale)
                    orig_h = int(h / scale)
                    detected_faces_list.append({
                        'x': float(orig_x + orig_w / 2), # center X
                        'y': float(orig_y + orig_h / 2), # center Y
                        'w': float(orig_w),
                        'h': float(orig_h)
                    })
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                
        sampled_frames += 1
        
    cap.release()
    
    if not detected_faces_list:
        logger.info("No faces detected in the clip, using center enquadramento.")
        return 'single', center_coords
        
    x_centers = [f['x'] for f in detected_faces_list]
    min_x = min(x_centers)
    max_x = max(x_centers)
    
    # If spatial gap is greater than 20% of video width and we have enough samples, assume split layout
    if (max_x - min_x) > (width * 0.20) and len(detected_faces_list) >= 4:
        mid_x = (min_x + max_x) / 2
        left_faces = [f for f in detected_faces_list if f['x'] < mid_x]
        right_faces = [f for f in detected_faces_list if f['x'] >= mid_x]
        
        if left_faces and right_faces:
            left_avg_x = sum(f['x'] for f in left_faces) / len(left_faces)
            right_avg_x = sum(f['x'] for f in right_faces) / len(right_faces)
            logger.info(f"Split layout detected: Left X = {left_avg_x:.1f}, Right X = {right_avg_x:.1f}")
            return 'split', [
                {'x': left_avg_x, 'w': sum(f['w'] for f in left_faces) / len(left_faces)},
                {'x': right_avg_x, 'w': sum(f['w'] for f in right_faces) / len(right_faces)}
            ]
            
    # Default to single centered face
    avg_x = sum(x_centers) / len(x_centers)
    logger.info(f"Single speaker layout detected: X = {avg_x:.1f}")
    return 'single', [{'x': avg_x, 'w': sum(f['w'] for f in detected_faces_list) / len(detected_faces_list)}]
