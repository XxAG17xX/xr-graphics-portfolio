import cv2
import time
import os
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh

drawingSpec = mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=3)

# Task 1a:increased max_num_faces to support multiple faces
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=5,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Task 1b:read all video files from a folder
input_folder = "videos"   #all mp4 files in this folder
video_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".mp4")])

# Task 1c:single video writer for combined output(easier for you to check output mister TA :)  )
out =None

currentTime = 0
previousTime = 0

print(f"Found {len(video_files)} videos: {video_files}")

for video_name in video_files:
    input_path = os.path.join(input_folder, video_name)
    cap = cv2.VideoCapture(input_path)
    print(f"Processing: {video_name}")

    # As long as device is ready
    while cap.isOpened():
        # Read the video frame
        success, image = cap.read()
        if not success:
           break

        # Flip the image for a front-facing webcam view
        image = cv2.flip(image, 1)

        # Resizing the frame
        aspect_ratio = image.shape[1] / image.shape[0]
        image = cv2.resize(image, (int(512 * aspect_ratio), 512))

        # Init writer once we know the frame size(from first video)
        if out is None:
            h, w = image.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')    
            out = cv2.VideoWriter("output.mp4", fourcc, 30, (w, h))         
    
        # Calculating the FPS
        currentTime = time.time()
        fps = 1 / (currentTime - previousTime) if previousTime != 0 else 0
        previousTime = currentTime

        # Displaying FPS and current video name on the image
        cv2.putText(image, str(int(fps)) + " FPS", (10, 70),
                    cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(image, video_name, (10, 110),
                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (0, 255, 255), 1)
        # Feed the frame to the MediaPipe face landmark detector
        # MediaPipe expects RGB, OpenCV gives BGR so we convert
        results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        # Visualize the detected landmarks
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=drawingSpec,
                    connection_drawing_spec=drawingSpec)
        # Write annotated frame to output video
        out.write(image)
    # Clean up after each video
    cap.release()
    print(f"Done: {video_name}")
out.release()
print("All videos combined into output.mp4")