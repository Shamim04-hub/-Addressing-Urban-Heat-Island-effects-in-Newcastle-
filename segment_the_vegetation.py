import onnxruntime as ort
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import os

# Define the path to the ONNX model file for Cityscapes semantic segmentation
model_path = 'models/cityscapes_fan_tiny_hybrid_224.onnx'
# Create an ONNX runtime inference session for the specified model
session = ort.InferenceSession(model_path)


def preprocess_image(image_path):

    # Open the image using PIL and convert to RGB
    img = Image.open(image_path).convert("RGB")
    # Resize the image to the model's expected input size (224x224)
    img = img.resize((224, 224))
    # Convert the image to a NumPy array and change data type to float32
    img = np.array(img).astype(np.float32)
    # Normalise pixel values by dividing by 255.0
    img = img / 255.0
    # Transpose the image dimensions from (height, width, channels) to (channels, height, width)
    img = np.transpose(img, (2, 0, 1))
    # Add a batch dimension at the beginning (axis=0) to match model input shape [1, C, H, W]
    img = np.expand_dims(img, axis=0)
    return img


def run_inference(session, img):
    # Get the name of the input node of the model
    input_name = session.get_inputs()[0].name
    # Run the model inference with the input image
    output_name = session.get_outputs()[0].name
    # Return the first (and typically only) output from the model, which is the segmentation mask
    result = session.run([output_name], {input_name: img})
    return result[0]


def overlay_tree_segmentation(original_image, mask):
    mask = mask.squeeze()
    # Define the class ID for trees in the Cityscapes dataset (typically 8 for 'vegetation' which includes trees)
    tree_class_id = 8
    # Create a binary mask where pixels belonging to the tree class are 1, others are 0
    tree_mask = np.where(mask == tree_class_id, 1, 0)
    # Convert the binary mask to an image (0-255 scale)
    tree_mask = Image.fromarray(tree_mask.astype(np.uint8) * 255)
    # Resize the mask to match the original image size using nearest-neighbor interpolation
    tree_mask = tree_mask.resize(original_image.size, Image.NEAREST)

    # Create an alpha channel for the overlay: make the tree mask semi-transparent
    # Convert tree_mask to grayscale ('L') and adjust alpha (0.5 for 50% opacity)
    alpha = tree_mask.convert("L").point(lambda p: p * 0.5)
    # Create a solid green image for the tree regions
    tree_rgb = Image.new("RGB", original_image.size, (144, 238, 144))
    # Apply the alpha mask to the green image
    tree_rgb.putalpha(alpha)
    # Composite the original image (converted to RGBA) with the semi-transparent green overlay
    combined = Image.alpha_composite(original_image.convert("RGBA"), tree_rgb)
    return combined


def create_panorama(image_paths, output_dir):
    # If no image paths are provided, do nothing
    if not image_paths:
        return

    try:
        # Open all images from the provided paths
        images = [Image.open(path) for path in image_paths if path]
        # Assuming all images have the same height, use the height of the first image
        height = images[0].height
        # Get the widths of all individual images
        widths = [img.width for img in images]
        # Calculate the total width of the panorama
        total_width = sum(widths)
        # Create a new blank RGB image for the panorama
        panorama = Image.new("RGB", (total_width, height))

        # Paste each image into the panorama image side-by-side
        x_offset = 0
        for img in images:
            panorama.paste(img, (x_offset, 0))
            x_offset += img.width

    # Define the save path for the panorama and save it
        panorama_path = os.path.join(output_dir, "segmented_panorama.jpg")
        panorama.save(panorama_path)
        print(f"Panorama saved to: {panorama_path}")

    except Exception as e:
        # Print an error message if panorama creation fails
        print(f"Error creating panorama: {e}")


# enter cooridnates for specified street/location ti be segementated vegetated
input_directory = 'data/coordinate_54.975056,-1.591944_images'
# Define the output directory where segmented images will be saved
output_directory = 'segmented_trees'
os.makedirs(output_directory, exist_ok=True)

# List to store paths of the processed (segmented) images for panorama creation
image_paths = []

# Iterate over all files in the input directory
for filename in os.listdir(input_directory):
    # Check if the file is an image (ends with .jpg or .png)
    if filename.endswith('.jpg') or filename.endswith('.png'):
        # Construct the full path to the image
        image_path = os.path.join(input_directory, filename)
        # Open the original image and convert it to RGB
        original_image = Image.open(image_path).convert("RGB")
        # Preprocess the image for the model
        preprocessed_image = preprocess_image(image_path)
        # Run inference to get the segmentation mask
        mask = run_inference(session, preprocessed_image)
        # Overlay the tree segmentation (or general vegetation based on class ID 8) onto the original image
        result_image = overlay_tree_segmentation(original_image, mask)
        output_path = os.path.join(output_directory,
                                   filename.split('.')[0] + '.png')
        # Save the resulting image
        result_image.save(output_path)
        image_paths.append(output_path)
# Create a panorama from all the segmented images
create_panorama(image_paths, output_directory)
# Print a completion message
print("Segmentation completed and saved in the 'segmented_trees' directory.")

