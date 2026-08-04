import cv2
# Open the default webcam
camera = cv2.VideoCapture(0)
# Check if webcam opened successfully
if not camera.isOpened():
    print("Unable to access the webcam.")
    exit()
print("Press 'q' to close the webcam.")
while True:
    # Read a frame
    ret, frame = camera.read()
    if not ret:
        print("Failed to capture frame.")
        break
    # Display the frame
    cv2.imshow("Live Webcam Feed", frame)
    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
# Release webcam
camera.release()
# Close all OpenCV windows
cv2.destroyAllWindows()