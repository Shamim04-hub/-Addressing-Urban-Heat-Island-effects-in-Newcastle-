"""
Reference:
"""
from ultralytics import YOLO  # For YOLO object detection
import os  # For operating system dependent functionalities like path joining
from PIL import Image, ImageDraw  # For image manipulation and drawing bounding boxes
import numpy as np


# Function to run tree detection on a single image using a YOLO model
def run_tree_detection_yolo_class(image_path,
                                  model_path,
                                  output_dir,
                                  confidence_threshold=0.20):
    """Detects trees in an image using the YOLO class and saves the output."""
    try:
        # Load the YOLO model from the specified path
        model = YOLO(model_path)
        # Perform prediction on the input image
        # save=False, save_txt=False prevent default saving mechanisms of YOLO
        # save_conf=True ensures confidence scores are included in the results
        results = model.predict(
            source=image_path,
            conf=confidence_threshold,
            save=False,
            save_txt=False,
            save_conf=True,
        )[0]  # Access the first element of the results list

        # Check if any results (detections) were returned
        if results:
            # Get bounding box information from the results
            boxes = results.boxes
            # Get class names from the loaded model
            names = model.names
            # Open the input image using PIL for drawing
            detected_image = Image.open(image_path).convert("RGB")
            # Create a drawing object for the image
            draw = ImageDraw.Draw(detected_image)

            # InitialiSe a counter for detected trees
            tree_detected_count = 0

            # Check if any bounding boxes were detected
            if boxes:
                # Convert bounding box coordinates (xyxy format), confidences, and class IDs to lists
                xyxy = boxes.xyxy.tolist()
                confidences = boxes.conf.tolist()
                class_ids = boxes.cls.int().tolist()

                # Iterate over each detected bounding box
                for i in range(len(xyxy)):
                    # Get coordinates, confidence, and class ID for the current detection
                    x1, y1, x2, y2 = map(
                        int, xyxy[i])  # Convert coordinates to integers
                    confidence = confidences[i]
                    class_id = class_ids[i]
                    class_name = names[
                        class_id]  # Get the name of the detected class

                    # Check if the detected class is 'tree'
                    if class_name == 'tree':
                        # Increment the tree counter
                        tree_detected_count += 1
                        # Create a label string with the class name and confidence score
                        label = f"{class_name}_{confidence:.2f}"
                        # Draw a green rectangle (bounding box) around the detected tree
                        draw.rectangle([(x1, y1), (x2, y2)],
                                       outline="green",
                                       width=2)
                        # Define the position for the label text (below the bounding box)
                        text_position = (x1, y2 + 15)
                        # Draw the label text on the image
                        draw.text(text_position, label, fill="blue")
            # Print the number of trees detected in the current image
            if tree_detected_count > 0:
                print(f"Detected {tree_detected_count} trees in {image_path}")
            else:
                print(f"No trees detected in {image_path}")
# Define the full output path for the image with detections
            output_path = os.path.join(output_dir,
                                       os.path.basename(image_path))
            # Create the output directory if it doesn't already exist
            os.makedirs(output_dir, exist_ok=True)
            # Save the image with drawn bounding boxes and labels
            detected_image.save(output_path)
            print(f"Image with tree detections saved to: {output_path}")

    except Exception as e:
        # Save the image with drawn bounding boxes and labels
        print(f"Error during tree detection: {e}")


# Function to process all images in a given input directory for tree detection
def process_directory(input_dir,
                      model_path,
                      output_dir,
                      confidence_threshold=0.10):
    """Processes all images in the input directory for tree detection."""
    # Check if the input directory exists
    if not os.path.exists(input_dir):
        print(f"Input directory '{input_dir}' does not exist.")
        return  # Exit the function if the directory is not found

    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over each file in the input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Construct the full path to the current image
            image_path = os.path.join(input_dir, filename)
            print(f"Processing image: {image_path}")
            # Call the tree detection function for the current image
            run_tree_detection_yolo_class(image_path, model_path, output_dir,
                                          confidence_threshold)


if __name__ == "__main__":
    # Define the path to the trained YOLO model file
    model_path = "models/count_trees_aerial_best.pt"  # Path to the YOLO model
    input_directory = "data/Satellite_images"  # Directory containing satellite images
    output_directory = "count_trees_opt"  # Directory to save processed images
    confidence_threshold = 0.50  # Confidence threshold for tree detection

    # Call the function to process all images in the specified directory
    process_directory(input_directory, model_path, output_directory,
                      confidence_threshold)
    # Print a message indicating the completion of the process
    print("Tree detection for all images in the directory completed.")
