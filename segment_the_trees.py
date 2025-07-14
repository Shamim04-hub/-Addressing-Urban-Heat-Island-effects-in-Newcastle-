import os
import sys
import yaml
from PIL import Image, ImageDraw
import numpy as np
from segment_anything import sam_model_registry, SamPredictor


# Function to segment trees in an image using SAM model, guided by bounding boxes from a YAML file
def segment_trees_with_sam(image_path,
                           yaml_path,
                           sam_model_type="vit_h",
                           sam_checkpoint="sam_vit_h_870864.pth",
                           output_dir="segmented_trees_output_sam"):
    """
    Segments trees in an image using SAM model, guided by bounding boxes from a YAML file.
    """
    try:
        # Block to load tree detection data from the YAML file
        try:
            # Open and load the YAML file
            with open(yaml_path, 'r') as yaml_file:
                tree_detections = yaml.safe_load(yaml_file)
                # If no detections are found in the YAML, print a message and return
                if not tree_detections:
                    print(
                        f"No tree detections found in YAML file: {yaml_path}")
                    return
        except FileNotFoundError:
            # Handle error if YAML file is not found
            print(f"Error: YAML file not found at: {yaml_path}")
            # Handle error if YAML file parsing fails
            return
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            return
        """  Load SAM Model """
        try:
            # Register and load the SAM model with the specified type and checkpoint
            sam = sam_model_registry[sam_model_type](checkpoint=sam_checkpoint)
            # Move the model to GPU if available, otherwise use CPU
            sam.to(
                'cuda' if torch.cuda.is_available() else 'cpu')  # getting GPU
            # Create a SAM predictor object
            predictor = SamPredictor(sam)
        except FileNotFoundError:
            # Handle error if SAM checkpoint file is not found
            print(f"Error: SAM checkpoint file not found at: {sam_checkpoint}")
            return
        except Exception as sam_load_exception:
            # Handle any other errors during SAM model loading
            print(f"Error loading SAM model: {sam_load_exception}")
            return

            # Block to load and prepare the input image
        try:
            # Open the image using PIL and convert to RGB format
            image_pil = Image.open(image_path).convert("RGB")
            # Convert the PIL image to a NumPy array
            image_np = np.array(image_pil)
            # Set the image for the SAM predictor
            predictor.set_image(image_np)
            # Handle error if the image file is not found
        except FileNotFoundError:
            # Handle any other errors during image loading
            print(f"Error: Image file not found at: {image_path}")
            return

        except Exception as image_load_exception:
            print(f"Error loading image file: {image_load_exception}")
            return

    # Define output directories for masks and segmented images
        output_mask_dir = os.path.join(output_dir, "masks")
        output_segmented_image_dir = os.path.join(output_dir,
                                                  "segmented_images")
        # Create these directories if they don't already exist
        os.makedirs(output_mask_dir, exist_ok=True)
        os.makedirs(output_segmented_image_dir, exist_ok=True)

        # Create a copy of the original image to draw segmentation overlays on
        segmented_image_pil = image_pil.copy()

        # Iterate through each tree detection found in the YAML file
        for i, detection in enumerate(tree_detections):
            # Extract bounding box coordinates (top-left x, top-left y, bottom-right x, bottom-right y)
            xh, yh, xw, yw = detection['xh'], detection['yh'], detection[
                'xw'], detection['yw']
            input_box = np.array([xh, yh, xw, yw])

            # Predict masks using the SAM model with the bounding box as a prompt
            masks, _, _ = predictor.predict(
                point_coords=None,
                point_labels=None,
                box=input_box,
                multimask_output=False,
            )
            # Get the first (and only, due to multimask_output=False) mask
            mask = masks[0]

            # Block to save the generated segmentation mask
            """  Save Segmentation Mask """
            # Convert the boolean mask to a PIL Image (0 or 255)
            mask_pil = Image.fromarray(mask)
            # Create a filename for the mask image
            mask_filename = os.path.splitext(
                os.path.basename(image_path))[0] + f"_tree_mask_{i+1}.png"
            mask_filepath = os.path.join(output_mask_dir, mask_filename)
            # Save the mask image
            mask_pil.save(mask_filepath)
            print(f"  Saved tree mask: {mask_filepath}")

            # Define the color for the mask overlay (green with some transparency)
            mask_overlay_color = (0, 255, 0, 150)
            # Create a drawing object for the copied image to draw overlays
            segmented_image_draw = ImageDraw.Draw(segmented_image_pil, 'RGBA')

            # Find contours in the binary mask to draw outlines instead of a filled overlay
            # 'level=0.5' is standard for binary images
            # 'fully_connected=high' considers 8-connectivity for contours
            contours = find_contours(mask, level=0.5, fully_connected='high')
            # Iterate over each contour found
            for n, contour in enumerate(contours):
                # Iterate over points in the contour
                for l in range(0, len(contour), 1):
                    # Contour points are (row, col), flip for PIL (x, y)
                    x_PIL, y_PIL = tuple(np.flip(contour[l], axis=0))
                    # Draw each point of the contour on the image
                    segmented_image_draw.point((x_PIL, y_PIL),
                                               fill=mask_overlay_color)

        # Define the filename for the final segmented image with overlays
        segmented_image_filename = os.path.splitext(
            os.path.basename(image_path))[0] + "_segmented.jpg"
        segmented_image_filepath = os.path.join(output_segmented_image_dir,
                                                segmented_image_filename)
        # Save the image with segmentation overlays
        segmented_image_pil.save(segmented_image_filepath)
        print(f"Segmented image saved: {segmented_image_filepath}")

    # Catch any other unexpected errors during the segmentation process
    except Exception as e:
        print(f"An unexpected error occurred during segmentation: {e}")


# Main execution block: This code runs when the script is executed directly
if __name__ == "__main__":
    # Import torch, necessary for SAM model if GPU is used, and skimage.measure for find_contours
    import torch
    import torch
    from skimage.measure import find_contours

    # Define paths for the input image, YAML detections, SAM checkpoint, and model type
    image_path = "data/coordinate_54.975056,-1.591944_images/street_view_0.jpg"
    yaml_path = "detected_trees_output_yolo_class/street_view_0_tree_detections.yaml"
    sam_checkpoint = "models/sam_vit_h_4b8939.pth"
    sam_model_type = "vit_h"

    # Original debugging print statements, commented out
    """
    print(f"Debugging: Image path: {image_path}") 
    print(f"Debugging: YAML path: {yaml_path}")  
    print(f"Debugging: SAM checkpoint path: {sam_checkpoint}") """

    # Call the main segmentation function with the defined parameter
    segment_trees_with_sam(image_path,
                           yaml_path,
                           sam_checkpoint=sam_checkpoint,
                           sam_model_type=sam_model_type)
    # Print a completion message
    print("Tree segmentation with SAM completed.")
