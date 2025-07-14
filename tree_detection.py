from ultralytics import YOLO
import os
from PIL import Image, ImageDraw
import yaml


# Function to run tree detection using a YOLO model on a single image
def run_tree_detection_yolo_class(
        image_path,
        model_path,
        output_dir="detected_trees_output_yolo_class",
        confidence_threshold=0.25):
    """Detects trees in an image using the YOLO class, saves output image and detection coordinates to YAML."""
    try:
        # Load the YOLO model from the specified model path
        model = YOLO(model_path)

        # Perform prediction on the input image
        # `save=False` prevents Ultralytics from saving its own default output image
        # `save_txt=False` prevents saving labels in YOLO txt format
        # `save_conf=True` includes confidence scores in the results
        results = model.predict(
            source=image_path,
            conf=confidence_threshold,
            save=False,
            save_txt=False,
            save_conf=True,
        )[0]
        # List to store data for each detected tree
        tree_detections_data = []

        # Check if any detections were made
        if results:
            # Extract bounding boxes and class names from the results
            boxes = results.boxes
            names = model.names  # Class names from the model

            # Open the original image using PIL to draw on it
            detected_image = Image.open(image_path).convert("RGB")
            draw = ImageDraw.Draw(detected_image)  # Create a drawing context

            tree_detected_count = 0  # Counter for detected trees

            # Check if there are any bounding boxes in the results
            if boxes:
                # Get coordinates (xyxy format), confidences, and class IDs as lists
                xyxy = boxes.xyxy.tolist()
                confidences = boxes.conf.tolist()
                class_ids = boxes.cls.int().tolist()

                # Iterate through each detected object
                for i in range(len(xyxy)):
                    x1, y1, x2, y2 = map(
                        int, xyxy[i])  # Convert coordinates to integers
                    confidence = confidences[i]
                    class_id = class_ids[i]
                    class_name = names[
                        class_id]  # Get the class name using the class ID

                    # Check if the detected object is a 'tree'
                    if class_name == 'tree':
                        tree_detected_count += 1
                        # Create a label with class name and confidence
                        label = f"{class_name}Tree_{confidence:.2f}"
                        # Draw a green rectangle around the detected tree
                        draw.rectangle([(x1, y1), (x2, y2)],
                                       outline="green",
                                       width=2)
                        # Draw the label text below the bounding box
                        draw.text((x1, y2 + 5), label, fill="blue")

                        # Store the detection data for this tree
                        tree_data = {
                            "class_name": class_name,
                            "confidence":
                            float(confidence),  # Ensure confidence is float
                            "xh": int(x1),  # Top-left x-coordinate
                            "yh": int(y1),  # Top-left y-coordinate
                            "xw": int(x2),  # Bottom-right x-coordinate
                            "yw": int(y2),  # Bottom-right y-coordinate
                        }
                        tree_detections_data.append(tree_data)
                        print(
                            f"  Detected Tree Coordinates (xh, yh, xw, yw): x1={x1}, y1={y1}, x2={x2}, y2={y2}"
                        )

        # Print the number of trees detected in the image
            if tree_detected_count > 0:
                print(f"Detected {tree_detected_count} trees in {image_path}")
            else:
                print(f"No trees detected in {image_path}")

            # Define the output path for the image with detections
            output_path = os.path.join(output_dir,
                                       os.path.basename(image_path))
            # Create the output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            # Save the image with drawn bounding boxes
            detected_image.save(output_path)
            print(f"Image with tree detections saved to: {output_path}")

            # If tree detections were made, save them to a YAML file
            if tree_detections_data:
                # Create YAML filename based on the original image name
                yaml_filename = os.path.splitext(
                    os.path.basename(image_path))[0] + "_tree_detections.yaml"
                yaml_filepath = os.path.join(output_dir, yaml_filename)
                # Write the list of tree detection data to the YAML file
                with open(yaml_filepath, 'w') as yaml_file:
                    yaml.dump(tree_detections_data, yaml_file, indent=2)
                print(
                    f"Tree detection coordinates saved to YAML: {yaml_filepath}"
                )

# Print any error that occurs during the detection process
    except Exception as e:
        print(f"Error during tree detection: {e}")


# Function to process all images within a given folder for tree detection
def process_images_in_folder(folder_path,
                             model_path,
                             output_dir="detected_trees_output_yolo_class",
                             confidence_threshold=0.25):
    """Processes all images in a folder to detect trees and save the results in a different folder."""
    # Iterate through all files in the specified folder
    for filename in os.listdir(folder_path):
        # Check if the file is an image (ends with .jpg or .png)
        if filename.endswith(".jpg") or filename.endswith(".png"):
            # Construct the full path to the image
            image_path = os.path.join(folder_path, filename)
            # Run tree detection on the current image
            run_tree_detection_yolo_class(image_path, model_path, output_dir,
                                          confidence_threshold)


if __name__ == "__main__":
    # Defines the folder containing input images
    folder_path = "data/coordinate_55.0149809,-1.6224566_images"  # Replace <latitude> and <longitude> with actual values
    # Defines the path to the trained YOLO model
    model_path = "models/tree_detection_street_best.pt"
    # Defines the directory where output files will be saved
    output_directory = "detected_trees_output_yolo_class"

    # Process all images in the specified folder
    process_images_in_folder(folder_path, model_path, output_directory)
    # Print a completion message
    print("Tree detection in all images completed.")